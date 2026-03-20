import requests
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException

from ceis_backend.db_init import init_sqlite_db
from ceis_backend.config import BACKEND_HOST, BACKEND_PORT
from ceis_backend.utils import (
    get_co2_for_garment,
    get_emission_per_unit,
    calculate_transport_emission,
    build_scenario_activities,
    calculate_replacement_fabric_blocks_emissions,
)
from ceis_backend.wiser_bridge import get_wiser_token
from ceis_backend.queries import (
    db_create_garment_type,
    db_get_garment_types,
    db_get_locations,
    db_get_materials,
    db_get_materials_for_garment,
    db_upsert_material,
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
    get_full_garment_recipe,
)
from ceis_backend.data.location_details import (
    distances_customer_sigmaringen,
    activity_id_transport,
)
from ceis_backend.models import (
    SecondLifeFabricBlockInfo,
    FabricBlockTypeCreate,
    ActivitySearchRequest,
    GarmentRecipeCreate,
    GarmentTypeCreate,
    MaterialCreate,
    ProcessTypeCreate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    init_sqlite_db()
    yield


app = FastAPI(lifespan=lifespan)


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


@app.get("/materials")
def get_materials():
    return db_get_materials()


@app.get("/garment-types/{garment_type_id}/materials")
def get_materials_for_garment(garment_type_id: int):
    return db_get_materials_for_garment(garment_type_id)


@app.post("/materials")
def upsert_material(payload: MaterialCreate):
    return db_upsert_material(payload.name, payload.kg_per_sqm, payload.activity_id)


@app.delete("/garment-recipes/{garment_type_id}")
def delete_garment_recipe(garment_type_id: int):
    return db_delete_garment_recipe(garment_type_id)


@app.post("/fabric-block-types")
def create_fabric_block_type(payload: FabricBlockTypeCreate):
    return db_create_fabric_block_type(payload.name, payload.sqm)


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
        payload.garment_type_name,
        payload.fabric_blocks,
        payload.materials or [],
        payload.processes or [],
    )


@app.post("/fabric-blocks")
async def create_fabric_block(fabric_block: SecondLifeFabricBlockInfo):
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


def _get_transport_emission_per_unit(token: str) -> float | None:
    if not token or isinstance(token, dict):
        return None

    return get_emission_per_unit(token, activity_id_transport)


@app.get("/scenarios")
def get_co2_scenarios():
    # Hardcoded values for crop top repair scenario
    replacements = ["64x40"]
    # use hemp as the material for now
    materials = get_materials()
    hemp_material = next((m for m in materials if m["name"].lower() == "hemp"), None)
    if not hemp_material:
        raise HTTPException(status_code=500, detail="Hemp material not found")
    selected_material_id = hemp_material["id"]

    recipe = get_full_garment_recipe(1, selected_material_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Garment recipe not found")
    amount_kg = 0.0
    for block in recipe.fabric_blocks:
        block_weight_kg = block.weight_kg
        if block_weight_kg is None:
            raise HTTPException(
                status_code=500,
                detail=(
                    "Failed to resolve fabric block weight for "
                    f"'{block.name}' and material '{block.material}'"
                ),
            )
        amount_kg += block_weight_kg

    wiser_token = get_wiser_token()
    per_unit_emission = _get_transport_emission_per_unit(wiser_token)

    distance_bucharest = distances_customer_sigmaringen.get("Bucharest")
    distance_st_gallen = distances_customer_sigmaringen.get("St. Gallen")

    emission_cache: dict[int, float | None] = {}
    replacement_fabric_blocks_data = calculate_replacement_fabric_blocks_emissions(
        replacements, wiser_token, emission_cache, selected_material_id
    )

    # Calculate total weight of replacement fabric blocks
    replacement_blocks_weight_kg = sum(
        detail.get("amount_kg", 0)
        for detail in replacement_fabric_blocks_data.get("details", [])
    )

    scenarios = [
        {
            "label": "Self repair (materials shipped)",
            "activities": build_scenario_activities(
                distance_bucharest,
                replacement_blocks_weight_kg,
                per_unit_emission,
                replacement_fabric_blocks_data,
            ),
        },
        {
            "label": "Repair at shop",
            "activities": build_scenario_activities(
                (
                    float(distance_st_gallen * 2)
                    if distance_st_gallen is not None
                    else None
                ),
                amount_kg,
                per_unit_emission,
                replacement_fabric_blocks_data,
            ),
        },
        {
            "label": "Send to manufacturer",
            "activities": build_scenario_activities(
                (
                    float(distance_bucharest * 2)
                    if distance_bucharest is not None
                    else None
                ),
                amount_kg,
                per_unit_emission,
                replacement_fabric_blocks_data,
            ),
        },
    ]

    # Add "Buy New" scenario using garment type 1
    buy_new_co2_data = get_co2_for_garment(1, wiser_token, selected_material_id)
    buy_new_activity_map: dict[str, float] = {}

    # Add transport to customer
    if distance_bucharest is not None:
        transport_to_customer_emission = calculate_transport_emission(
            distance_bucharest, amount_kg, per_unit_emission
        )
        if transport_to_customer_emission is not None:
            buy_new_activity_map["Transport To Customer"] = (
                transport_to_customer_emission
            )

    # Aggregate fabric block activities by process name
    for detail in buy_new_co2_data.fabric_blocks.details:
        # Add material emission under the fabric block name
        material_emission = detail.get("material_emission", 0)
        if material_emission > 0:
            buy_new_activity_map["Garment Material"] = (
                buy_new_activity_map.get("Garment Material", 0) + material_emission
            )

        # Aggregate production processes by process name
        for process in detail.get("production_processes", []):
            process_name = f"Garment {process.get('process', 'Unknown Process')}"
            process_emission = process.get("emission", 0)
            buy_new_activity_map[process_name] = (
                buy_new_activity_map.get(process_name, 0) + process_emission
            )

    # Aggregate assembly process activities by process name
    for detail in buy_new_co2_data.processes.details:
        process_name = f"Garment {detail.get('process', 'Unknown Process')}"
        process_emission = detail.get("emission", 0)
        buy_new_activity_map[process_name] = (
            buy_new_activity_map.get(process_name, 0) + process_emission
        )

    buy_new_activities = [
        {
            "name": name,
            "costs": {
                "economic": 0,
                "co2_kg": emission,
            },
        }
        for name, emission in sorted(buy_new_activity_map.items())
    ]

    scenarios.append(
        {
            "label": "Buy New",
            "activities": buy_new_activities,
        }
    )

    return scenarios


@app.get("/co2/{garment_type_id}")
def get_co2_for_garment_endpoint(garment_type_id: int, material_id: int):
    wiser_token = get_wiser_token()
    co2_data = get_co2_for_garment(garment_type_id, wiser_token, material_id)
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
