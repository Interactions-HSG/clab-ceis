"""Database CRUD operations for CEIS backend."""

import sqlite3

from fastapi import HTTPException

from ceis_backend.config import DB_PATH
from ceis_backend.models import (
    FabricBlock,
    FabricBlockType,
    SecondLifeFabricBlock,
    GarmentRecipe,
    Process,
)


STRATEGIST_CIRCULARITY_THRESHOLD = 30.0


def db_create_garment_type(name: str, price_chf: float) -> dict:
    """Create a new garment type in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if price_chf <= 0:
            raise HTTPException(
                status_code=400, detail="price_chf must be greater than 0"
            )

        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES (?, ?)",
            (name, price_chf),
        )
        cursor.execute(
            "SELECT id, name, price_chf FROM garment_types WHERE id = ?",
            (cursor.lastrowid,),
        )
        created = cursor.fetchone()
        conn.commit()
        return {
            "id": created[0],
            "name": created[1],
            "price_chf": float(price_chf),
        }
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Garment type already exists")
    finally:
        conn.close()


def db_get_garment_types() -> list[dict]:
    """Get all garment types from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, price_chf FROM garment_types")
    garment_types = cursor.fetchall()
    conn.close()
    return [{"id": gt[0], "name": gt[1], "price_chf": gt[2]} for gt in garment_types]


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


def db_get_strategy_progress() -> dict:
    """Aggregate strategist-facing progress metrics from sold garments."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH sold_garments AS (
            SELECT gi.id, gi.type_id, gi.co2eq
            FROM garments_inventory gi
            WHERE gi.sold = 1
        ),
        total_recipe AS (
            SELECT sg.id AS garment_id,
                   COALESCE(SUM(fbt.sqm * grfb.amount), 0) AS total_recipe_sqm,
                   COALESCE(SUM(grfb.amount), 0) AS total_recipe_blocks
            FROM sold_garments sg
            LEFT JOIN garment_recipe_fabric_blocks grfb
                ON grfb.garment_type = sg.type_id
            LEFT JOIN fabric_block_types fbt
                ON fbt.id = grfb.fabric_block_id
            GROUP BY sg.id
        ),
        second_life AS (
            SELECT sg.id AS garment_id,
                   COALESCE(COUNT(fbi.id), 0) AS second_life_blocks,
                   COALESCE(SUM(fbt.sqm), 0) AS second_life_sqm
            FROM sold_garments sg
            LEFT JOIN fabric_blocks_inventory fbi
                ON fbi.garment_id = sg.id
               AND fbi.second_life = 1
            LEFT JOIN fabric_block_types fbt
                ON fbt.id = fbi.type_id
            GROUP BY sg.id
        )
        SELECT sg.id,
               gt.name,
               sg.co2eq,
               tr.total_recipe_blocks,
               sl.second_life_blocks,
               tr.total_recipe_sqm,
               sl.second_life_sqm
        FROM sold_garments sg
        JOIN garment_types gt ON gt.id = sg.type_id
        LEFT JOIN total_recipe tr ON tr.garment_id = sg.id
        LEFT JOIN second_life sl ON sl.garment_id = sg.id
        ORDER BY sg.id
        """
    )
    sold_garment_rows = cursor.fetchall()
    conn.close()

    sold_garments = []
    total_recipe_blocks = 0
    total_second_life_blocks = 0
    total_recipe_sqm = 0.0
    total_second_life_sqm = 0.0
    total_co2 = 0.0

    for row in sold_garment_rows:
        (
            garment_id,
            garment_name,
            co2eq,
            recipe_blocks,
            second_life_blocks,
            recipe_sqm,
            second_life_sqm,
        ) = row
        recipe_blocks = int(recipe_blocks or 0)
        second_life_blocks = int(second_life_blocks or 0)
        recipe_sqm = float(recipe_sqm or 0)
        second_life_sqm = float(second_life_sqm or 0)
        co2eq = float(co2eq or 0)

        total_recipe_blocks += recipe_blocks
        total_second_life_blocks += second_life_blocks
        total_recipe_sqm += recipe_sqm
        total_second_life_sqm += second_life_sqm
        total_co2 += co2eq

        circularity_pct = (
            round((second_life_blocks / recipe_blocks) * 100, 2)
            if recipe_blocks
            else 0.0
        )
        fabric_saved_pct = (
            round((second_life_sqm / recipe_sqm) * 100, 2) if recipe_sqm else 0.0
        )
        sold_garments.append(
            {
                "garment_id": garment_id,
                "garment_name": garment_name,
                "recipe_fabric_blocks": recipe_blocks,
                "second_life_fabric_blocks": second_life_blocks,
                "circularity_pct": circularity_pct,
                "fabric_saved_pct": fabric_saved_pct,
                "co2eq": round(co2eq, 2),
            }
        )

    circularity_pct = (
        round((total_second_life_blocks / total_recipe_blocks) * 100, 2)
        if total_recipe_blocks
        else 0.0
    )
    fabric_saved_pct = (
        round((total_second_life_sqm / total_recipe_sqm) * 100, 2)
        if total_recipe_sqm
        else 0.0
    )

    return {
        "thresholds": {
            "circularity_pct": STRATEGIST_CIRCULARITY_THRESHOLD,
        },
        "aggregates": {
            "sold_garments": len(sold_garments),
            "circularity_pct": circularity_pct,
            "circularity_threshold_delta": round(
                circularity_pct - STRATEGIST_CIRCULARITY_THRESHOLD, 2
            ),
            "fabric_saved_pct": fabric_saved_pct,
            "environmental_cost_co2eq": round(total_co2, 2),
            "second_life_fabric_blocks_sold": total_second_life_blocks,
            "recipe_fabric_blocks_sold": total_recipe_blocks,
        },
        "sold_garments": sold_garments,
    }


