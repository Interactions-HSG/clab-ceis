import requests
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query

from ceis_backend.db_init import init_sqlite_db
from ceis_backend.config import BACKEND_HOST, BACKEND_PORT
from ceis_backend.utils import (
    get_co2,
    get_wiser_token,
    get_emission_per_unit,
    calculate_transport_emission,
    db_create_garment_type,
    db_get_garment_types,
    db_get_locations,
    db_delete_garment_recipe,
    db_create_fabric_block_type,
    db_create_process_type,
    db_get_fabric_block_types,
    db_delete_fabric_block_type,
    db_get_process_types,
    db_delete_process_type,
    db_create_garment_recipe,
    db_create_fabric_block,
    db_get_fabric_blocks,
    db_delete_fabric_block,
    db_get_replacement_fabric_blocks_emissions,
)
from ceis_backend.location_details import (
    distances_customer_sigmaringen,
    activity_id_transport,
)
from ceis_backend.models import (
    FabricBlockInfo,
    FabricBlockTypeCreate,
    ActivitySearchRequest,
    GarmentRecipeCreate,
    GarmentTypeCreate,
    ProcessTypeCreate,
)

app = FastAPI()


@app.on_event("startup")
def startup_event():
    """Initialize the database when the app starts."""
    init_sqlite_db()


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.post("/garment-types")
def create_garment_type(payload: GarmentTypeCreate):
    return db_create_garment_type(payload.name)


@app.get("/garment-types")
def get_garment_types():
    return db_get_garment_types()


@app.get("/locations")
def get_locations():
    return db_get_locations()


@app.delete("/garment-recipes/{garment_type_id}")
def delete_garment_recipe(garment_type_id: int):
    return db_delete_garment_recipe(garment_type_id)


@app.post("/fabric-block-types")
def create_fabric_block_type(payload: FabricBlockTypeCreate):
    return db_create_fabric_block_type(
        payload.name, payload.material, payload.amount_kg, payload.activity_id
    )


@app.post("/process-types")
def create_process_type(payload: ProcessTypeCreate):
    return db_create_process_type(payload.name, payload.unit, payload.activity_id)


@app.post("/activity-search")
def activity_search(payload: ActivitySearchRequest):
    if not payload.query:
        raise HTTPException(status_code=400, detail="Query is required")

    token = get_wiser_token()
    print("token:", token)
    if isinstance(token, dict):
        raise HTTPException(status_code=500, detail="Failed to fetch Wiser token")

    url = "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.12-cutoff/activity/search/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = requests.post(url, headers=headers, json={"query": payload.query})
    if response.status_code != 200:
        print("Activity search failed")
        print("Request url:", url)
        print("Query:", payload.query)
        print("Status:", response.status_code)
        print("Response headers:", dict(response.headers))
        try:
            print("Response body:", response.json())
        except Exception:
            print("Response body (text):", response.text)
        raise HTTPException(
            status_code=response.status_code,
            detail="Activity search failed",
        )

    data = response.json()
    results = []
    for item in data.get("search_results", []):
        location = item.get("location", {}) or {}
        results.append(
            {
                "id": item.get("id"),
                "location": location.get("code"),
                "name": item.get("name"),
                "reference_product": item.get("reference_product"),
            }
        )

    return {"results": results}


@app.get("/fabric-block-types")
def get_fabric_block_types():
    return db_get_fabric_block_types()


@app.delete("/fabric-block-types/{type_id}")
def delete_fabric_block_type(type_id: int):
    return db_delete_fabric_block_type(type_id)


@app.get("/process-types")
def get_preparation_types():
    return db_get_process_types()


@app.delete("/process-types/{type_id}")
def delete_process_type(type_id: int):
    return db_delete_process_type(type_id)


@app.post("/garment-recipes")
def create_garment_recipe(payload: GarmentRecipeCreate):
    return db_create_garment_recipe(
        payload.garment_type_id,
        payload.fabric_blocks,
        payload.processes or [],
    )


@app.post("/fabric-blocks")
async def create_fabric_block(fabric_block: FabricBlockInfo):
    print("Received fabric block:", fabric_block)
    return db_create_fabric_block(
        fabric_block.type_id,
        fabric_block.location_id,
        fabric_block.processes or [],
    )


@app.get("/fabric-blocks")
def get_fabric_blocks(type: Optional[str] = None):
    return db_get_fabric_blocks(type)


@app.delete("/fabric-blocks/{fabric_block_id}")
def delete_fabric_block(fabric_block_id: int):
    return db_delete_fabric_block(fabric_block_id)


def _get_transport_emission_per_unit() -> float | None:
    token = get_wiser_token()
    if not token or isinstance(token, dict):
        return None

    return get_emission_per_unit(token, activity_id_transport)


@app.get("/co2/repair")
def get_repair_co2(
    amount_kg: float = Query(None, description="Amount in kg"),
    replacements: Optional[str] = Query(
        None, description="Comma-separated list of fabric block types to replace"
    ),
):
    if not amount_kg or amount_kg <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount_kg value")

    per_unit_emission = _get_transport_emission_per_unit()

    distance_bucharest = distances_customer_sigmaringen.get("Bucharest")
    distance_st_gallen = distances_customer_sigmaringen.get("St. Gallen")

    scenarios = [
        {
            "use_case": "Self repair (materials shipped)",
            "route": "Bucharest -> Sigmaringen",
            "distance_km": distance_bucharest,
            "co2_kg": (
                calculate_transport_emission(
                    distance_bucharest, amount_kg, per_unit_emission
                )
                if distance_bucharest is not None
                else None
            ),
        },
        {
            "use_case": "Repair at shop",
            "route": "Sigmaringen -> St. Gallen -> Sigmaringen",
            "distance_km": (
                distance_st_gallen * 2 if distance_st_gallen is not None else None
            ),
            "co2_kg": (
                calculate_transport_emission(
                    float(distance_st_gallen * 2),
                    amount_kg,
                    per_unit_emission,
                )
                if distance_st_gallen is not None
                else None
            ),
        },
        {
            "use_case": "Send to manufacturer",
            "route": "Sigmaringen -> Bucharest -> Sigmaringen",
            "distance_km": (
                distance_bucharest * 2 if distance_bucharest is not None else None
            ),
            "co2_kg": (
                calculate_transport_emission(
                    float(distance_bucharest * 2),
                    amount_kg,
                    per_unit_emission,
                )
                if distance_bucharest is not None
                else None
            ),
        },
    ]

    replacement_names: list[str] = []
    if replacements:
        replacement_names = [
            name.strip() for name in replacements.split(",") if name.strip()
        ]

    token = get_wiser_token()
    if isinstance(token, dict):
        raise HTTPException(status_code=500, detail="Failed to fetch Wiser token")

    emission_cache: dict[int, float | None] = {}
    replacement_fabric_blocks = db_get_replacement_fabric_blocks_emissions(
        replacement_names, token, emission_cache
    )

    return {
        "amount_kg": amount_kg,
        "scenarios": scenarios,
        "replacement_fabric_blocks": replacement_fabric_blocks,
    }


@app.get("/co2/{garment_type_id}")
def get_co2_for_garment(garment_type_id: int):
    co2_data = get_co2(garment_type_id)
    return co2_data


def main():
    uvicorn.run(
        "ceis_backend.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,
    )


if __name__ == "__main__":
    main()
