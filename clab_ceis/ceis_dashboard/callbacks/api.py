from __future__ import annotations

import requests

import config
from ceis_backend.models import Co2Response
# from clab_ceis.ceis_backend.models import Co2Response


def fetch_fabric_blocks():
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/fabric-blocks")

        if resp.status_code != 200:
            return []

        backend_data = resp.json()

        for block in backend_data:
            preps = block.get("preparations", [])

            if isinstance(preps, list):
                block["preparations"] = ", ".join(
                    f"{p.get('type','')}({p.get('amount',0)})" for p in preps
                )
            else:
                block["preparations"] = str(preps)

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


def get_co2(garment_type_id: int) -> Co2Response | None:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/co2/{garment_type_id}")
        if resp.status_code != 200:
            return None

        data = resp.json()
        return Co2Response(**data)

    except Exception as e:
        print(e)
        return None
