import sqlite3

from fastapi import HTTPException

from ceis_backend.config import DB_PATH
from ceis_backend.models import (
    Co2Response,
    EmissionDetails,
    FabricBlock,
    GarmentRecipe,
    Process,
)
from ceis_backend.wiser_bridge import get_emission_per_unit, get_wiser_token
from ceis_backend.location_details import (
    distances_to_manufacturer,
    activity_id_transport,
)


def calculate_transport_emission(
    distance_km: float, amount_kg: float, emission_per_unit: float | None
) -> float | None:
    """
    Calculate transport emission based on distance and weight.

    Args:
        distance_km: Distance in kilometers.
        amount_kg: Weight in kilograms.
        emission_per_unit: Emission per unit from WISER (kg CO2eq per ton-km).

    Returns:
        Total transport emission in kg CO2eq, or None if emission_per_unit is unavailable.
    """
    if emission_per_unit is None:
        return None
    return emission_per_unit / 1000 * distance_km * amount_kg


def get_recipe_for_fabric_block(fabric_block: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get fabric block type details
    cursor.execute(
        "SELECT id, material, activity_id, amount_kg FROM fabric_block_types WHERE name = ?",
        (fabric_block,),
    )
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None, None, 0, []

    fabric_block_type_id, material, activity_id, amount_kg = result

    # Get processes for this fabric block type
    cursor.execute(
        """
        SELECT pt.name, fbrp.amount, pt.activity_id
        FROM fabric_block_recipe_processes fbrp
        JOIN process_types pt ON fbrp.process_id = pt.id
        WHERE fbrp.fabric_block_type = ?
        """,
        (fabric_block_type_id,),
    )
    processes_data = cursor.fetchall()
    processes: list[Process] = []
    for proc_name, proc_amount, activity_id_process in processes_data:
        processes.append(
            Process(
                activity=proc_name, amount=proc_amount, activity_id=activity_id_process
            )
        )

    conn.close()
    return material, activity_id, amount_kg, processes


def get_co2(garment_type_id: int) -> Co2Response:
    wiser_token = get_wiser_token()

    recipe = get_garment_recipe(garment_type_id)
    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail=f"Garment recipe not found for garment type ID: {garment_type_id}",
        )

    emission_details = Co2Response(
        fabric_blocks=EmissionDetails(details=[], total_emission=0),
        processes=EmissionDetails(details=[], total_emission=0),
    )

    fabric_blocks_emissions = 0
    already_used_fabric_block_ids = []
    for fabric_block in recipe.fabric_blocks:
        print("fabric block", fabric_block)
        material, activity_id, amount, fabric_block_processes = (
            get_recipe_for_fabric_block(fabric_block)
        )

        emission = None
        if activity_id is not None:
            emission = get_emission_per_unit(wiser_token, activity_id)
        # Calculate emissions from fabric block production processes
        fabric_block_production_emissions = 0
        fabric_block_process_details = []
        for fb_process in fabric_block_processes:
            process_emission_per_unit = get_emission_per_unit(
                wiser_token, fb_process.activity_id
            )

            process_emissions = (
                process_emission_per_unit * fb_process.amount
                if process_emission_per_unit is not None
                else 0
            )
            fabric_block_production_emissions += process_emissions
            fabric_block_process_details.append(
                {
                    "process": fb_process.activity,
                    "amount": fb_process.amount,
                    "emission": process_emissions,
                    "activity_id": fb_process.activity_id,
                }
            )
        # Calculate total emission for this fabric block (material + production processes)
        material_emission = emission * amount if emission is not None else 0
        total_fabric_block_emission = (
            material_emission + fabric_block_production_emissions
        )

        # Calculating alternative fabric block emissions if available
        used_fabric_block = get_used_fabric_block(
            fabric_block, already_used_fabric_block_ids
        )
        print("used fabric block", used_fabric_block)
        used_fabric_block_alternative = {}
        if used_fabric_block:
            already_used_fabric_block_ids.append(used_fabric_block.id)
            used_fabric_block_emissions = 0
            used_fabric_block_alternative["id"] = used_fabric_block.id
            used_fabric_block_alternative["location"] = used_fabric_block.location_name
            used_fabric_block_alternative["preparation_details"] = []

            # Calculate transport emissions if location is available
            transport_emission = 0
            if (
                used_fabric_block.location_name
                and used_fabric_block.location_name in distances_to_manufacturer
            ):
                distance = distances_to_manufacturer[used_fabric_block.location_name]
                transport_emission_per_unit = get_emission_per_unit(
                    wiser_token, activity_id_transport
                )
                transport_emission = calculate_transport_emission(
                    distance, amount, transport_emission_per_unit
                )
                if transport_emission is not None:
                    print(
                        f"Transport emission for {used_fabric_block.location_name}: {transport_emission}"
                    )

            used_fabric_block_alternative["transport_emission"] = (
                transport_emission or 0
            )
            used_fabric_block_emissions += transport_emission or 0

            for prep in used_fabric_block.processes:
                process_emission_per_unit = get_emission_per_unit(
                    wiser_token, prep.activity_id
                )
                process_emissions = (
                    process_emission_per_unit * prep.amount
                    if process_emission_per_unit is not None
                    else 0
                )
                used_fabric_block_emissions += process_emissions
                used_fabric_block_alternative["preparation_details"].append(
                    {
                        "preparation": prep.activity,
                        "amount": prep.amount,
                        "emission": process_emissions,
                        "activity_id": prep.activity_id,
                    }
                )
            used_fabric_block_alternative["emission"] = used_fabric_block_emissions

        emission_details.fabric_blocks.details.append(
            {
                "fabric_block": fabric_block,
                "material": material,
                "amount": amount,
                "activity_id": activity_id,
                "emission": total_fabric_block_emission,
                "material_emission": material_emission,
                "production_emission": fabric_block_production_emissions,
                "production_processes": fabric_block_process_details,
                "alternative": used_fabric_block_alternative,
            }
        )
        print(f"CO2eq material emission: {material_emission}")
        print(f"CO2eq production processes: {fabric_block_production_emissions}")
        fabric_blocks_emissions += total_fabric_block_emission

    emission_details.fabric_blocks.total_emission = fabric_blocks_emissions

    # Calculate emissions from garment assembly processes
    processes_emissions = 0
    for process in recipe.processes:
        process_emissions = 0
        print("process", process)
        emission_details.processes.details.append(
            {"process": process.activity, "duration": process.amount, "resources": []}
        )
        resource_emission_per_unit = get_emission_per_unit(
            wiser_token, process.activity_id
        )
        resource_emissions = (
            resource_emission_per_unit * process.amount
            if resource_emission_per_unit is not None
            else 0
        )
        process_emissions += resource_emissions
        # append emission details
        emission_details.processes.details[-1]["resources"].append(
            {
                "name": process.activity,
                "amount": 1.0,
                "activity_id": process.activity_id,
                "emission": resource_emissions,
            }
        )
        print(
            f"CO2eq for resource {process.activity} activity id {process.activity_id}: {resource_emission_per_unit}"
        )
        if resource_emission_per_unit is not None:
            processes_emissions += resource_emissions
        emission_details.processes.details[-1]["emission"] = process_emissions
    emission_details.processes.total_emission = processes_emissions

    return emission_details


