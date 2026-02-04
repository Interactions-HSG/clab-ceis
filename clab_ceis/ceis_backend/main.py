from typing import Optional
from db_init import init_sqlite_db
from utils import get_bindings
from fastapi import FastAPI, Request
import requests
import sqlite3
import json
from models import FabricBlock

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

    # return {
    #     "alternatives": [
    #         {
    #             "price": 25,
    #             "co2eq": 33,
    #             "timestamp": 1707985660,
    #         },
    #         {
    #             "price": 40,
    #             "co2eq": 20,
    #             "timestamp": 1708985660,
    #         },
    #     ]
    # }


@app.post("/fabric-block")
async def create_fabric_block(fabric_block: FabricBlock):
    print("Received fabric block:", fabric_block)
    co2eq = fabric_block.co2eq if fabric_block.co2eq is not None else None
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

    preparations = fabric_block.preparations or []
    if preparations:
        cursor.executemany(
            """
            INSERT INTO preparations_used_fabric_blocks (type_id, amount, fabric_block_id)
            VALUES (?, ?, ?)
            """,
            [(prep.type_id, prep.amount, fabric_block_id) for prep in preparations],
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
        print("preparations_data:", preparations_data)
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


def get_wiser_token():
    url = (
        "https://auth.wiser.ehealth.hevs.ch/realms/wiser/protocol/openid-connect/token"
    )
    payload = {
        "grant_type": "password",
        "client_id": "wiser-api-public",
        "username": "simeon",
        "password": "meWdis-sikfup-0josgi",
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        json = response.json()
        return json["access_token"]
    except Exception as e:
        return {"error": str(e)}


def get_recipe_for_fabric_block(fabric_block: str):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT material, activity_id, amount_kg FROM fabric_block_types WHERE name = ?",
        (fabric_block,),
    )
    result = cursor.fetchone()
    if result:
        material, activity_id, amount_kg = result
        return material, activity_id, amount_kg
    return None, None, 0


def get_resource_data_for_process(process: str) -> Optional[list[tuple[str, float]]]:
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT rt.activity_id, prc.amount
        FROM process_types pt
        JOIN process_resource_consumption prc ON prc.process_id = pt.id
        JOIN resource_types rt ON prc.resource_id = rt.id
        WHERE pt.name = ?
        """,
        (process,),
    )
    result = cursor.fetchall()
    conn.close()
    if result:
        return [(row[0], row[1]) for row in result]
    return None


def get_co2(garment_type: str) -> dict[str, object]:
    wiser_token = get_wiser_token()
    print("wiser_token", wiser_token)

    total_emission = 0
    emission_details = {"fabric_blocks": [], "processes": []}
    recipe = None
    if garment_type == "croptop":
        recipe = get_garment_recipe("croptop")
    elif garment_type == "skirt":
        recipe = get_garment_recipe("skirt")
    else:
        return {"error": "Invalid garment type"}
    if recipe is None:
        return {"error": "Recipe not found for garment type"}
    print("recipe", recipe)

    activity_url = "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.11-cutoff/activity/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {wiser_token}",
    }
    for fabric_block in recipe["fabric_blocks"]:
        print("fabric block", fabric_block)
        material, activity_id, amount = get_recipe_for_fabric_block(fabric_block)

        url = f"{activity_url}{activity_id}/"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            json = response.json()
        except Exception as e:
            print("error", str(e))
            return {"error": str(e)}
        emission = next(
            (
                item["emissions"]
                for item in json["lcia_results"]
                if item["method"]["name"] == "IPCC 2021"
            ),
            None,
        )
        emission_details["fabric_blocks"].append(
            {
                "fabric_block": fabric_block,
                "material": material,
                "amount": amount,
                "activity_id": activity_id,
                "emission": emission * amount if emission is not None else None,
            }
        )
        print(f"CO2eq per unit: {emission}")
        if emission is not None:
            total_emission += emission * amount
    for process, details in recipe["processes"].items():
        print("process", process)
        emission_details["processes"].append({"process": process, "details": details})
        resource_data = get_resource_data_for_process(process)
        if resource_data is None:
            print(f"No activity ids found for process {process}")
            continue
        for activity_id, amount in resource_data:
            url = f"{activity_url}{activity_id}/"
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                json = response.json()
            except Exception as e:
                print("error", str(e))
                return {"error": str(e)}
            emission = next(
                (
                    item["emissions"]
                    for item in json["lcia_results"]
                    if item["method"]["name"] == "IPCC 2021"
                ),
                None,
            )
            # append emission details
            emission_details["processes"][-1].setdefault("emissions", []).append(
                {
                    "amount": amount,
                    "activity_id": activity_id,
                    "emission": (
                        emission * amount * details["time"]
                        if emission is not None
                        else None
                    ),
                }
            )
            print(f"CO2eq for process {process} activity {activity_id}: {emission}")
            if emission is not None:
                total_emission += emission * amount * details["time"]

    return {"total_co2eq": total_emission, "details": emission_details}


def get_garment_recipe(garment_type: str):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM garment_types WHERE name = ?", (garment_type,))
    garment_type_id = cursor.fetchone()

    if not garment_type_id:
        return None

    garment_type_id = garment_type_id[0]

    cursor.execute(
        """
        SELECT ft.name, grfb.amount FROM garment_recipe_fabric_blocks grfb
        JOIN fabric_block_types ft ON grfb.fabric_block_id = ft.id
        WHERE grfb.garment_type = ?
    """,
        (garment_type_id,),
    )

    fabric_blocks_data = cursor.fetchall()

    fabric_blocks = []
    for fb in fabric_blocks_data:
        fb_name, fb_amount = fb
        fabric_blocks.extend([fb_name] * fb_amount)

    cursor.execute(
        """
        SELECT pt.name, grp.time FROM garment_recipe_processes grp
        JOIN process_types pt ON grp.process_id = pt.id
        WHERE grp.garment_type = ?
    """,
        (garment_type_id,),
    )

    processes_data = cursor.fetchall()

    processes = {}
    for proc in processes_data:
        proc_name, proc_time = proc
        processes[proc_name] = {"time": proc_time}

    conn.close()

    recipe = {"fabric_blocks": fabric_blocks, "processes": processes}
    return recipe
