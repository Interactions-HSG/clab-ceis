from __future__ import annotations

import json
from functools import lru_cache

from fastapi import HTTPException

from ceis_backend.config import BASE_DIR
from ceis_backend.data.location_details import (
    ACTIVITY_ID_LONG_DISTANCE_TRANSPORT,
    ACTIVITY_ID_TRANSPORT,
    COTTON_DISTANCE_TO_MANUFACTURER_KM,
    HEMP_DISTANCE_TO_MANUFACTURER_KM,
    SILK_DISTANCE_TO_MANUFACTURER_KM,
)
from ceis_backend.queries import (
    db_get_fabric_block_types,
    db_get_garment_types,
    db_get_manufacturer_distance_row,
    db_get_materials,
    db_get_manufacturers,
    db_get_materials_for_garment,
    db_get_process_types,
    get_fabric_block_processes_for_emission,
    get_full_garment_recipe,
)
from ceis_backend.utils import calculate_transport_emission, get_co2_for_garment
from ceis_backend.wiser_bridge import WiserClient


MOCK_DATA_PATH = BASE_DIR / "data" / "designer_balance_mock_data.json"


@lru_cache(maxsize=1)
def load_designer_balance_mock_data() -> dict:
    with MOCK_DATA_PATH.open(encoding="utf-8") as mock_file:
        return json.load(mock_file)


def get_designer_balance_options() -> dict:
    return {
        "garment_types": db_get_garment_types(),
        "suppliers": {
            "fabric": db_get_manufacturers("fabric"),
            "garment": db_get_manufacturers("garment"),
            "finishing": db_get_manufacturers("finishing"),
        },
    }


def get_designer_garment_reference_data(wiser_client: WiserClient) -> dict:
    mock_data = load_designer_balance_mock_data()
    emission_cache: dict[int, float | None] = {}

    materials = []
    for material in db_get_materials():
        material_mock = _mock_material_data(material["name"], mock_data)
        material_emission_per_unit = _get_emission_per_unit(
            wiser_client, material["activity_id"], emission_cache
        )
        materials.append(
            {
                **material,
                "cost_per_kg_chf": _safe_round(
                    float(material_mock.get("cost_per_kg_chf", 0))
                ),
                "longevity_wears": int(material_mock.get("longevity_wears", 0)),
                "co2eq_per_kg": (
                    _safe_round(material_emission_per_unit, 3)
                    if material_emission_per_unit is not None
                    else None
                ),
            }
        )

    process_rows = []
    process_defs = mock_data.get("process_types", {})
    for process_type in db_get_process_types():
        process_mock = process_defs.get(
            process_type["name"].lower(), process_defs.get("default", {})
        )
        ecological_unit_cost = _get_emission_per_unit(
            wiser_client, process_type["activity_id"], emission_cache
        )

        process_rows.append(
            {
                **process_type,
                "economic_cost_per_unit_chf": _safe_round(
                    float(process_mock.get("cost_per_unit_chf", 0))
                ),
                "ecological_cost_per_unit_co2eq": (
                    _safe_round(float(ecological_unit_cost), 6)
                    if ecological_unit_cost is not None
                    else None
                ),
            }
        )

    fabric_block_types = db_get_fabric_block_types()

    return {
        "garment_types": db_get_garment_types(),
        "materials": materials,
        "process_types": process_rows,
        "fabric_block_types": _build_fabric_block_reference_rows(
            fabric_block_types, materials, wiser_client, emission_cache
        ),
    }


def _safe_round(value: float | int | None, digits: int = 2) -> float:
    return round(float(value or 0), digits)


def _get_emission_per_unit(
    wiser_client: WiserClient,
    activity_id: int | None,
    emission_cache: dict[int, float | None] | None = None,
) -> float | None:
    if activity_id is None:
        return None
    if emission_cache is not None and activity_id in emission_cache:
        return emission_cache[activity_id]
    try:
        emission_per_unit = wiser_client.get_emission_per_unit(activity_id)
    except Exception:
        emission_per_unit = None
    if emission_cache is not None:
        emission_cache[activity_id] = emission_per_unit
    return emission_per_unit


def _get_material_distance_to_manufacturer_km(material_name: str) -> float | None:
    material_distances = {
        "hemp": HEMP_DISTANCE_TO_MANUFACTURER_KM,
        "cotton": COTTON_DISTANCE_TO_MANUFACTURER_KM,
        "silk": SILK_DISTANCE_TO_MANUFACTURER_KM,
        "mikado silk": SILK_DISTANCE_TO_MANUFACTURER_KM,
    }
    return material_distances.get(material_name.lower())