def get_garment_recipe(garment_type_id: int) -> GarmentRecipe | None:
    conn = sqlite3.connect(DB_PATH)
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
        SELECT pt.name, grp.amount, pt.activity_id FROM garment_recipe_processes grp
        JOIN process_types pt ON grp.process_id = pt.id
        WHERE grp.garment_type = ?
    """,
        (garment_type_id,),
    )

    processes_data = cursor.fetchall()

    processes: list[Process] = []
    for proc in processes_data:
        proc_name, proc_amount, activity_id = proc
        processes.append(
            Process(activity=proc_name, amount=proc_amount, activity_id=activity_id)
        )

    conn.close()

    recipe = GarmentRecipe(fabric_blocks=fabric_blocks, processes=processes)
    return recipe


def get_used_fabric_block(
    fabric_block_name: str, already_used_ids: list[int]
) -> FabricBlock | None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    base_query = """
        SELECT fbi.id, fbi.type_id, fbi.co2eq, fbi.location_id, l.name as location_name
        FROM fabric_blocks_inventory fbi
        JOIN fabric_block_types fbt ON fbi.type_id = fbt.id
        LEFT JOIN locations l ON fbi.location_id = l.id
        WHERE fbt.name = ?
    """

    params = [fabric_block_name]

    if already_used_ids:
        placeholders = ",".join("?" * len(already_used_ids))
        base_query += f" AND fbi.id NOT IN ({placeholders})"
        params.extend(str(id) for id in already_used_ids)

    base_query += " LIMIT 1"

    cursor.execute(base_query, params)
    result = cursor.fetchone()

    if not result:
        conn.close()
        return None

    fb_id, fb_type_id, fb_co2eq, fb_location_id, fb_location_name = result
    cursor.execute(
        """
        SELECT pt.name, pufb.amount, pt.activity_id
        FROM preparations_used_fabric_blocks pufb
        JOIN process_types pt ON pufb.type_id = pt.id
        WHERE pufb.fabric_block_id = ?
        """,
        (fb_id,),
    )
    preparations_data = cursor.fetchall()
    preparations: list[Process] = []
    for prep in preparations_data:
        prep_name, prep_amount, activity_id = prep
        preparations.append(
            Process(activity=prep_name, amount=prep_amount, activity_id=activity_id)
        )
    conn.close()
    return FabricBlock(
        id=fb_id,
        type_id=fb_type_id,
        co2eq=fb_co2eq,
        processes=preparations,
        location_id=fb_location_id,
        location_name=fb_location_name,
    )


# Database CRUD operations


def db_create_garment_type(name: str) -> dict:
    """Create a new garment type in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO garment_types (name) VALUES (?)",
            (name,),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "name": name}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Garment type already exists")
    finally:
        conn.close()


