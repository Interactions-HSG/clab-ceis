from typing import Optional
from pathlib import Path
import sqlite3
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException, Query
import requests

from db_init import init_sqlite_db
from utils import (
    get_co2,
    get_wiser_token,
    get_transport_emission_per_unit,
    calculate_transport_emission,
)
from location_details import distances_customer_sigmaringen, activity_id_transport
from models import (
    FabricBlockInfo,
    FabricBlockTypeCreate,
    ActivitySearchRequest,
    GarmentRecipeCreate,
    GarmentTypeCreate,
    ProcessTypeCreate,
    ResourceTypeCreate,
)


# Load environment variables from ceis_backend/.env.secrets, regardless of CWD
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env.secrets", override=True)


app = FastAPI()

init_sqlite_db()


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


@app.post("/garment-types")
def create_garment_type(payload: GarmentTypeCreate):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO garment_types (name) VALUES (?)",
            (payload.name,),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "name": payload.name}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Garment type already exists")
    finally:
        conn.close()


@app.get("/garment-types")
def get_garment_types():
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM garment_types")
    garment_types = cursor.fetchall()
    conn.close()
    return [{"id": gt[0], "name": gt[1]} for gt in garment_types]


@app.get("/locations")
def get_locations():
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM locations")
    locations = cursor.fetchall()
    conn.close()
    return [{"id": loc[0], "name": loc[1]} for loc in locations]


