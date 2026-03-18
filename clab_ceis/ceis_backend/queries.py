"""Database CRUD operations for CEIS backend."""

import sqlite3

from fastapi import HTTPException

from ceis_backend.config import DB_PATH
from ceis_backend.models import (
    FabricBlock,
    SecondLifeFabricBlock,
    GarmentRecipe,
    Process,
)


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


def db_get_materials() -> list[dict]:
    """Get all materials from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, kg_per_sqm, activity_id FROM materials ORDER BY name"
    )
    materials = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row[0],
            "name": row[1],
            "kg_per_sqm": row[2],
            "activity_id": row[3],
        }
        for row in materials
    ]


def db_upsert_material(name: str, kg_per_sqm: float, activity_id: int) -> dict:
    """Create or update a material by name."""
    normalized_name = name.strip()
    if not normalized_name:
        raise HTTPException(status_code=400, detail="Material name is required")
    if kg_per_sqm <= 0:
        raise HTTPException(status_code=400, detail="kg_per_sqm must be greater than 0")
    if activity_id <= 0:
        raise HTTPException(
            status_code=400, detail="activity_id must be greater than 0"
        )

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM materials WHERE name = ?", (normalized_name,))
        existing = cursor.fetchone()
        action = "updated" if existing else "created"

        cursor.execute(
            """
            INSERT INTO materials (name, kg_per_sqm, activity_id)
            VALUES (?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                kg_per_sqm = excluded.kg_per_sqm,
                activity_id = excluded.activity_id
            """,
            (normalized_name, kg_per_sqm, activity_id),
        )
        cursor.execute(
            "SELECT id, name, kg_per_sqm, activity_id FROM materials WHERE name = ?",
            (normalized_name,),
        )
        row = cursor.fetchone()
        conn.commit()
        return {
            "id": row[0],
            "name": row[1],
            "kg_per_sqm": row[2],
            "activity_id": row[3],
            "action": action,
        }
    finally:
        conn.close()


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


def db_create_fabric_block_type(name: str, sqm: float) -> dict:
    """Create a new fabric block type in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO fabric_block_types (name, sqm)
            VALUES (?, ?)
            """,
            (name, sqm),
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
    garment_type_name: str, fabric_blocks: list, processes: list
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
            "SELECT id FROM garment_types WHERE name = ?",
            (garment_type_name,),
        )
        garment_type_row = cursor.fetchone()
        if garment_type_row is None:
            raise HTTPException(status_code=400, detail="Invalid garment type")
        garment_type_id = garment_type_row[0]

        fabric_block_ids = [fb.type_id for fb in fabric_blocks]
        cursor.execute(
            f"SELECT COUNT(*) FROM fabric_block_types WHERE id IN ({','.join('?' * len(fabric_block_ids))})",
            fabric_block_ids,
        )
        if cursor.fetchone()[0] != len(set(fabric_block_ids)):
            raise HTTPException(status_code=400, detail="Invalid fabric block type")

        material_ids = [fb.material_id for fb in fabric_blocks]
        cursor.execute(
            f"SELECT COUNT(*) FROM materials WHERE id IN ({','.join('?' * len(material_ids))})",
            material_ids,
        )
        if cursor.fetchone()[0] != len(set(material_ids)):
            raise HTTPException(status_code=400, detail="Invalid material type")

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
            (garment_type, fabric_block_id, material_id, amount)
            VALUES (?, ?, ?, ?)
            """,
            [
                (garment_type_id, fb.type_id, fb.material_id, int(fb.amount))
                for fb in fabric_blocks
            ],
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
            "garment_type_name": garment_type_name,
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


def get_fabric_block_recipe(
    fabric_block_name: str, material_id: int | None = None
) -> FabricBlock | None:
    """Get a fabric block recipe with all its processes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get fabric block type details
    cursor.execute(
        "SELECT id FROM fabric_block_types WHERE name = ?",
        (fabric_block_name,),
    )
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None

    fabric_block_type_id = result[0]

    selected_material_name = "unknown"
    selected_activity_id = 0
    if material_id is not None:
        cursor.execute(
            "SELECT name, activity_id FROM materials WHERE id = ?",
            (material_id,),
        )
        material_row = cursor.fetchone()
    else:
        cursor.execute("SELECT name, activity_id FROM materials ORDER BY id LIMIT 1")
        material_row = cursor.fetchone()

    if material_row:
        selected_material_name = material_row[0]
        selected_activity_id = material_row[1]

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
            Process(name=proc_name, amount=proc_amount, activity_id=activity_id_process)
        )

    conn.close()
    return FabricBlock(
        id=fabric_block_type_id,
        name=fabric_block_name,
        material=selected_material_name,
        activity_id=selected_activity_id,
        processes=processes,
    )


def get_fabric_block_weight_kg(
    fabric_block_name: str, material_name: str
) -> float | None:
    """Get computed block weight in kg for a fabric block and material pair."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT fbt.sqm, m.kg_per_sqm
            FROM fabric_block_types fbt
            JOIN materials m ON m.name = ?
            WHERE fbt.name = ?
            LIMIT 1
            """,
            (material_name, fabric_block_name),
        )
        row = cursor.fetchone()
        if not row:
            return None
        sqm, kg_per_sqm = row
        return sqm * kg_per_sqm
    finally:
        conn.close()


def get_full_garment_recipe(garment_type_id: int) -> GarmentRecipe | None:
    """Get a complete garment recipe including all fabric blocks and processes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM garment_types WHERE id = ?", (garment_type_id,))
    if not cursor.fetchone():
        return None

    cursor.execute(
        """
        SELECT ft.name, grfb.material_id, grfb.amount FROM garment_recipe_fabric_blocks grfb
        JOIN fabric_block_types ft ON grfb.fabric_block_id = ft.id
        WHERE grfb.garment_type = ?
    """,
        (garment_type_id,),
    )

    fabric_blocks_data = cursor.fetchall()

    fabric_blocks: list[FabricBlock] = []
    for fb in fabric_blocks_data:
        fb_name, fb_material_id, fb_amount = fb
        # Get full fabric block details
        fabric_block = get_fabric_block_recipe(fb_name, fb_material_id)
        if fabric_block:
            # Add the fabric block multiple times based on amount
            fabric_blocks.extend([fabric_block] * fb_amount)

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
            Process(name=proc_name, amount=proc_amount, activity_id=activity_id)
        )

    conn.close()

    recipe = GarmentRecipe(fabric_blocks=fabric_blocks, processes=processes)
    return recipe