def db_get_garment_types() -> list[dict]:
    """Get all garment types from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM garment_types")
    garment_types = cursor.fetchall()
    conn.close()
    return [{"id": gt[0], "name": gt[1]} for gt in garment_types]


def db_get_locations() -> list[dict]:
    """Get all locations from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM locations")
    locations = cursor.fetchall()
    conn.close()
    return [{"id": loc[0], "name": loc[1]} for loc in locations]


def db_delete_garment_recipe(garment_type_id: int) -> dict:
    """Delete a garment recipe by garment type ID."""
    conn = sqlite3.connect(DB_PATH)
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


def db_create_fabric_block_type(
    name: str, material: str | None, amount_kg: float | None, activity_id: int
) -> dict:
    """Create a new fabric block type in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO fabric_block_types (name, material, amount_kg, activity_id)
            VALUES (?, ?, ?, ?)
            """,
            (name, material, amount_kg, activity_id),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "name": name}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Fabric block type already exists")
    finally:
        conn.close()


def db_create_process_type(name: str, unit: str | None, activity_id: int) -> dict:
    """Create a new process type in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO process_types (name, unit, activity_id)
            VALUES (?, ?, ?)
            """,
            (name, unit, activity_id),
        )
        conn.commit()
        return {"id": cursor.lastrowid, "name": name}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Process type already exists")
    finally:
        conn.close()


def db_get_fabric_block_types() -> list[dict]:
    """Get all fabric block types from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM fabric_block_types")
    fabric_block_types = cursor.fetchall()
    conn.close()
    return [{"id": fb_type[0], "name": fb_type[1]} for fb_type in fabric_block_types]


def db_delete_fabric_block_type(type_id: int) -> dict:
    """Delete a fabric block type by ID."""
    conn = sqlite3.connect(DB_PATH)
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


def db_get_process_types() -> list[dict]:
    """Get all process types from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, unit, activity_id FROM process_types")
    process_types = cursor.fetchall()
    conn.close()
    return [
        {
            "id": pt[0],
            "name": pt[1],
            "unit": pt[2],
            "activity_id": pt[3],
        }
        for pt in process_types
    ]


def db_delete_process_type(type_id: int) -> dict:
    """Delete a process type by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT id FROM process_types WHERE id = ?",
            (type_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Process type not found")

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


def db_create_garment_recipe(
    garment_type_id: int, fabric_blocks: list, processes: list
) -> dict:
    """Create or update a garment recipe in the database."""
    if not fabric_blocks:
        raise HTTPException(
            status_code=400,
            detail="Garment recipe must include at least one fabric block",
        )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT id FROM garment_types WHERE id = ?",
            (garment_type_id,),
        )
        if cursor.fetchone() is None:
            raise HTTPException(status_code=400, detail="Invalid garment type")

        fabric_block_ids = [fb.type_id for fb in fabric_blocks]
        cursor.execute(
            f"SELECT COUNT(*) FROM fabric_block_types WHERE id IN ({','.join('?' * len(fabric_block_ids))})",
            fabric_block_ids,
        )
        if cursor.fetchone()[0] != len(set(fabric_block_ids)):
            raise HTTPException(status_code=400, detail="Invalid fabric block type")

        if processes:
            process_ids = [proc.process_id for proc in processes]
            cursor.execute(
                f"SELECT COUNT(*) FROM process_types WHERE id IN ({','.join('?' * len(process_ids))})",
                process_ids,
            )
            if cursor.fetchone()[0] != len(set(process_ids)):
                raise HTTPException(status_code=400, detail="Invalid process type")

        for fb in fabric_blocks:
            if fb.amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Fabric block amounts must be greater than 0",
                )
        for proc in processes:
            if proc.amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Process amount must be greater than 0",
                )

        cursor.execute(
            "DELETE FROM garment_recipe_fabric_blocks WHERE garment_type = ?",
            (garment_type_id,),
        )
        cursor.execute(
            "DELETE FROM garment_recipe_processes WHERE garment_type = ?",
            (garment_type_id,),
        )

        cursor.executemany(
            """
            INSERT INTO garment_recipe_fabric_blocks
            (garment_type, fabric_block_id, amount)
            VALUES (?, ?, ?)
            """,
            [(garment_type_id, fb.type_id, int(fb.amount)) for fb in fabric_blocks],
        )

        if processes:
            cursor.executemany(
                """
                INSERT INTO garment_recipe_processes
                (garment_type, process_id, amount)
                VALUES (?, ?, ?)
                """,
                [(garment_type_id, proc.process_id, proc.amount) for proc in processes],
            )

        conn.commit()
        return {
            "message": "Garment recipe saved",
            "garment_type_id": garment_type_id,
        }
    finally:
        conn.close()


def db_create_fabric_block(
    type_id: int, location_id: int | None, processes: list
) -> dict:
    """Create a new fabric block in the inventory."""
    co2eq = None  # Placeholder
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO fabric_blocks_inventory (type_id, co2eq, location_id)
        VALUES (?, ?, ?)
        """,
        (type_id, co2eq, location_id),
    )
    fabric_block_id = cursor.lastrowid
    if not fabric_block_id:
        conn.close()
        return {"error": "Invalid fabric block type"}

    if processes:
        cursor.executemany(
            """
            INSERT INTO preparations_used_fabric_blocks (type_id, amount, fabric_block_id)
            VALUES (?, ?, ?)
            """,
            [(prep.type_id, prep.amount, fabric_block_id) for prep in processes],
        )

    conn.commit()
    conn.close()
    return {"message": "Fabric block created successfully", "id": fabric_block_id}