def db_get_sold_garments_for_co2() -> list[dict]:
    """Return sold garments that are still missing persisted CO2 values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT gi.id, gi.type_id, gt.name
        FROM garments_inventory gi
        JOIN garment_types gt ON gt.id = gi.type_id
        WHERE gi.sold = 1
          AND gi.co2eq IS NULL
        ORDER BY gi.id
        """
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "type_id": row[1], "name": row[2]} for row in rows]


def db_get_inventory_fabric_blocks_for_garment(garment_id: int) -> list[dict]:
    """Return actual fabric blocks linked to a garment inventory record."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT fbi.id,
               fbt.id,
               fbt.name,
               fbt.sqm,
               fbi.location_id,
               l.name,
               fbi.quality,
               fbi.second_life,
               m.id,
               m.name,
               m.kg_per_sqm,
               m.activity_id
        FROM fabric_blocks_inventory fbi
        JOIN fabric_block_types fbt ON fbt.id = fbi.type_id
        LEFT JOIN locations l ON l.id = fbi.location_id
        LEFT JOIN materials m ON m.id = fbi.material_id
        WHERE fbi.garment_id = ?
        ORDER BY fbi.id
        """,
        (garment_id,),
    )
    rows = cursor.fetchall()

    fabric_blocks = []
    for row in rows:
        (
            inventory_id,
            type_id,
            type_name,
            sqm,
            location_id,
            location_name,
            quality,
            second_life,
            material_id,
            material_name,
            kg_per_sqm,
            activity_id,
        ) = row

        cursor.execute(
            """
            SELECT pt.name, pfbi.amount, pt.activity_id
            FROM processes_fabric_blocks_inventory pfbi
            JOIN process_types pt ON pt.id = pfbi.process_id
            WHERE pfbi.fabric_block_id = ?
            ORDER BY pfbi.id
            """,
            (inventory_id,),
        )
        process_rows = cursor.fetchall()
        processes = [
            Process(name=process_name, amount=amount, activity_id=process_activity_id)
            for process_name, amount, process_activity_id in process_rows
        ]

        fabric_blocks.append(
            {
                "inventory_id": inventory_id,
                "type_id": type_id,
                "type_name": type_name,
                "sqm": float(sqm or 0),
                "location_id": location_id,
                "location_name": location_name,
                "quality": float(quality or 0),
                "second_life": bool(second_life),
                "material_id": material_id,
                "material_name": material_name,
                "kg_per_sqm": float(kg_per_sqm or 0),
                "activity_id": activity_id,
                "processes": processes,
            }
        )

    conn.close()
    return fabric_blocks


