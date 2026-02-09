from typing import Optional, Mapping, cast
from db_init import init_sqlite_db
from utils import get_bindings, get_co2
from fastapi import FastAPI, Request, HTTPException
import requests
import sqlite3
import json
from models import (
    Co2Response,
    FabricBlock,
    FabricBlockInfo,
    FabricBlockTypeCreate,
    GarmentRecipeCreate,
    GarmentTypeCreate,
    ProcessTypeCreate,
    ResourceTypeCreate,
)

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


@app.get("/croptop")
def get_info_croptop():
    try:
        bindings = get_bindings("getTopData")

        print(bindings)
        data = [
            {
                "recipe": item.get("recipeName", {}).get("value"),
                "fabricBlockDesign": item.get("fabricBlockDesignName", {}).get("value"),
                "requiredAmount": int(item.get("requiredAmount", {}).get("value", 0)),
                "availableAmount": int(item.get("availableAmount", {}).get("value", 0)),
            }
            for item in bindings
        ]
        print("data", data)
        return {}
    except Exception as e:
        return {"error": str(e)}


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


@app.post("/fabric-block")
async def create_fabric_block(fabric_block: FabricBlockInfo):
    print("Received fabric block:", fabric_block)
    co2eq = None  # Placeholder
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO fabric_blocks_inventory (type_id, co2eq)
        VALUES (?, ?)
        """,
        (fabric_block.type_id, co2eq),
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
                   SELECT id, type_id, co2eq, garment_id FROM fabric_blocks_inventory
                   WHERE type_id = ? OR ? IS NULL
                   """,
        (type, type),
    )
    fabric_blocks_data = cursor.fetchall()
    print("fabric_blocks_data:", fabric_blocks_data)

    fabric_blocks = []
    for fb in fabric_blocks_data:
        fb_id, fb_type, fb_co2eq, garment_id = fb
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
                "preparations": preparations,
            }
        )
    conn.close()
    return fabric_blocks


@app.get("/co2/croptop")
def get_co2_croptop():
    co2_data = get_co2("croptop")
    return co2_data


@app.get("/co2/skirt")
def get_co2_skirt():
    co2_data = get_co2("skirt")
    return co2_data


