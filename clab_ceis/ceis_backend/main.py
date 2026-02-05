from typing import Optional, Mapping, cast
from db_init import init_sqlite_db
from utils import get_bindings, get_co2
from fastapi import FastAPI, Request, HTTPException
import requests
import sqlite3
import json
from models import Co2Response, FabricBlock, FabricBlockInfo

app = FastAPI()

init_sqlite_db()


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}


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


