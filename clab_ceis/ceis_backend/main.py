from typing import Optional
from db_init import init_sqlite_db
from utils import get_bindings
from fastapi import FastAPI, Request
import requests
import sqlite3
import json
from models import FabricBlock
from recipes import FB1_recipe, FB2_recipe, croptop_recipe

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
async def create_fabric_block(fabric_block: FabricBlock, request: Request):
    co2eq = fabric_block.co2eq if fabric_block.co2eq is not None else None
    conn = sqlite3.connect('ceis_backend.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO fabric_blocks (type, co2eq)
        VALUES (?, ?)
    ''', (fabric_block.type, co2eq))
    fabric_block_id = cursor.lastrowid

    preparations = fabric_block.preparations if fabric_block.preparations is not None else []
    for prep in preparations:
        cursor.execute('''
            INSERT INTO preparations (type, amount, fabric_block_id)
            VALUES (?, ?, ?)
        ''', (prep.type, prep.amount, fabric_block_id))
    conn.commit()
    conn.close()
    return {"message": "Fabric block created successfully", "id": fabric_block_id}

@app.get("/fabric-blocks")
def get_fabric_blocks(type: Optional[str] = None):
    conn = sqlite3.connect('ceis_backend.db')
    cursor = conn.cursor()
    cursor.execute('''
                   SELECT id, type, co2eq FROM fabric_blocks
                   WHERE type = ? OR ? IS NULL
                   ''', (type, type))
    fabric_blocks_data = cursor.fetchall()

    fabric_blocks = []
    for fb in fabric_blocks_data:
        fb_id, fb_type, fb_co2eq = fb
        cursor.execute('SELECT type, amount FROM preparations WHERE fabric_block_id = ?', (fb_id,))
        preparations_data = cursor.fetchall()
        preparations = [{"type": p[0], "amount": p[1]} for p in preparations_data]
        fabric_blocks.append({
            "id": fb_id,
            "type": fb_type,
            "co2eq": fb_co2eq,
            "preparations": preparations
        })
    conn.close()
    return fabric_blocks


@app.get("/co2/croptop")
def get_assessments():
    wiser_token = get_wiser_token()
    print("wiser_token", wiser_token)

    total_emission = 0
    emission_details = []
    for fabric_block in croptop_recipe["fabric_blocks"]:
        print("fabric_block", fabric_block)
        material = None
        amount = 0
        if fabric_block == "FB1":
            material, amount = extract_materials_from_fabric_block_recipe(FB1_recipe)
        elif fabric_block == "FB2":
            material, amount = extract_materials_from_fabric_block_recipe(FB2_recipe)
        print("material:", material, "amount:", amount)
        activity_id = None
        if material == "cotton":
            activity_id = 3878
        elif material == "polyester":
            activity_id = 5544

        if activity_id is not None:
            emission_details.append({"material": material, "amount": amount, "activity_id": activity_id})
            url = f"https://api.wiser.ehealth.hevs.ch/ecoinvent/3.11-cutoff/activity/{activity_id}/"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {wiser_token}",
            }
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                json =  response.json()
            except Exception as e:
                print("error", str(e))
                return {"error": str(e)}
            emission = next(
                (item["emissions"] for item in json["lcia_results"] if item["method"]["name"] == "IPCC 2021"),
                None
            )
            print(f"CO2eq per unit: {emission}")
            if emission is not None:
                total_emission += emission * amount
    
    return {"total_co2eq": total_emission, "details": emission_details}


@app.get("/test")
def test_endpoint():

    url = "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.11-cutoff/activity/3878/"

    headers = {
        "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJralFLN3FFYXl1cS1mM1NLU2FiaXV4Z3lpRG5IRnlSWXVQc3c3cEQyVDVFIn0.eyJleHAiOjE3NjA5NTQ4MzQsImlhdCI6MTc2MDk1NDUzNCwianRpIjoiNzk2YzMyNWUtYTY1YS00ZWZjLWI4YTktNGZiYTYxMTY3MmYwIiwiaXNzIjoiaHR0cHM6Ly9hdXRoLndpc2VyLmVoZWFsdGguaGV2cy5jaC9yZWFsbXMvd2lzZXIiLCJhdWQiOlsic3A0LWtnIiwic3A1LWJhY2tlbmQtdGVzdCIsIndpc2VyLXNwMy1hcGkiLCJzcDUtc3dpc3MtcHJvZHVjdGlvbiIsInNwNS1zd2lzcy1wcm9kdWN0aW9uLXRlc3QiLCJzcDYtY2l0eS1pY3QiLCJzcDctZGF0YS1jZW50ZXJzIiwiYWNjb3VudCJdLCJzdWIiOiIxN2E5ODUxMC0yMmRhLTQwZmMtYmJhNS0xMDYwMmQ2MWFkNzEiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJ3aXNlci1hcGktcHVibGljIiwic2Vzc2lvbl9zdGF0ZSI6IjBmNzUzZmRhLWE5NzgtNDFhYy04ZmQ5LTVjNDUzODlmYWY1ZCIsImFjciI6IjEiLCJhbGxvd2VkLW9yaWdpbnMiOlsiLyoiXSwicmVhbG1fYWNjZXNzIjp7InJvbGVzIjpbIm9mZmxpbmVfYWNjZXNzIiwiZGVmYXVsdC1yb2xlcy13aXNlciIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsic3A1LXN3aXNzLXByb2R1Y3Rpb24iOnsicm9sZXMiOlsiUk9MRV9TUDVfQURNSU4iXX0sInNwNS1zd2lzcy1wcm9kdWN0aW9uLXRlc3QiOnsicm9sZXMiOlsiUk9MRV9TUDVfQURNSU4iXX0sInNwNi1jaXR5LWljdCI6eyJyb2xlcyI6WyJST0xFX1NQNl9BRE1JTiJdfSwic3A0LWtnIjp7InJvbGVzIjpbIlJPTEVfQURNSU4iLCJSRUFEX1JFUE9fKiJdfSwic3A3LWRhdGEtY2VudGVycyI6eyJyb2xlcyI6WyJST0xFX1NQN19BRE1JTiJdfSwiYWNjb3VudCI6eyJyb2xlcyI6WyJtYW5hZ2UtYWNjb3VudCIsIm1hbmFnZS1hY2NvdW50LWxpbmtzIiwidmlldy1wcm9maWxlIl19fSwic2NvcGUiOiJwcm9maWxlIGVtYWlsIiwic2lkIjoiMGY3NTNmZGEtYTk3OC00MWFjLThmZDktNWM0NTM4OWZhZjVkIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInJvbGVzIjpbIlJPTEVfQURNSU4iLCJSRUFEX1JFUE9fKiJdLCJuYW1lIjoiU2ltZW9uIFBpbHoiLCJvcmdhbml6YXRpb25zIjpbeyJncm91cF9pZCI6IjdhNTRlZWQyLTc3NjctNDA3Yy04YWI2LWY1OWJiZGY4MTM5NyIsImNvbXBhbnlfbmFtZSI6IlVuaXZlcnNpdMOkdCBTdC4gR2FsbGVuIiwiYXVkaXRvcl9ncm91cCI6IjUzMGU5ZTczLTc3YjAtNDY3OS1hNzBlLWQyMmQ3ODMyNzFjNyJ9XSwiZ3JvdXBfbmFtZXMiOlsiL0lOVEVSTkFML1VOSVZFUlNJVFlfU1RfR0FMTEVOL0FETUlOX0dST1VQIiwiL0lOVEVSTkFML1VOSVZFUlNJVFlfU1RfR0FMTEVOIl0sImFkbWluX2dyb3VwX2lkcyI6WyI3YTU0ZWVkMi03NzY3LTQwN2MtOGFiNi1mNTliYmRmODEzOTciXSwicHJlZmVycmVkX3VzZXJuYW1lIjoic2ltZW9uIiwiZ2l2ZW5fbmFtZSI6IlNpbWVvbiIsImZhbWlseV9uYW1lIjoiUGlseiIsIm1haW5fb3JnYW5pemF0aW9uX2lkIjoiN2E1NGVlZDItNzc2Ny00MDdjLThhYjYtZjU5YmJkZjgxMzk3IiwiZW1haWwiOiJzaW1lb24ucGlsekB1bmlzZy5jaCJ9.KHh5jttEiauy5NQim-qjkrdzsVH2r5xP6Fs5x1FqvJzxIusHtkskqfIsP6U8EHJI3NlpNN5iL1Rk5sQFvLGojBH6T6NcRFEqaoZhpLzk-D5s-GU1UYfyUa4qYV6b8PoCmCjjyzZ1Bo5VUcdbbEYn4vco4FdJ93w_7vlpnMYK34SApwwda-PkRxtPRBFj8TdNTKyp2vwLO4ji4WRbK99IWRQKMIzjbJpqAgd3sJTAL-gUXe5PpqOar_8Yumt7bOlh_f9tNVHtoSOgkQi-RWMIbnO_mPRM6_mOH6K-cXDG92hPR-19oDh1G06F_LnD_jvYFulY8Nv9aAeuDynDPdZFpw",
    }

    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("Response:", response.text)

def get_wiser_token():
    url = "https://auth.wiser.ehealth.hevs.ch/realms/wiser/protocol/openid-connect/token"
    payload = {
        "grant_type": "password",
        "client_id": "wiser-api-public",
        "username": "simeon",
        "password": "meWdis-sikfup-0josgi"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        json =  response.json()
        return json["access_token"]
    except Exception as e:
        return {"error": str(e)}

def extract_materials_from_fabric_block_recipe(recipe):
    material = recipe["material"]
    amount = recipe["amount"]
    return material, amount
    
    