def _calculate_fabric_block_reference_emission(
    fabric_block_type: dict,
    material: dict,
    wiser_client: WiserClient,
    emission_cache: dict[int, float | None],
) -> float | None:
    block_weight_kg = float(material["kg_per_sqm"]) * float(fabric_block_type["sqm"])

    material_emission_per_unit = _get_emission_per_unit(
        wiser_client, material.get("activity_id"), emission_cache
    )
    if material_emission_per_unit is None:
        return None
    total_emission = material_emission_per_unit * block_weight_kg

    for _, process_amount, process_activity_id in get_fabric_block_processes_for_emission(
        fabric_block_type["id"]
    ):
        process_emission_per_unit = _get_emission_per_unit(
            wiser_client, process_activity_id, emission_cache
        )
        if process_emission_per_unit is None:
            return None
        total_emission += process_emission_per_unit * float(process_amount)

    distance_km = _get_material_distance_to_manufacturer_km(material["name"])
    if distance_km is None:
        return None

    transport_emission = calculate_transport_emission(
        distance_km,
        block_weight_kg,
        _get_emission_per_unit(
            wiser_client, ACTIVITY_ID_LONG_DISTANCE_TRANSPORT, emission_cache
        ),
    )
    if transport_emission is None:
        return None

    return _safe_round(total_emission + transport_emission, 3)


def _build_fabric_block_reference_rows(
    fabric_block_types: list[dict],
    materials: list[dict],
    wiser_client: WiserClient,
    emission_cache: dict[int, float | None],
) -> list[dict]:
    rows = []
    for fabric_block_type in fabric_block_types:
        for material in materials:
            rows.append(
                {
                    "id": fabric_block_type["id"],
                    "name": fabric_block_type["name"],
                    "sqm": fabric_block_type["sqm"],
                    "material": material["name"],
                    "co2eq_kg": _calculate_fabric_block_reference_emission(
                        fabric_block_type, material, wiser_client, emission_cache
                    ),
                }
            )
    return rows


def _mock_material_data(material_name: str, mock_data: dict) -> dict:
    materials = mock_data.get("materials", {})
    return materials.get(material_name.lower(), materials.get("default", {}))


def _process_cost(process_name: str, amount: float, mock_data: dict) -> float:
    process_definitions = mock_data.get("process_types", {})
    process_data = process_definitions.get(
        process_name.lower(), process_definitions.get("default", {})
    )
    return float(process_data.get("cost_per_unit_chf", 0)) * float(amount)


def _transport_cost(
    distance_km: float | None, amount_kg: float, mock_data: dict
) -> float:
    if distance_km is None:
        return 0.0
    process_definitions = mock_data.get("process_types", {})
    cost_per_ton_km = float(
        process_definitions.get("transport", {}).get("cost_per_ton_km_chf", 0)
    )
    return cost_per_ton_km * (float(amount_kg) / 1000.0) * float(distance_km)


def _transport_delay(distance_km: float | None, mock_data: dict) -> float:
    if distance_km is None:
        return 0.0
    delay_model = mock_data.get("delay_model", {})
    base_delay = float(delay_model.get("transport_base_delay_days", 0))
    delay_per_100_km = float(delay_model.get("transport_delay_days_per_100_km", 0))
    return base_delay + (float(distance_km) / 100.0) * delay_per_100_km


def _actor_delay(role_group: str, mock_data: dict) -> float:
    delay_model = mock_data.get("delay_model", {})
    actor_delays = delay_model.get("actor_base_delay_days", {})
    return float(actor_delays.get(role_group, actor_delays.get("default", 0)))


def _select_default_company(
    options: list[dict], preferred: str | None = None
) -> str | None:
    if preferred:
        for option in options:
            if option["company"] == preferred:
                return preferred
    if not options:
        return None
    return options[0]["company"]