@app.delete("/garment-recipes/{garment_type_id}")
def delete_garment_recipe(garment_type_id: int):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM garment_types WHERE id = ?",
            (garment_type_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Garment type not found")

        cursor.execute(
            "DELETE FROM garment_recipe_fabric_blocks WHERE garment_type = ?",
            (garment_type_id,),
        )
        fabric_deleted = cursor.rowcount
        cursor.execute(
            "DELETE FROM garment_recipe_processes WHERE garment_type = ?",
            (garment_type_id,),
        )
        processes_deleted = cursor.rowcount
        if (fabric_deleted + processes_deleted) == 0:
            raise HTTPException(status_code=404, detail="Garment recipe not found")

        conn.commit()
        return {"message": "Garment recipe deleted"}
    finally:
        conn.close()


@app.post("/fabric-block-types")
def create_fabric_block_type(payload: FabricBlockTypeCreate):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO fabric_block_types (name, material, amount_kg, activity_id)
            VALUES (?, ?, ?, ?)
            """,
            (payload.name, payload.material, payload.amount_kg, payload.activity_id),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "name": payload.name}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Fabric block type already exists")
    finally:
        conn.close()


@app.post("/process-types")
def create_process_type(payload: ProcessTypeCreate):
    if not payload.resources:
        raise HTTPException(
            status_code=400, detail="Process type must include at least one resource"
        )

    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO process_types (name) VALUES (?)",
            (payload.name,),
        )
        process_id = cursor.lastrowid

        resource_ids = [res.resource_id for res in payload.resources]
        if resource_ids:
            cursor.execute(
                f"SELECT COUNT(*) FROM resource_types WHERE id IN ({','.join('?' * len(resource_ids))})",
                resource_ids,
            )
            if cursor.fetchone()[0] != len(set(resource_ids)):
                conn.rollback()
                raise HTTPException(status_code=400, detail="Invalid resource id")

        cursor.executemany(
            """
            INSERT INTO process_resource_consumption (process_id, resource_id, amount)
            VALUES (?, ?, ?)
            """,
            [(process_id, res.resource_id, res.amount) for res in payload.resources],
        )
        conn.commit()
        return {"id": process_id, "name": payload.name}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Process type already exists")
    finally:
        conn.close()


@app.post("/resource-types")
def create_resource_type(payload: ResourceTypeCreate):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM resource_types WHERE name = ?",
            (payload.name,),
        )
        if cursor.fetchone():
            raise HTTPException(status_code=409, detail="Resource type already exists")

        cursor.execute(
            """
            INSERT INTO resource_types (name, unit, activity_id)
            VALUES (?, ?, ?)
            """,
            (payload.name, payload.unit, payload.activity_id),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "name": payload.name}
    finally:
        conn.close()


@app.get("/resource-types")
def get_resource_types():
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, unit, activity_id FROM resource_types")
    resource_types = cursor.fetchall()
    conn.close()
    return [
        {
            "id": res_type[0],
            "name": res_type[1],
            "unit": res_type[2],
            "activity_id": res_type[3],
        }
        for res_type in resource_types
    ]


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
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM fabric_block_types")
    fabric_block_types = cursor.fetchall()
    conn.close()
    return [{"id": fb_type[0], "name": fb_type[1]} for fb_type in fabric_block_types]


@app.delete("/fabric-block-types/{type_id}")
def delete_fabric_block_type(type_id: int):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM fabric_block_types WHERE id = ?",
            (type_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Fabric block type not found")

        cursor.execute(
            "DELETE FROM garment_recipe_fabric_blocks WHERE fabric_block_id = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM fabric_blocks_inventory WHERE type_id = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM fabric_block_types WHERE id = ?",
            (type_id,),
        )
        conn.commit()
        return {"message": "Fabric block type deleted"}
    finally:
        conn.close()


@app.get("/process-types")
def get_preparation_types():
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM process_types")
    preparation_types = cursor.fetchall()
    conn.close()
    return [
        {"id": prep_type[0], "name": prep_type[1]} for prep_type in preparation_types
    ]


@app.delete("/process-types/{type_id}")
def delete_process_type(type_id: int):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM process_types WHERE id = ?",
            (type_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Process type not found")

        cursor.execute(
            "DELETE FROM process_resource_consumption WHERE process_id = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM garment_recipe_processes WHERE process_id = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM preparations_used_fabric_blocks WHERE type_id = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM process_types WHERE id = ?",
            (type_id,),
        )
        conn.commit()
        return {"message": "Process type deleted"}
    finally:
        conn.close()


@app.delete("/resource-types/{type_id}")
def delete_resource_type(type_id: int):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM resource_types WHERE id = ?",
            (type_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Resource type not found")

        cursor.execute(
            "DELETE FROM process_resource_consumption WHERE resource_id = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM resource_types WHERE id = ?",
            (type_id,),
        )
        conn.commit()
        return {"message": "Resource type deleted"}
    finally:
        conn.close()


@app.post("/garment-recipes")
def create_garment_recipe(payload: GarmentRecipeCreate):
    if not payload.fabric_blocks:
        raise HTTPException(
            status_code=400,
            detail="Garment recipe must include at least one fabric block",
        )

    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM garment_types WHERE id = ?",
            (payload.garment_type_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=400, detail="Invalid garment type")

        fabric_block_ids = [fb.type_id for fb in payload.fabric_blocks]
        cursor.execute(
            f"SELECT COUNT(*) FROM fabric_block_types WHERE id IN ({','.join('?' * len(fabric_block_ids))})",
            fabric_block_ids,
        )
        if cursor.fetchone()[0] != len(set(fabric_block_ids)):
            raise HTTPException(status_code=400, detail="Invalid fabric block type")

        processes = payload.processes or []
        if processes:
            process_ids = [proc.process_id for proc in processes]
            cursor.execute(
                f"SELECT COUNT(*) FROM process_types WHERE id IN ({','.join('?' * len(process_ids))})",
                process_ids,
            )
            if cursor.fetchone()[0] != len(set(process_ids)):
                raise HTTPException(status_code=400, detail="Invalid process type")

        for fb in payload.fabric_blocks:
            if fb.amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Fabric block amounts must be greater than 0",
                )
        for proc in processes:
            if proc.time <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Process time must be greater than 0",
                )

        cursor.execute(
            "DELETE FROM garment_recipe_fabric_blocks WHERE garment_type = ?",
            (payload.garment_type_id,),
        )
        cursor.execute(
            "DELETE FROM garment_recipe_processes WHERE garment_type = ?",
            (payload.garment_type_id,),
        )

        cursor.executemany(
            """
            INSERT INTO garment_recipe_fabric_blocks
            (garment_type, fabric_block_id, amount)
            VALUES (?, ?, ?)
            """,
            [
                (payload.garment_type_id, fb.type_id, int(fb.amount))
                for fb in payload.fabric_blocks
            ],
        )

        if processes:
            cursor.executemany(
                """
                INSERT INTO garment_recipe_processes
                (garment_type, process_id, time)
                VALUES (?, ?, ?)
                """,
                [
                    (payload.garment_type_id, proc.process_id, proc.time)
                    for proc in processes
                ],
            )

        conn.commit()
        return {
            "message": "Garment recipe saved",
            "garment_type_id": payload.garment_type_id,
        }
    finally:
        conn.close()


@app.post("/fabric-blocks")
async def create_fabric_block(fabric_block: FabricBlockInfo):
    print("Received fabric block:", fabric_block)
    co2eq = None  # Placeholder
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO fabric_blocks_inventory (type_id, co2eq, location_id)
        VALUES (?, ?, ?)
        """,
        (fabric_block.type_id, co2eq, fabric_block.location_id),
    )
    fabric_block_id = cursor.lastrowid
    if not fabric_block_id:
        conn.close()
        return {"error": "Invalid fabric block type"}

    preparations = fabric_block.processes or []
    if preparations:
        cursor.executemany(
            """
            INSERT INTO preparations_used_fabric_blocks (type_id, amount, fabric_block_id)
            VALUES (?, ?, ?)
            """,
            [(prep.type_id, prep.time, fabric_block_id) for prep in preparations],
        )

    conn.commit()
    conn.close()
    return {"message": "Fabric block created successfully", "id": fabric_block_id}


