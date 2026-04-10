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

        return backend_data

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


def fetch_designer_balance_options() -> dict:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/designer-balance/options")
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
    finishing_supplier: str | None,
) -> dict:
    try:
        resp = requests.get(
            f"{config.BACKEND_API_URL}/designer-balance/{garment_type_id}",
            params={
                "material_id": material_id,
                "fabric_supplier": fabric_supplier,
                "garment_supplier": garment_supplier,
                "finishing_supplier": finishing_supplier,
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
