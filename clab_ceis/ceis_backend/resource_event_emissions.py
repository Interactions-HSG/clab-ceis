"""CO2 enrichment for resource events."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import HTTPException

from ceis_backend.config import DB_PATH
from ceis_backend.data.location_details import ACTIVITY_ID_LONG_DISTANCE_TRANSPORT
from ceis_backend.queries import db_update_garment_inventory_co2
from ceis_backend.utils import (
    calculate_transport_emission,
    get_co2_for_garment,
    get_co2_for_sold_garment,
)
from ceis_backend.wiser_bridge import WiserClient, WiserClientError


DEMO_EMISSION_FACTORS = {
    276186: 8.0,
    6756: 6.0,
    20936: 10.0,
    6566: 1.0,
    21893: 2.0,
    7309: 0.2,
    17901: 0.1,
}


class _ResourceEventEmissionClient:
    def __init__(self, wiser_client: WiserClient) -> None:
        self._wiser_client = wiser_client
        self._cache: dict[int, float | None] = {}
        self._demo_activity_ids: set[int] = set()
        self.used_demo_factors = False

    def reset_calculation_scope(self) -> None:
        self.used_demo_factors = False

    def get_emission_per_unit(self, activity_id: int) -> float | None:
        if activity_id in self._cache:
            if activity_id in self._demo_activity_ids:
                self.used_demo_factors = True
            return self._cache[activity_id]

        used_demo_factor = False
        emission_per_unit = None
        try:
            emission_per_unit = self._wiser_client.get_emission_per_unit(activity_id)
        except WiserClientError:
            emission_per_unit = DEMO_EMISSION_FACTORS.get(activity_id)
            used_demo_factor = emission_per_unit is not None

        if emission_per_unit is None and activity_id in DEMO_EMISSION_FACTORS:
            emission_per_unit = DEMO_EMISSION_FACTORS[activity_id]
            used_demo_factor = True

        if used_demo_factor:
            self.used_demo_factors = True
            self._demo_activity_ids.add(activity_id)

        self._cache[activity_id] = emission_per_unit
        return emission_per_unit


def enrich_resource_events_with_co2(
    events: list[dict[str, Any]], wiser_client: WiserClient
) -> list[dict[str, Any]]:
    """Return resource events with CO2 calculated where enough inputs exist."""
    if not events:
        return []

    order_details = _get_order_details(
        {
            int(event["order_id"])
            for event in events
            if event.get("order_id") is not None
        }
    )
    material_details = _get_material_details(
        {
            int(event["material_id"])
            for event in events
            if event.get("material_id") is not None
        }
    )
    material_distance_details = _get_material_distance_details(
        {
            int(event["material_manufacturer_distance_id"])
            for event in events
            if event.get("material_manufacturer_distance_id") is not None
        }
    )

    emission_client = _ResourceEventEmissionClient(wiser_client)
    enriched_events = []
    for event in events:
        enriched = dict(event)
        emission_client.reset_calculation_scope()
        if enriched.get("co2eq") is not None:
            enriched["co2eq_calculation_status"] = "stored"
            enriched_events.append(enriched)
            continue

        result = _calculate_event_co2(
            enriched,
            emission_client,
            order_details,
            material_details,
            material_distance_details,
        )
        enriched.update(result)
        if (
            result.get("co2eq") is not None
            and result.get("co2eq_calculation_status") == "calculated"
        ):
            _update_resource_event_co2(
                int(enriched["event_id"]),
                float(result["co2eq"]),
            )
        enriched_events.append(enriched)

    return enriched_events


def _calculate_event_co2(
    event: dict[str, Any],
    emission_client: _ResourceEventEmissionClient,
    order_details: dict[int, dict[str, Any]],
    material_details: dict[int, dict[str, Any]],
    material_distance_details: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    order_id = event.get("order_id")
    if order_id is not None:
        return _calculate_order_event_co2(
            int(order_id), emission_client, order_details
        )

    material_id = event.get("material_id")
    if material_id is not None:
        return _calculate_material_event_co2(
            int(material_id), emission_client, material_details
        )

    material_distance_id = event.get("material_manufacturer_distance_id")
    if material_distance_id is not None:
        return _calculate_material_transport_event_co2(
            int(material_distance_id),
            emission_client,
            material_distance_details,
        )

    if event.get("manufacturer_distance_id") is not None:
        return {
            "co2eq_calculation_status": "missing_inputs",
            "co2eq_calculation_note": (
                "Transport distance is known, but no shipment weight is linked."
            ),
        }

    return {
        "co2eq_calculation_status": "not_applicable",
        "co2eq_calculation_note": "Lifecycle or supplier marker event.",
    }


def _calculate_order_event_co2(
    order_id: int,
    emission_client: _ResourceEventEmissionClient,
    order_details: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    order = order_details.get(order_id)
    if order is None:
        return {
            "co2eq_calculation_status": "missing_inputs",
            "co2eq_calculation_note": "Order record was not found.",
        }

    stored_inventory_co2 = order.get("inventory_co2eq")
    if stored_inventory_co2 is not None:
        return {
            "co2eq": round(float(stored_inventory_co2), 6),
            "co2eq_calculation_status": "calculated",
            "co2eq_calculation_note": "Copied from linked garment inventory.",
        }

    garment_inventory_id = order.get("garment_inventory_id")
    if garment_inventory_id is not None:
        try:
            emission_details = get_co2_for_sold_garment(
                int(garment_inventory_id),
                int(order["garment_type_id"]),
                emission_client,
            )
        except HTTPException as error:
            return {
                "co2eq_calculation_status": "missing_inputs",
                "co2eq_calculation_note": str(error.detail),
            }
        total_co2 = _total_garment_co2(emission_details)
        if _calculation_status(emission_client) == "calculated":
            db_update_garment_inventory_co2(int(garment_inventory_id), total_co2)
        return {
            "co2eq": round(total_co2, 6),
            "co2eq_calculation_status": _calculation_status(emission_client),
            "co2eq_calculation_note": "Calculated from linked garment inventory.",
        }

    material_id = order.get("material_id")
    if material_id is None:
        return {
            "co2eq_calculation_status": "missing_inputs",
            "co2eq_calculation_note": (
                "Production order has no selected material."
            ),
        }

    try:
        emission_details = get_co2_for_garment(
            int(order["garment_type_id"]),
            emission_client,
            int(material_id),
        )
    except HTTPException as error:
        return {
            "co2eq_calculation_status": "missing_inputs",
            "co2eq_calculation_note": str(error.detail),
        }
    return {
        "co2eq": round(_total_garment_co2(emission_details), 6),
        "co2eq_calculation_status": _calculation_status(emission_client),
        "co2eq_calculation_note": "Calculated from garment recipe and material.",
    }


def _calculate_material_event_co2(
    material_id: int,
    emission_client: _ResourceEventEmissionClient,
    material_details: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    material = material_details.get(material_id)
    if material is None:
        return {
            "co2eq_calculation_status": "missing_inputs",
            "co2eq_calculation_note": "Material record was not found.",
        }

    emission_per_unit = emission_client.get_emission_per_unit(
        int(material["activity_id"])
    )
    if emission_per_unit is None:
        return {
            "co2eq_calculation_status": "missing_factor",
            "co2eq_calculation_note": "No material emission factor is available.",
        }

    return {
        "co2eq": round(emission_per_unit * float(material["kg_per_sqm"]), 6),
        "co2eq_calculation_status": _calculation_status(emission_client),
        "co2eq_calculation_note": "Calculated per square meter of material.",
    }


def _calculate_material_transport_event_co2(
    material_distance_id: int,
    emission_client: _ResourceEventEmissionClient,
    material_distance_details: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    material_distance = material_distance_details.get(material_distance_id)
    if material_distance is None:
        return {
            "co2eq_calculation_status": "missing_inputs",
            "co2eq_calculation_note": (
                "Material transport distance record was not found."
            ),
        }

    emission_per_unit = emission_client.get_emission_per_unit(
        ACTIVITY_ID_LONG_DISTANCE_TRANSPORT
    )
    if emission_per_unit is None:
        return {
            "co2eq_calculation_status": "missing_factor",
            "co2eq_calculation_note": "No transport emission factor is available.",
        }

    co2eq = calculate_transport_emission(
        float(material_distance["distance_km"]),
        float(material_distance["kg_per_sqm"]),
        emission_per_unit,
    )
    return {
        "co2eq": round(float(co2eq or 0), 6),
        "co2eq_calculation_status": _calculation_status(emission_client),
        "co2eq_calculation_note": (
            "Calculated per square meter of material transported."
        ),
    }


def _total_garment_co2(emission_details: Any) -> float:
    return float(emission_details.fabric_blocks.total_emission) + float(
        emission_details.processes.total_emission
    )


def _calculation_status(emission_client: _ResourceEventEmissionClient) -> str:
    return "estimated" if emission_client.used_demo_factors else "calculated"


def _get_order_details(order_ids: set[int]) -> dict[int, dict[str, Any]]:
    if not order_ids:
        return {}

    placeholders = ",".join("?" for _ in order_ids)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT o.id,
                   o.garment_type_id,
                   o.material_id,
                   o.garment_inventory_id,
                   gi.co2eq
            FROM orders o
            LEFT JOIN garments_inventory gi ON gi.id = o.garment_inventory_id
            WHERE o.id IN ({placeholders})
            """,
            sorted(order_ids),
        )
        return {
            row[0]: {
                "garment_type_id": row[1],
                "material_id": row[2],
                "garment_inventory_id": row[3],
                "inventory_co2eq": row[4],
            }
            for row in cursor.fetchall()
        }


