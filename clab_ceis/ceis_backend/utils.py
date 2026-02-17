from SPARQLWrapper import SPARQLWrapper, JSON
from typing import Optional, Mapping, cast
from fastapi import HTTPException
import requests
import sqlite3
import json
from models import (
    Co2Response,
    EmissionDetails,
    FabricBlock,
    GarmentRecipe,
    Process,
    Resource,
)

SPARQL_ENDPOINT = "http://graphdb:7200/repositories/ceis-dev-local"


def get_bindings(file_name: str):
    with open(f"./queries/{file_name}.rq", "r", encoding="utf-8") as file:
        query = file.read()
    client = SPARQLWrapper(SPARQL_ENDPOINT)
    client.setQuery(query)
    client.setReturnFormat(JSON)
    results = client.query().convert()
    # if not dict
    if not isinstance(results, dict):
        raise ValueError("Invalid response from SPARQL endpoint")

    bindings = results.get("results", {}).get("bindings", [])
    print(bindings)
    if bindings and isinstance(bindings, list):
        return bindings
    raise ValueError("Invalid response from SPARQL endpoint")


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


def get_resources_data_for_process(process: Process) -> list[Resource]:
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT rt.name, rt.activity_id, prc.amount
        FROM process_types pt
        JOIN process_resource_consumption prc ON prc.process_id = pt.id
        JOIN resource_types rt ON prc.resource_id = rt.id
        WHERE pt.name = ?
        """,
        (process.activity,),
    )
    result = cursor.fetchall()
    conn.close()
    if result:
        return [
            Resource(name=row[0], activity_id=row[1], amount=row[2]) for row in result
        ]
    return []


def get_co2(garment_type_id: int) -> Co2Response:
    wiser_token = get_wiser_token()
    print("wiser_token", wiser_token)

    recipe = get_garment_recipe(garment_type_id)
    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail=f"Garment recipe not found for garment type ID: {garment_type_id}",
        )

    activity_url = "https://api.wiser.ehealth.hevs.ch/ecoinvent/3.12-cutoff/activity/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {wiser_token}",
    }

    emission_details = Co2Response(
        fabric_blocks=EmissionDetails(details=[], total_emission=0),
        processes=EmissionDetails(details=[], total_emission=0),
    )

    fabric_blocks_emissions = 0
    already_used_fabric_block_ids = []
    for fabric_block in recipe.fabric_blocks:
        print("fabric block", fabric_block)
        material, activity_id, amount = get_recipe_for_fabric_block(fabric_block)

        url = f"{activity_url}{activity_id}/"

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            json = response.json()
        except Exception as e:
            print("error", str(e))
            raise HTTPException(status_code=500, detail=str(e))
        emission = next(
            (
                item["emissions"]
                for item in json["lcia_results"]
                if item["method"]["name"] == "IPCC 2021"
            ),
            None,
        )

        used_fabric_block = get_used_fabric_block(
            fabric_block, already_used_fabric_block_ids
        )
        print("used fabric block", used_fabric_block)

        used_fabric_block_alternative = {}
        if used_fabric_block:
            already_used_fabric_block_ids.append(used_fabric_block.id)
            used_fabric_block_emissions = 0
            used_fabric_block_alternative["id"] = used_fabric_block.id
            used_fabric_block_alternative["preparation_details"] = []
            for prep in used_fabric_block.processes:
                print("preparation", prep)
                resources_data = get_resources_data_for_process(prep)
                if not resources_data:
                    continue
                process_emissions = 0
                resources_details = []
                for resource in resources_data:
                    url = f"{activity_url}{resource.activity_id}/"
                    try:
                        response = requests.get(url, headers=headers)
                        response.raise_for_status()
                        json = response.json()
                    except Exception as e:
                        print("error", str(e))
                        raise HTTPException(status_code=500, detail=str(e))
                    resource_emission_per_unit = next(
                        (
                            item["emissions"]
                            for item in json["lcia_results"]
                            if item["method"]["name"] == "IPCC 2021"
                        ),
                        None,
                    )
                    print(
                        f"CO2eq for resource {resource.name} activity id {resource.activity_id}: {resource_emission_per_unit}"
                    )
                    if resource_emission_per_unit is not None:
                        resource_emissions = (
                            resource_emission_per_unit * resource.amount * prep.time
                        )
                        resources_details.append(
                            {
                                "name": resource.name,
                                "amount": resource.amount,
                                "activity_id": resource.activity_id,
                                "emission": resource_emissions,
                            }
                        )
                        process_emissions += resource_emissions
                used_fabric_block_emissions += process_emissions
                process_details = {
                    "preparation": prep.activity,
                    "duration": prep.time,
                    "resources": resources_details,
                    "emission": process_emissions,
                }
                used_fabric_block_alternative["preparation_details"].append(
                    process_details
                )
            used_fabric_block_alternative["emission"] = used_fabric_block_emissions

        emission_details.fabric_blocks.details.append(
            {
                "fabric_block": fabric_block,
                "material": material,
                "amount": amount,
                "activity_id": activity_id,
                "emission": emission * amount if emission is not None else None,
                "alternative": used_fabric_block_alternative,
            }
        )
        print(f"CO2eq per unit: {emission}")
        if emission is not None:
            fabric_blocks_emissions += emission * amount

    emission_details.fabric_blocks.total_emission = fabric_blocks_emissions

    processes_emissions = 0
    for process in recipe.processes:
        process_emissions = 0
        print("process", process)
        emission_details.processes.details.append(
            {"process": process.activity, "duration": process.time, "resources": []}
        )
        resources_data = get_resources_data_for_process(process)
        if not resources_data:
            continue
        for resource in resources_data:
            url = f"{activity_url}{resource.activity_id}/"
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                json = response.json()
            except Exception as e:
                print("error", str(e))
                raise HTTPException(status_code=500, detail=str(e))
            resource_emission_per_unit = next(
                (
                    item["emissions"]
                    for item in json["lcia_results"]
                    if item["method"]["name"] == "IPCC 2021"
                ),
                None,
            )
            resource_emissions = (
                resource_emission_per_unit * resource.amount * process.time
                if resource_emission_per_unit is not None
                else 0
            )
            process_emissions += resource_emissions
            # append emission details
            emission_details.processes.details[-1]["resources"].append(
                {
                    "name": resource.name,
                    "amount": resource.amount,
                    "activity_id": resource.activity_id,
                    "emission": resource_emissions,
                }
            )
            print(
                f"CO2eq for resource {resource.name} activity id {resource.activity_id}: {resource_emission_per_unit}"
            )
            if resource_emission_per_unit is not None:
                processes_emissions += resource_emissions
        emission_details.processes.details[-1]["emission"] = process_emissions
    emission_details.processes.total_emission = processes_emissions

    return emission_details


def get_garment_recipe(garment_type_id: int) -> GarmentRecipe | None:
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM garment_types WHERE id = ?", (garment_type_id,))
    if not cursor.fetchone():
        return None

    cursor.execute(
        """
        SELECT ft.name, grfb.amount FROM garment_recipe_fabric_blocks grfb
        JOIN fabric_block_types ft ON grfb.fabric_block_id = ft.id
        WHERE grfb.garment_type = ?
    """,
        (garment_type_id,),
    )

    fabric_blocks_data = cursor.fetchall()

    fabric_blocks: list[str] = []
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

    processes: list[Process] = []
    for proc in processes_data:
        proc_name, proc_time = proc
        processes.append(Process(activity=proc_name, time=proc_time))

    conn.close()

    recipe = GarmentRecipe(fabric_blocks=fabric_blocks, processes=processes)
    return recipe


def get_used_fabric_block(
    fabric_block_name: str, already_used_ids: list[int]
) -> FabricBlock | None:
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    base_query = """
        SELECT fbi.id, fbi.type_id, fbi.co2eq
        FROM fabric_blocks_inventory fbi
        JOIN fabric_block_types fbt ON fbi.type_id = fbt.id
        WHERE fbt.name = ?
    """

    params = [fabric_block_name]

    if already_used_ids:
        placeholders = ",".join("?" * len(already_used_ids))
        base_query += f" AND fbi.id NOT IN ({placeholders})"
        params.extend(already_used_ids)

    base_query += " LIMIT 1"

    cursor.execute(base_query, params)
    result = cursor.fetchone()

    if not result:
        conn.close()
        return None

    fb_id, fb_type_id, fb_co2eq = result
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
    preparations: list[Process] = []
    for prep in preparations_data:
        prep_name, prep_amount = prep
        preparations.append(Process(activity=prep_name, time=prep_amount))
    conn.close()
    return FabricBlock(
        id=fb_id, type_id=fb_type_id, co2eq=fb_co2eq, processes=preparations
    )