@app.get("/fabric-blocks")
def get_fabric_blocks(type: Optional[str] = None):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        """
                   SELECT fbi.id, fbi.type_id, fbi.co2eq, fbi.garment_id, l.name as location_name
                   FROM fabric_blocks_inventory fbi
                   LEFT JOIN locations l ON fbi.location_id = l.id
                   WHERE fbi.type_id = ? OR ? IS NULL
                   """,
        (type, type),
    )
    fabric_blocks_data = cursor.fetchall()
    print("fabric_blocks_data:", fabric_blocks_data)

    fabric_blocks = []
    for fb in fabric_blocks_data:
        fb_id, fb_type, fb_co2eq, garment_id, location_name = fb
        cursor.execute(
            "SELECT name FROM fabric_block_types WHERE id = ?",
            (fb_type,),
        )
        fb_type_name = cursor.fetchone()
        fb_type_name = fb_type_name[0] if fb_type_name else None
        cursor.execute(
            """
            SELECT pt.name, pufb.amount
            FROM preparations_used_fabric_blocks pufb
            JOIN process_types pt ON pufb.type_id = pt.id
            WHERE pufb.fabric_block_id = ?
            """,
            (fb_id,),
        )
        preparations_data = cursor.fetchall()
        preparations = [{"type": p[0], "amount": p[1]} for p in preparations_data]
        fabric_blocks.append(
            {
                "id": fb_id,
                "type": fb_type_name,
                "co2eq": fb_co2eq,
                "garment_id": garment_id,
                "location": location_name,
                "preparations": preparations,
            }
        )
    conn.close()
    return fabric_blocks


@app.delete("/fabric-blocks/{fabric_block_id}")
def delete_fabric_block(fabric_block_id: int):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM fabric_blocks_inventory WHERE id = ?",
            (fabric_block_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Fabric block not found")

        cursor.execute(
            "DELETE FROM preparations_used_fabric_blocks WHERE fabric_block_id = ?",
            (fabric_block_id,),
        )
        cursor.execute(
            "DELETE FROM fabric_blocks_inventory WHERE id = ?",
            (fabric_block_id,),
        )
        conn.commit()
        return {"message": "Fabric block deleted"}
    finally:
        conn.close()


def _get_transport_emission_per_unit() -> float | None:
    token = get_wiser_token()
    if not token or isinstance(token, dict):
        return None

    activity_url = "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.12-cutoff/activity/"
    return get_transport_emission_per_unit(token, activity_url)


@app.get("/co2/repair")
def get_repair_co2(amount_kg: float = Query(1.0, description="Amount in kg")):
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

    return {"amount_kg": amount_kg, "scenarios": scenarios}


@app.get("/co2/{garment_type_id}")
def get_co2_for_garment(garment_type_id: int):
    co2_data = get_co2(garment_type_id)
    return co2_data