def db_get_garment_processes(garment_type_id: int) -> list[Process]:
    """Return recipe-level assembly processes for a garment type."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT pt.name, grp.amount, pt.activity_id
        FROM garment_recipe_processes grp
        JOIN process_types pt ON pt.id = grp.process_id
        WHERE grp.garment_type = ?
        ORDER BY grp.id
        """,
        (garment_type_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        Process(name=process_name, amount=amount, activity_id=activity_id)
        for process_name, amount, activity_id in rows
    ]


def db_get_garment_inventory_processes(garment_id: int) -> list[Process]:
    """Return garment-inventory-specific processes for a garment record."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT pt.name, pgi.amount, pt.activity_id
        FROM processes_garments_inventory pgi
        JOIN process_types pt ON pt.id = pgi.process_id
        WHERE pgi.garment_id = ?
        ORDER BY pgi.id
        """,
        (garment_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        Process(name=process_name, amount=amount, activity_id=activity_id)
        for process_name, amount, activity_id in rows
    ]


def db_update_garment_inventory_co2(garment_id: int, co2eq: float) -> None:
    """Persist the computed CO2 value for a garment inventory record."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE garments_inventory SET co2eq = ? WHERE id = ?",
        (round(co2eq, 6), garment_id),
    )
    conn.commit()
    conn.close()


def db_get_materials_for_garment(garment_type_id: int) -> list[dict]:
    """Get materials associated with a specific garment recipe."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.id, m.name, m.kg_per_sqm, m.activity_id
        FROM garment_recipe_materials grm
        JOIN materials m ON m.id = grm.material_id
        WHERE grm.garment_type = ?
        ORDER BY grm.id
        """,
        (garment_type_id,),
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


def db_get_recipe_fabric_blocks(garment_type_id: int) -> list[dict]:
    """Get fabric blocks associated with a specific garment recipe."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ft.id, ft.name, grfb.amount
        FROM garment_recipe_fabric_blocks grfb
        JOIN fabric_block_types ft ON ft.id = grfb.fabric_block_id
        WHERE grfb.garment_type = ?
        ORDER BY grfb.id
        """,
        (garment_type_id,),
    )
    fabric_blocks = cursor.fetchall()
    conn.close()
    return [
        {
            "fabric_block_id": row[0],
            "fabric_block": row[1],
            "amount": row[2],
        }
        for row in fabric_blocks
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
            "DELETE FROM garment_recipe_materials WHERE garment_type = ?",
            (garment_type_id,),
        )
        materials_deleted = cursor.rowcount
        cursor.execute(
            "DELETE FROM garment_recipe_processes WHERE garment_type = ?",
            (garment_type_id,),
        )
        processes_deleted = cursor.rowcount
        if (fabric_deleted + materials_deleted + processes_deleted) == 0:
            raise HTTPException(status_code=404, detail="Garment recipe not found")

        conn.commit()
        return {"message": "Garment recipe deleted"}
    finally:
        conn.close()


def db_create_fabric_block_type(name: str, sqm: float, processes: list) -> dict:
    """Create a new fabric block type in the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if sqm <= 0:
            raise HTTPException(status_code=400, detail="sqm must be greater than 0")

        if processes:
            process_ids = [proc.process_id for proc in processes]
            cursor.execute(
                f"SELECT COUNT(*) FROM process_types WHERE id IN ({','.join('?' * len(process_ids))})",
                process_ids,
            )
            if cursor.fetchone()[0] != len(set(process_ids)):
                raise HTTPException(status_code=400, detail="Invalid process type")

        for proc in processes:
            if proc.amount <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Process amount must be greater than 0",
                )

        cursor.execute(
            """
            INSERT INTO fabric_block_types (name, sqm)
            VALUES (?, ?)
            """,
            (name, sqm),
        )
        fabric_block_type_id = cursor.lastrowid

        if processes:
            cursor.executemany(
                """
                INSERT INTO fabric_block_recipe_processes
                (fabric_block_type, process_id, amount)
                VALUES (?, ?, ?)
                """,
                [
                    (fabric_block_type_id, proc.process_id, proc.amount)
                    for proc in processes
                ],
            )

        conn.commit()
        return {"id": fabric_block_type_id, "name": name}
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
            "DELETE FROM processes_fabric_blocks_inventory WHERE process_id = ?",
            (type_id,),
        )
        cursor.execute(
            "DELETE FROM processes_garments_inventory WHERE process_id = ?",
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
    garment_type_name: str, fabric_blocks: list, materials: list, processes: list
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

        material_ids = sorted(
            {
                m.material_id
                for m in materials
                if getattr(m, "material_id", None) is not None
            }
        )
        if not material_ids:
            raise HTTPException(
                status_code=400,
                detail="Garment recipe must include at least one material",
            )
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
            "DELETE FROM garment_recipe_materials WHERE garment_type = ?",
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

        cursor.executemany(
            """
            INSERT INTO garment_recipe_materials
            (garment_type, material_id)
            VALUES (?, ?)
            """,
            [(garment_type_id, material_id) for material_id in material_ids],
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
    type_id: int,
    location_id: int | None,
    material_id: int | None,
    quality: float,
    processes: list,
) -> dict:
    """Create a new fabric block in the inventory."""
    if quality < 0 or quality > 100:
        raise HTTPException(status_code=400, detail="quality must be between 0 and 100")

    co2eq = None  # Placeholder
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if material_id is not None:
        cursor.execute("SELECT 1 FROM materials WHERE id = ?", (material_id,))
        if cursor.fetchone() is None:
            conn.close()
            raise HTTPException(status_code=400, detail="Invalid material")

    cursor.execute(
        """
        INSERT INTO fabric_blocks_inventory (type_id, co2eq, location_id, material_id, quality, second_life)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (type_id, co2eq, location_id, material_id, quality, 1),
    )
    fabric_block_id = cursor.lastrowid
    if not fabric_block_id:
        conn.close()
        return {"error": "Invalid fabric block type"}

    if processes:
        cursor.executemany(
            """
            INSERT INTO processes_fabric_blocks_inventory (process_id, amount, fabric_block_id)
            VALUES (?, ?, ?)
            """,
            [
                (process.process_id, process.amount, fabric_block_id)
                for process in processes
            ],
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
                   SELECT fbi.id, fbi.type_id, fbi.co2eq, fbi.garment_id, l.name as location_name, m.name as material_name, fbi.quality
                   FROM fabric_blocks_inventory fbi
                   LEFT JOIN locations l ON fbi.location_id = l.id
                   LEFT JOIN materials m ON fbi.material_id = m.id
                   WHERE fbi.type_id = ? OR ? IS NULL
                   """,
        (type_filter, type_filter),
    )
    fabric_blocks_data = cursor.fetchall()

    fabric_blocks = []
    for fb in fabric_blocks_data:
        fb_id, fb_type, fb_co2eq, garment_id, location_name, material_name, quality = fb
        cursor.execute(
            "SELECT name FROM fabric_block_types WHERE id = ?",
            (fb_type,),
        )
        fb_type_name = cursor.fetchone()
        fb_type_name = fb_type_name[0] if fb_type_name else None
        cursor.execute(
            """
            SELECT pt.name, pfbi.amount
            FROM processes_fabric_blocks_inventory pfbi
            JOIN process_types pt ON pfbi.process_id = pt.id
            WHERE pfbi.fabric_block_id = ?
            """,
            (fb_id,),
        )
        inventory_processes_data = cursor.fetchall()
        processes = [{"type": p[0], "amount": p[1]} for p in inventory_processes_data]
        fabric_blocks.append(
            {
                "id": fb_id,
                "type": fb_type_name,
                "co2eq": fb_co2eq,
                "garment_id": garment_id,
                "location": location_name,
                "material": material_name,
                "quality": quality,
                "processes": processes,
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
            "DELETE FROM processes_fabric_blocks_inventory WHERE fabric_block_id = ?",
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
    fabric_block_name: str, material_id: int
) -> FabricBlock | None:
    """Get a fabric block recipe with all its processes for a specific material."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get fabric block type details
    cursor.execute(
        "SELECT id, sqm FROM fabric_block_types WHERE name = ?",
        (fabric_block_name,),
    )
    result = cursor.fetchone()
    if not result:
        conn.close()
        return None

    fabric_block_type_id = result[0]
    fabric_block_sqm = result[1]

    cursor.execute(
        "SELECT name, kg_per_sqm, activity_id FROM materials WHERE id = ?",
        (material_id,),
    )
    material_row = cursor.fetchone()
    if not material_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid material")

    selected_material_name = material_row[0]
    selected_kg_per_sqm = material_row[1]
    selected_activity_id = material_row[2]

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
        weight_kg=selected_kg_per_sqm * fabric_block_sqm,
        activity_id=selected_activity_id,
        processes=processes,
    )


def get_full_garment_recipe(
    garment_type_id: int, material_id: int
) -> GarmentRecipe | None:
    """Get a complete garment recipe including all fabric blocks and processes."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM garment_types WHERE id = ?", (garment_type_id,))
    if not cursor.fetchone():
        return None

    cursor.execute(
        """
        SELECT ft.name, grfb.amount
        FROM garment_recipe_fabric_blocks grfb
        JOIN fabric_block_types ft ON grfb.fabric_block_id = ft.id
        WHERE grfb.garment_type = ?
    """,
        (garment_type_id,),
    )

    fabric_blocks_data = cursor.fetchall()

    cursor.execute(
        "SELECT id FROM materials WHERE id = ?",
        (material_id,),
    )
    material_row = cursor.fetchone()
    if not material_row:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid material")
    selected_material_id = material_row[0]

    cursor.execute(
        """
        SELECT 1
        FROM garment_recipe_materials
        WHERE garment_type = ? AND material_id = ?
        LIMIT 1
        """,
        (garment_type_id, selected_material_id),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=400,
            detail="Material is not associated with this garment recipe",
        )

    fabric_blocks: list[FabricBlock] = []
    for fb in fabric_blocks_data:
        fb_name, fb_amount = fb
        # Get full fabric block details
        fabric_block = get_fabric_block_recipe(fb_name, selected_material_id)
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


def get_manufacturer_distance_km(
    source_company: str, destination_company: str
) -> float | None:
    """Return the stored transport distance between two manufacturers."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT distance_km
            FROM manufacturer_distances
            WHERE source_company = ? AND destination_company = ?
            LIMIT 1
            """,
            (source_company, destination_company),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return float(row[0])
    finally:
        conn.close()


def db_get_manufacturer_distance_row(
    source_company: str, destination_company: str
) -> dict | None:
    """Return the stored transport row between two manufacturers."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT source_company,
                   source_role_group,
                   source_location,
                   destination_company,
                   destination_role_group,
                   destination_location,
                   distance_km
            FROM manufacturer_distances
            WHERE source_company = ? AND destination_company = ?
            LIMIT 1
            """,
            (source_company, destination_company),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "source_company": row[0],
            "source_role_group": row[1],
            "source_location": row[2],
            "destination_company": row[3],
            "destination_role_group": row[4],
            "destination_location": row[5],
            "distance_km": float(row[6]),
        }
    finally:
        conn.close()