def _get_material_details(material_ids: set[int]) -> dict[int, dict[str, Any]]:
    if not material_ids:
        return {}

    placeholders = ",".join("?" for _ in material_ids)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT id, kg_per_sqm, activity_id
            FROM materials
            WHERE id IN ({placeholders})
            """,
            sorted(material_ids),
        )
        return {
            row[0]: {
                "kg_per_sqm": row[1],
                "activity_id": row[2],
            }
            for row in cursor.fetchall()
        }


def _get_material_distance_details(
    material_distance_ids: set[int],
) -> dict[int, dict[str, Any]]:
    if not material_distance_ids:
        return {}

    placeholders = ",".join("?" for _ in material_distance_ids)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"""
            SELECT mmd.id, mmd.distance_km, m.kg_per_sqm
            FROM material_manufacturer_distances mmd
            JOIN materials m ON m.id = mmd.material_id
            WHERE mmd.id IN ({placeholders})
            """,
            sorted(material_distance_ids),
        )
        return {
            row[0]: {
                "distance_km": row[1],
                "kg_per_sqm": row[2],
            }
            for row in cursor.fetchall()
        }


def _update_resource_event_co2(event_id: int, co2eq: float) -> None:
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE resource_events SET co2eq = ? WHERE id = ?",
            (round(co2eq, 6), event_id),
        )