def _build_supply_chain_legs(
    fabric_supplier: dict | None,
    garment_supplier: dict | None,
    finishing_supplier: dict | None,
    total_weight_kg: float,
    transport_emission_per_unit: float | None,
    mock_data: dict,
) -> tuple[list[dict], list[dict], dict]:
    actors = []
    if fabric_supplier:
        actors.append(
            {
                "role_group": "fabric",
                "company": fabric_supplier["company"],
                "location": fabric_supplier["location"],
                "delay_days": _actor_delay("fabric", mock_data),
            }
        )
    if garment_supplier:
        actors.append(
            {
                "role_group": "garment",
                "company": garment_supplier["company"],
                "location": garment_supplier["location"],
                "delay_days": _actor_delay("garment", mock_data),
            }
        )
    if finishing_supplier:
        actors.append(
            {
                "role_group": "finishing",
                "company": finishing_supplier["company"],
                "location": finishing_supplier["location"],
                "delay_days": _actor_delay("finishing", mock_data),
            }
        )

    raw_legs = [
        (fabric_supplier, garment_supplier),
        (garment_supplier, finishing_supplier),
    ]
    legs = []
    transport_cost_total = 0.0
    transport_co2_total = 0.0
    total_delay_days = 0.0

    for source_supplier, destination_supplier in raw_legs:
        if not source_supplier or not destination_supplier:
            continue

        distance_row = db_get_manufacturer_distance_row(
            source_supplier["company"], destination_supplier["company"]
        )
        distance_km = distance_row["distance_km"] if distance_row else None
        leg_delay_days = _transport_delay(distance_km, mock_data)
        leg_cost_chf = _transport_cost(distance_km, total_weight_kg, mock_data)
        leg_co2eq_kg = calculate_transport_emission(
            float(distance_km) if distance_km is not None else 0.0,
            total_weight_kg,
            transport_emission_per_unit,
        )
        transport_cost_total += leg_cost_chf
        transport_co2_total += float(leg_co2eq_kg or 0)
        total_delay_days += leg_delay_days
        legs.append(
            {
                "source_company": source_supplier["company"],
                "source_role_group": source_supplier["role_group"],
                "destination_company": destination_supplier["company"],
                "destination_role_group": destination_supplier["role_group"],
                "distance_km": _safe_round(distance_km),
                "delay_days": _safe_round(leg_delay_days),
                "economic_cost_chf": _safe_round(leg_cost_chf),
                "co2eq_kg": _safe_round(leg_co2eq_kg),
            }
        )

    actor_delays = []
    incoming_delay_by_company = {
        leg["destination_company"]: float(leg["delay_days"]) for leg in legs
    }
    for actor in actors:
        total_actor_delay = float(actor["delay_days"]) + float(
            incoming_delay_by_company.get(actor["company"], 0)
        )
        actor_delays.append(
            {
                "company": actor["company"],
                "role_group": actor["role_group"],
                "delay_days": _safe_round(total_actor_delay),
            }
        )
        total_delay_days += float(actor["delay_days"])

    highest_delay_actor = max(
        actor_delays,
        key=lambda actor: float(actor["delay_days"]),
        default={"company": None, "role_group": None, "delay_days": 0.0},
    )

    return (
        legs,
        actors,
        {
            "transport_cost_total": _safe_round(transport_cost_total),
            "transport_co2_total": _safe_round(transport_co2_total, 3),
            "total_delay_days": _safe_round(total_delay_days),
            "highest_delay_actor": highest_delay_actor,
        },
    )