def db_get_fabric_blocks(type_filter: str | None = None) -> list[dict]:
    """Get all fabric blocks from inventory, optionally filtered by type."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
                   SELECT fbi.id, fbi.type_id, fbi.co2eq, fbi.garment_id, l.name as location_name
                   FROM fabric_blocks_inventory fbi
                   LEFT JOIN locations l ON fbi.location_id = l.id
                   WHERE fbi.type_id = ? OR ? IS NULL
                   """,
        (type_filter, type_filter),
    )
    fabric_blocks_data = cursor.fetchall()

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


def db_delete_fabric_block(fabric_block_id: int) -> dict:
    """Delete a fabric block from inventory by ID."""
    conn = sqlite3.connect(DB_PATH)
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


def db_get_replacement_fabric_blocks_emissions(
    replacement_names: list[str], token: str, emission_cache: dict[int, float | None]
) -> dict:
    """Calculate emissions for replacement fabric blocks for repair scenarios."""
    replacement_fabric_blocks = {"details": [], "total_emission": 0}

    if not replacement_names:
        return replacement_fabric_blocks

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        for fabric_block_name in replacement_names:
            cursor.execute(
                """
                SELECT id, activity_id, amount_kg
                FROM fabric_block_types
                WHERE name = ?
                LIMIT 1
                """,
                (fabric_block_name,),
            )
            row = cursor.fetchone()
            if not row:
                continue

            fabric_block_type_id, activity_id, weight_per_block = row

            # Get emission for material
            if activity_id in emission_cache:
                material_emission_per_unit = emission_cache[activity_id]
            else:
                material_emission_per_unit = get_emission_per_unit(token, activity_id)
                if material_emission_per_unit is None:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to fetch emission for activity {activity_id}",
                    )
                emission_cache[activity_id] = material_emission_per_unit

            material_emission = (
                material_emission_per_unit * weight_per_block
                if material_emission_per_unit is not None
                else 0
            )

            # Get processes for this fabric block
            cursor.execute(
                """
                SELECT pt.name, fbrp.amount, pt.activity_id
                FROM fabric_block_recipe_processes fbrp
                JOIN process_types pt ON fbrp.process_id = pt.id
                WHERE fbrp.fabric_block_type = ?
                """,
                (fabric_block_type_id,),
            )
            processes_data = cursor.fetchall()

            process_emissions_list = []
            for process_name, process_amount, process_activity_id in processes_data:
                # Get emission for process
                if process_activity_id in emission_cache:
                    resource_emission_per_unit = emission_cache[process_activity_id]
                else:
                    resource_emission_per_unit = get_emission_per_unit(
                        token, process_activity_id
                    )
                    if resource_emission_per_unit is None:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Failed to fetch emission for activity {process_activity_id}",
                        )
                    emission_cache[process_activity_id] = resource_emission_per_unit

                resource_emissions = (
                    resource_emission_per_unit * process_amount
                    if resource_emission_per_unit is not None
                    else 0
                )

                process_emissions_list.append(
                    {
                        "process": process_name,
                        "emission": resource_emissions,
                    }
                )

            # Calculate total emissions for this fabric block
            total_processes_emission = sum(
                p["emission"] for p in process_emissions_list
            )
            fabric_block_total_emission = material_emission + total_processes_emission

            replacement_fabric_blocks["details"].append(
                {
                    "fabric_block": fabric_block_name,
                    "material_emission": material_emission,
                    "processes": process_emissions_list,
                }
            )
            replacement_fabric_blocks["total_emission"] += fabric_block_total_emission
    finally:
        conn.close()

    return replacement_fabric_blocks
