from __future__ import annotations
import requests
import config

from ceis_backend.models import GarmentCo2Response


def fetch_fabric_blocks():
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/fabric-blocks")

        if resp.status_code != 200:
            return []

        backend_data = resp.json()

        for block in backend_data:
            processes = block.get("processes", [])

            if isinstance(processes, list):
                block["processes"] = ", ".join(
                    f"{p.get('type','')}({p.get('amount')})" for p in processes
                )
            else:
                block["processes"] = str(processes)

        return [
            block
            for block in backend_data
            if block.get("garment_id") in (None, "")
        ]

    except Exception:
        return []


def fetch_garment_types():
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/garment-types")
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


def fetch_materials() -> list[dict]:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/materials")
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


def fetch_materials_for_garment(garment_type_id: int) -> list[dict]:
    try:
        resp = requests.get(
            f"{config.BACKEND_API_URL}/garment-types/{garment_type_id}/materials"
        )
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


def fetch_strategy_progress() -> dict:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/strategy-progress")
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


def fetch_supply_chain() -> dict:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/supply-chain", timeout=30)
        if resp.status_code != 200:
            return {"nodes": [], "edges": []}
        return resp.json()
    except Exception:
        return {"nodes": [], "edges": []}


def fetch_resource_events(**filters) -> list[dict]:
    try:
        params = {key: value for key, value in filters.items() if value is not None}
        resp = requests.get(
            f"{config.BACKEND_API_URL}/resource-events",
            params=params,
            timeout=30,
        )
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


def fetch_repairs() -> list[dict]:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/repairs", timeout=30)
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


def fetch_orders() -> list[dict]:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/orders", timeout=30)
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


def fetch_returned_garments() -> list[dict]:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/returned-garments", timeout=30)
        if resp.status_code != 200:
            return []
        return resp.json()
    except Exception:
        return []


def disassemble_returned_garment(garment_id: int) -> dict:
    try:
        resp = requests.post(
            f"{config.BACKEND_API_URL}/returned-garments/{garment_id}/disassemble",
            timeout=30,
        )
        if resp.status_code != 200:
            payload = resp.json()
            return {"error": payload.get("detail", "Unable to disassemble garment")}
        return resp.json()
    except Exception as error:
        return {"error": str(error)}


def fetch_returned_garment_alternatives(
    garment_id: int,
    distance_km: float,
    use_higher_electricity_factor: bool = False,
) -> dict:
    try:
        resp = requests.get(
            f"{config.BACKEND_API_URL}/returned-garments/{garment_id}/return-alternatives",
            params={
                "distance_km": distance_km,
                "use_higher_electricity_factor": use_higher_electricity_factor,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            payload = resp.json()
            return {"error": payload.get("detail", "Unable to calculate alternatives")}
        return resp.json()
    except Exception as error:
        return {"error": str(error)}


def ship_order(order_id: int) -> dict:
    try:
        resp = requests.post(
            f"{config.BACKEND_API_URL}/orders/{order_id}/ship",
            timeout=30,
        )
        if resp.status_code != 200:
            payload = resp.json()
            return {"error": payload.get("detail", "Unable to ship order")}
        return resp.json()
    except Exception as error:
        return {"error": str(error)}


def fetch_designer_balance_options() -> dict:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/designer-balance/options")
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


def fetch_designer_garment_reference() -> dict:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/designer-garment/reference")
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


def fetch_designer_balance_scenario(
    garment_type_id: int,
    material_id: int,
    fabric_supplier: str | None,
    garment_supplier: str | None,
) -> dict:
    try:
        resp = requests.get(
            f"{config.BACKEND_API_URL}/designer-balance/{garment_type_id}",
            params={
                "material_id": material_id,
                "fabric_supplier": fabric_supplier,
                "garment_supplier": garment_supplier,
            },
        )
        if resp.status_code != 200:
            return {}
        return resp.json()
    except Exception:
        return {}


def get_co2(garment_type_id: int, material_id: int) -> GarmentCo2Response | None:
    try:
        resp = requests.get(
            f"{config.BACKEND_API_URL}/co2/{garment_type_id}",
            params={"material_id": material_id},
        )
        if resp.status_code != 200:
            return None

        data = resp.json()
        return GarmentCo2Response(**data)

    except Exception as e:
        print(e)
        return None