def db_get_manufacturers(role_group: str | None = None) -> list[dict]:
    """Return manufacturers, optionally filtered by role group."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        if role_group is None:
            cursor.execute(
                """
                SELECT company, role, role_group, location
                FROM manufacturers
                ORDER BY role_group, company
                """
            )
        else:
            cursor.execute(
                """
                SELECT company, role, role_group, location
                FROM manufacturers
                WHERE role_group = ?
                ORDER BY company
                """,
                (role_group,),
            )
        rows = cursor.fetchall()
        return [
            {
                "company": row[0],
                "role": row[1],
                "role_group": row[2],
                "location": row[3],
            }
            for row in rows
        ]
    finally:
        conn.close()


def get_used_fabric_block(
    fabric_block_name: str,
    already_used_ids: list[int],
    preferred_material: str | None = None,
) -> SecondLifeFabricBlock | None:
    """Get a fabric block from inventory, excluding already-used IDs."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    base_query = """
        SELECT fbi.id, fbi.type_id, fbi.co2eq, fbi.location_id, l.name as location_name,
    """
    base_query += "fbi.quality"
    base_query += ", "
    base_query += "m.name"
    base_query += """
        FROM fabric_blocks_inventory fbi
        JOIN fabric_block_types fbt ON fbi.type_id = fbt.id
        LEFT JOIN locations l ON fbi.location_id = l.id
    """
    base_query += "LEFT JOIN materials m ON fbi.material_id = m.id"
    base_query += """
        WHERE fbt.name = ?
          AND fbi.garment_id IS NULL
    """

    params = [fabric_block_name]

    if already_used_ids:
        placeholders = ",".join("?" * len(already_used_ids))
        base_query += f" AND fbi.id NOT IN ({placeholders})"
        params.extend(str(id) for id in already_used_ids)

    if preferred_material:
        base_query += " ORDER BY CASE WHEN m.name = ? THEN 0 ELSE 1 END, fbi.id"
        params.append(preferred_material)
    else:
        base_query += " ORDER BY fbi.id"

    base_query += " LIMIT 1"

    cursor.execute(base_query, params)
    result = cursor.fetchone()

    if not result:
        conn.close()
        return None

    (
        fb_id,
        fb_type_id,
        fb_co2eq,
        fb_location_id,
        fb_location_name,
        fb_quality,
        fb_material,
    ) = result
    cursor.execute(
        """
        SELECT pt.name, pfbi.amount, pt.activity_id
        FROM processes_fabric_blocks_inventory pfbi
        JOIN process_types pt ON pfbi.process_id = pt.id
        WHERE pfbi.fabric_block_id = ?
        """,
        (fb_id,),
    )
    inventory_processes_data = cursor.fetchall()
    processes: list[Process] = []
    for process in inventory_processes_data:
        process_name, process_amount, activity_id = process
        processes.append(
            Process(name=process_name, amount=process_amount, activity_id=activity_id)
        )
    conn.close()
    return SecondLifeFabricBlock(
        id=fb_id,
        type_id=fb_type_id,
        co2eq=fb_co2eq,
        processes=processes,
        location_id=fb_location_id,
        location_name=fb_location_name,
        material=fb_material,
        quality=float(fb_quality),
    )


def get_fabric_block_type_for_emission(
    fabric_block_name: str,
) -> FabricBlockType | None:
    """Get fabric block type details for emission calculation.

    Returns FabricBlockType or None if not found.
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
        fb_type_id, fb_sqm = row
        return FabricBlockType(id=fb_type_id, name=fabric_block_name, sqm=fb_sqm)
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