@app.get("/test")
def test_endpoint():

    url = "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.11-cutoff/activity/3878/"

    headers = {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJralFLN3FFYXl1cS1mM1NLU2FiaXV4Z3lpRG5IRnlSWXVQc3c3cEQyVDVFIn0.eyJleHAiOjE3NzAwNTQ3MzEsImlhdCI6MTc3MDA1NDQzMSwianRpIjoiY2Y1MWViNTYtZTY5MS00ZjBiLWEwNDgtMGQzNDgzOTIzNWI3IiwiaXNzIjoiaHR0cHM6Ly9hdXRoLndpc2VyLmVoZWFsdGguaGV2cy5jaC9yZWFsbXMvd2lzZXIiLCJhdWQiOlsic3A0LWtnIiwic3A1LWJhY2tlbmQtdGVzdCIsIndpc2VyLXNwMy1hcGkiLCJzcDUtc3dpc3MtcHJvZHVjdGlvbiIsInNwNS1zd2lzcy1wcm9kdWN0aW9uLXRlc3QiLCJzcDYtY2l0eS1pY3QiLCJhY2NvdW50Iiwic3A3LWRhdGEtY2VudGVycyJdLCJzdWIiOiIxN2E5ODUxMC0yMmRhLTQwZmMtYmJhNS0xMDYwMmQ2MWFkNzEiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJ3aXNlci1hcGktcHVibGljIiwic2Vzc2lvbl9zdGF0ZSI6ImYwNjFiZjJiLTkxMGQtNGMyYi1iNDA5LTc0ZmNiNWM0ZWIyZCIsImFjciI6IjEiLCJhbGxvd2VkLW9yaWdpbnMiOlsiLyoiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwiZGVmYXVsdC1yb2xlcy13aXNlciIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsic3A1LXN3aXNzLXByb2R1Y3Rpb24iOnsicm9sZXMiOlsiUk9MRV9TUDVfQURNSU4iXX0sInNwNS1zd2lzcy1wcm9kdWN0aW9uLXRlc3QiOnsicm9sZXMiOlsiUk9MRV9TUDVfQURNSU4iXX0sInNwNi1jaXR5LWljdCI6eyJyb2xlcyI6WyJST0xFX1NQNl9BRE1JTiJdfSwid2lzZXItc3AzLWFwaSI6eyJyb2xlcyI6WyJwbGFzdGljc2V1cm9wZV8qIiwiZWNvaW52ZW50XyoiLCJ1dmVrXyoiLCJrYm9iXyoiXX0sInNwNC1rZyI6eyJyb2xlcyI6WyJST0xFX0FETUlOIiwiUkVBRF9SRVBPXyoiXX0sImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfSwic3A3LWRhdGEtY2VudGVycyI6eyJyb2xlcyI6WyJST0xFX1NQN19BRE1JTiJdfX0sInNjb3BlIjoicHJvZmlsZSBlbWFpbCIsInNpZCI6ImYwNjFiZjJiLTkxMGQtNGMyYi1iNDA5LTc0ZmNiNWM0ZWIyZCIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJyb2xlcyI6WyJST0xFX0FETUlOIiwiUkVBRF9SRVBPXyoiXSwibmFtZSI6IlNpbWVvbiBQaWx6Iiwib3JnYW5pemF0aW9ucyI6W3siZ3JvdXBfaWQiOiI3YTU0ZWVkMi03NzY3LTQwN2MtOGFiNi1mNTliYmRmODEzOTciLCJjb21wYW55X25hbWUiOiJVbml2ZXJzaXTDpHQgU3QuIEdhbGxlbiIsImF1ZGl0b3JfZ3JvdXAiOiI1MzBlOWU3My03N2IwLTQ2NzktYTcwZS1kMjJkNzgzMjcxYzcifV0sImdyb3VwX25hbWVzIjpbIi9JTlRFUk5BTC9VTklWRVJTSVRZX1NUX0dBTExFTi9BRE1JTl9HUk9VUCIsIi9JTlRFUk5BTC9VTklWRVJTSVRZX1NUX0dBTExFTiJdLCJhZG1pbl9ncm91cF9pZHMiOlsiN2E1NGVlZDItNzc2Ny00MDdjLThhYjYtZjU5YmJkZjgxMzk3Il0sInByZWZlcnJlZF91c2VybmFtZSI6InNpbWVvbiIsImdpdmVuX25hbWUiOiJTaW1lb24iLCJmYW1pbHlfbmFtZSI6IlBpbHoiLCJtYWluX29yZ2FuaXphdGlvbl9pZCI6IjdhNTRlZWQyLTc3NjctNDA3Yy04YWI2LWY1OWJiZGY4MTM5NyIsImVtYWlsIjoic2ltZW9uLnBpbHpAdW5pc2cuY2gifQ.V5bZgTz86CxSDtI1hCwkDcXKmrlDXmQdtdyOjNrWQGlPJGULbT7ULqI_CzVRt967rAUwljTg8xyrbnCzYiV_zWOggIZHdiBtdq1idKBB7imlGE5t-wn7JFyV8wv0HF4wBuSdj5Ri3w9Pe5TyEV4hr9WmXi_MbSu33O4cWpFb-duBxwXYE6yVH_SbTrXssf5D4HN2K5PHv5g-K0WinffY460GNRnFl_lbbgCXyy9ZbPY9D1vUxx6dMuabsJZOKTOUKFsYBRCI7_QhqLPXMtH15StbgTJbTB52hdMqGlkA1OPPGYfIuU7Qmt3olDpKVlvOrI8lD_OCgcbioan6QxeeiQ",
    }

    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.text)