def get_used_fabric_block(
    fabric_block_name: str, already_used_ids: list[int]
) -> SecondLifeFabricBlock | None:
    """Get a used/secondhand fabric block from inventory, excluding already-used IDs."""
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
            Process(name=prep_name, amount=prep_amount, activity_id=activity_id)
        )
    conn.close()
    return SecondLifeFabricBlock(
        id=fb_id,
        type_id=fb_type_id,
        co2eq=fb_co2eq,
        processes=preparations,
        location_id=fb_location_id,
        location_name=fb_location_name,
    )


def get_fabric_block_type_for_emission(
    fabric_block_name: str,
) -> tuple[int, int, float, float, str] | None:
    """Get fabric block type details for emission calculation.

    Returns tuple of (fabric_block_type_id, activity_id, sqm, kg_per_sqm, material_name)
    or None if not found.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT id, sqm
            FROM fabric_block_types
            WHERE name = ?
            LIMIT 1
            """,
            (fabric_block_name,),
        )
        row = cursor.fetchone()
        if not row:
            return None

    finally:
        conn.close()


def get_fabric_block_processes_for_emission(
    fabric_block_type_id: int,
) -> list[tuple[str, float, int]]:
    """Get fabric block processes for emission calculation.

    Returns list of tuples (process_name, process_amount, process_activity_id).
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT pt.name, fbrp.amount, pt.activity_id
            FROM fabric_block_recipe_processes fbrp
            JOIN process_types pt ON fbrp.process_id = pt.id
            WHERE fbrp.fabric_block_type = ?
            """,
            (fabric_block_type_id,),
        )
        return cursor.fetchall()
    finally:
        conn.close()