def get_designer_balance_scenario(
    garment_type_id: int,
    wiser_client: WiserClient,
    material_id: int | None = None,
    fabric_supplier_name: str | None = None,
    garment_supplier_name: str | None = None,
    finishing_supplier_name: str | None = None,
) -> dict:
    mock_data = load_designer_balance_mock_data()
    garment_types = db_get_garment_types()
    garment = next(
        (item for item in garment_types if item["id"] == garment_type_id), None
    )
    if garment is None:
        raise HTTPException(status_code=404, detail="Garment type not found")

    materials = db_get_materials_for_garment(garment_type_id)
    if not materials:
        raise HTTPException(
            status_code=404,
            detail="No materials configured for this garment type",
        )

    selected_material = next(
        (item for item in materials if item["id"] == material_id), None
    )
    if selected_material is None:
        selected_material = materials[0]

    recipe = get_full_garment_recipe(garment_type_id, int(selected_material["id"]))
    if recipe is None:
        raise HTTPException(status_code=404, detail="Garment recipe not found")

    co2_data = get_co2_for_garment(
        garment_type_id, wiser_client, int(selected_material["id"])
    )
    co2_process_details = [
        detail
        for detail in co2_data.processes.details
        if detail.get("process") != "transport inside supply chain"
    ]
    base_process_co2 = sum(
        float(detail.get("emission", 0)) for detail in co2_process_details
    )
    base_fabric_co2 = float(co2_data.fabric_blocks.total_emission)

    supplier_options = {
        "fabric": db_get_manufacturers("fabric"),
        "garment": db_get_manufacturers("garment"),
        "finishing": db_get_manufacturers("finishing"),
    }
    selected_supplier_names = {
        "fabric": _select_default_company(
            supplier_options["fabric"], fabric_supplier_name
        ),
        "garment": _select_default_company(
            supplier_options["garment"], garment_supplier_name
        ),
        "finishing": _select_default_company(
            supplier_options["finishing"], finishing_supplier_name
        ),
    }
    supplier_lookup = {
        role_group: {item["company"]: item for item in options}
        for role_group, options in supplier_options.items()
    }

    fabric_supplier = supplier_lookup["fabric"].get(selected_supplier_names["fabric"])
    garment_supplier = supplier_lookup["garment"].get(
        selected_supplier_names["garment"]
    )
    finishing_supplier = supplier_lookup["finishing"].get(
        selected_supplier_names["finishing"]
    )

    total_weight_kg = sum(float(block.weight_kg or 0) for block in recipe.fabric_blocks)
    selected_material_kg_per_sqm = float(selected_material.get("kg_per_sqm") or 0)
    transport_emission_per_unit = wiser_client.get_emission_per_unit(
        ACTIVITY_ID_TRANSPORT
    )

    supply_chain_legs, supply_chain_actors, transport_summary = (
        _build_supply_chain_legs(
            fabric_supplier,
            garment_supplier,
            finishing_supplier,
            total_weight_kg,
            transport_emission_per_unit,
            mock_data,
        )
    )

    material_mock = _mock_material_data(selected_material["name"], mock_data)
    material_cost_per_kg = float(material_mock.get("cost_per_kg_chf", 0))

    bom_by_block_name: dict[str, dict] = {}
    bop_rows: list[dict] = []
    process_usage: dict[str, dict] = {}

    for fabric_block, block_detail in zip(
        recipe.fabric_blocks, co2_data.fabric_blocks.details
    ):
        sqm_per_unit = (
            float(fabric_block.weight_kg or 0) / selected_material_kg_per_sqm
            if selected_material_kg_per_sqm > 0
            else 0.0
        )
        material_cost = float(fabric_block.weight_kg or 0) * material_cost_per_kg
        if fabric_block.name not in bom_by_block_name:
            bom_by_block_name[fabric_block.name] = {
                "fabric_block": fabric_block.name,
                "quantity": 0,
                "material": selected_material["name"],
                "sqm_per_unit": _safe_round(sqm_per_unit, 3),
                "total_sqm": 0.0,
                "weight_kg": 0.0,
                "economic_cost_chf": 0.0,
                "co2eq_kg": 0.0,
            }

        bom_by_block_name[fabric_block.name]["quantity"] += 1
        bom_by_block_name[fabric_block.name]["total_sqm"] += sqm_per_unit
        bom_by_block_name[fabric_block.name]["weight_kg"] += float(
            fabric_block.weight_kg or 0
        )
        bom_by_block_name[fabric_block.name]["economic_cost_chf"] += material_cost
        bom_by_block_name[fabric_block.name]["co2eq_kg"] += float(
            block_detail.get("emission", 0)
        )

        for process_detail in block_detail.get("production_processes", []):
            process_name = process_detail.get("process", "Unknown")
            process_amount = float(process_detail.get("amount", 0))
            process_emission = float(process_detail.get("emission", 0))
            process_cost = _process_cost(process_name, process_amount, mock_data)
            bop_rows.append(
                {
                    "source": f"Fabric block {fabric_block.name}",
                    "process": process_name,
                    "amount": _safe_round(process_amount, 3),
                    "economic_cost_chf": _safe_round(process_cost),
                    "co2eq_kg": _safe_round(process_emission, 3),
                }
            )
            if process_name.lower() in {
                item["name"].lower() for item in db_get_process_types()
            }:
                process_key = process_name.lower()
                current = process_usage.setdefault(
                    process_key,
                    {"amount": 0.0, "economic_cost_chf": 0.0, "co2eq_kg": 0.0},
                )
                current["amount"] += process_amount
                current["economic_cost_chf"] += process_cost
                current["co2eq_kg"] += process_emission

    for process_detail in co2_process_details:
        process_name = process_detail.get("process", "Unknown")
        process_amount = float(
            process_detail.get("amount", process_detail.get("duration", 0))
        )
        process_emission = float(process_detail.get("emission", 0))
        process_cost = _process_cost(process_name, process_amount, mock_data)
        bop_rows.append(
            {
                "source": "Garment assembly",
                "process": process_name,
                "amount": _safe_round(process_amount, 3),
                "economic_cost_chf": _safe_round(process_cost),
                "co2eq_kg": _safe_round(process_emission, 3),
            }
        )
        process_key = process_name.lower()
        current = process_usage.setdefault(
            process_key,
            {"amount": 0.0, "economic_cost_chf": 0.0, "co2eq_kg": 0.0},
        )
        current["amount"] += process_amount
        current["economic_cost_chf"] += process_cost
        current["co2eq_kg"] += process_emission

    transport_tkm = sum(
        (float(leg.get("distance_km", 0)) * total_weight_kg / 1000.0)
        for leg in supply_chain_legs
    )
    total_transport_co2 = float(transport_summary["transport_co2_total"])
    total_transport_cost = float(transport_summary["transport_cost_total"])
    bop_rows.extend(
        {
            "source": f"{leg['source_company']} -> {leg['destination_company']}",
            "process": "transport inside supply chain",
            "amount": leg["distance_km"],
            "economic_cost_chf": leg["economic_cost_chf"],
            "co2eq_kg": leg["co2eq_kg"],
        }
        for leg in supply_chain_legs
    )

    process_usage["transport"] = {
        "amount": transport_tkm,
        "economic_cost_chf": total_transport_cost,
        "co2eq_kg": total_transport_co2,
    }

    bom_rows = []
    total_material_cost = 0.0
    for row in bom_by_block_name.values():
        row["total_sqm"] = _safe_round(row["total_sqm"], 3)
        row["weight_kg"] = _safe_round(row["weight_kg"], 3)
        row["economic_cost_chf"] = _safe_round(row["economic_cost_chf"])
        row["co2eq_kg"] = _safe_round(row["co2eq_kg"], 3)
        total_material_cost += float(row["economic_cost_chf"])
        bom_rows.append(row)

    process_types = db_get_process_types()
    process_table = []
    total_process_cost = 0.0
    for process_type in process_types:
        process_key = process_type["name"].lower()
        usage = process_usage.get(
            process_key,
            {"amount": 0.0, "economic_cost_chf": 0.0, "co2eq_kg": 0.0},
        )
        total_process_cost += float(usage["economic_cost_chf"])
        process_table.append(
            {
                "process_type": process_type["name"],
                "unit": process_type.get("unit") or "",
                "total_usage_per_garment": _safe_round(usage["amount"], 3),
                "economic_cost_chf": _safe_round(usage["economic_cost_chf"]),
                "co2eq_kg": _safe_round(usage["co2eq_kg"], 3),
            }
        )

    total_economic_cost = total_material_cost + total_process_cost
    total_co2eq = base_fabric_co2 + base_process_co2 + total_transport_co2

    return {
        "garment": garment,
        "material": {
            "id": selected_material["id"],
            "name": selected_material["name"],
            "cost_per_kg_chf": _safe_round(material_cost_per_kg),
            "longevity_wears": int(material_mock.get("longevity_wears", 0)),
        },
        "options": {
            "materials": materials,
            "suppliers": supplier_options,
        },
        "selection": {
            "fabric_supplier": selected_supplier_names["fabric"],
            "garment_supplier": selected_supplier_names["garment"],
            "finishing_supplier": selected_supplier_names["finishing"],
        },
        "summary": {
            "bom_cost_chf": _safe_round(total_material_cost),
            "bop_cost_chf": _safe_round(total_process_cost - total_transport_cost),
            "transport_cost_chf": _safe_round(total_transport_cost),
            "economic_total_chf": _safe_round(total_economic_cost),
            "margin_chf": _safe_round(
                float(garment.get("price_chf") or 0) - total_economic_cost
            ),
            "co2eq_total_kg": _safe_round(total_co2eq, 3),
            "material_and_fabric_co2eq_kg": _safe_round(base_fabric_co2, 3),
            "process_co2eq_kg": _safe_round(base_process_co2, 3),
            "transport_co2eq_kg": _safe_round(total_transport_co2, 3),
            "average_lifetime_wears": int(material_mock.get("longevity_wears", 0)),
            "total_delay_days": transport_summary["total_delay_days"],
            "highest_delay_actor": transport_summary["highest_delay_actor"],
        },
        "bill_of_materials": bom_rows,
        "bill_of_processes": bop_rows,
        "process_table": process_table,
        "supply_chain": {
            "actors": supply_chain_actors,
            "legs": supply_chain_legs,
        },
    }
