import json
import os
import sqlite3
from pathlib import Path

from ceis_backend.config import DB_PATH
from ceis_backend.manufacturer_distance_sync import (
    sync_manufacturer_distances_if_changed,
)

SEED_DATA_PATH = Path(__file__).with_name("data") / "seed_data.json"


def load_seed_data():
    with SEED_DATA_PATH.open(encoding="utf-8") as seed_file:
        return json.load(seed_file)


def _id_for_name(cursor, table, name):
    cursor.execute(f"SELECT id FROM {table} WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row is None:
        raise ValueError(f"Missing seed dependency: {table}.{name}")
    return row[0]


def _insert_recipe_row(cursor, table, values, identity_columns):
    columns = tuple(values)
    placeholders = ", ".join("?" for _ in columns)
    identity_clause = " AND ".join(f"{column} = ?" for column in identity_columns)
    cursor.execute(
        f"""
        INSERT INTO {table} ({", ".join(columns)})
        SELECT {placeholders}
        WHERE NOT EXISTS (
            SELECT 1 FROM {table} WHERE {identity_clause}
        )
        """,
        tuple(values.values()) + tuple(values[column] for column in identity_columns),
    )


def seed_data(cursor):
    seed_data = load_seed_data()

    cursor.executemany(
        """
        INSERT OR IGNORE INTO materials (
            name, kg_per_sqm, cost_per_sqm_chf, activity_id
        ) VALUES (:name, :kg_per_sqm, :cost_per_sqm_chf, :activity_id)
        """,
        seed_data["materials"],
    )
    cursor.executemany(
        "INSERT OR IGNORE INTO locations (name) VALUES (:name)",
        seed_data["locations"],
    )
    cursor.executemany(
        """
        INSERT OR IGNORE INTO fabric_block_types (name, sqm)
        VALUES (:name, :sqm)
        """,
        seed_data["fabric_block_types"],
    )
    cursor.executemany(
        """
        INSERT OR IGNORE INTO process_types (name, unit, activity_id)
        VALUES (:name, :unit, :activity_id)
        """,
        seed_data["process_types"],
    )
    cursor.executemany(
        """
        INSERT OR IGNORE INTO garment_types (name, price_chf)
        VALUES (:name, :price_chf)
        """,
        seed_data["garment_types"],
    )

    for garment in seed_data["garment_types"]:
        garment_id = _id_for_name(cursor, "garment_types", garment["name"])

        for fabric_block_name, amount in garment["fabric_blocks"].items():
            _insert_recipe_row(
                cursor,
                "garment_recipe_fabric_blocks",
                {
                    "garment_type": garment_id,
                    "fabric_block_id": _id_for_name(
                        cursor, "fabric_block_types", fabric_block_name
                    ),
                    "amount": amount,
                },
                ("garment_type", "fabric_block_id"),
            )

        for material_name in garment["materials"]:
            _insert_recipe_row(
                cursor,
                "garment_recipe_materials",
                {
                    "garment_type": garment_id,
                    "material_id": _id_for_name(
                        cursor, "materials", material_name
                    ),
                },
                ("garment_type", "material_id"),
            )

        for process in seed_data["default_garment_processes"]:
            _insert_recipe_row(
                cursor,
                "garment_recipe_processes",
                {
                    "garment_type": garment_id,
                    "process_id": _id_for_name(
                        cursor, "process_types", process["process"]
                    ),
                    "amount": process["amount"],
                },
                ("garment_type", "process_id"),
            )

    for process in seed_data["fabric_block_processes"]:
        _insert_recipe_row(
            cursor,
            "fabric_block_recipe_processes",
            {
                "fabric_block_type": _id_for_name(
                    cursor, "fabric_block_types", process["fabric_block"]
                ),
                "process_id": _id_for_name(
                    cursor, "process_types", process["process"]
                ),
                "amount": process["amount"],
            },
            ("fabric_block_type", "process_id"),
        )


def _insert_demo_fabric_block(cursor, fabric_block, garment_id=None):
    cursor.execute(
        """
        INSERT INTO fabric_blocks_inventory (
            type_id, co2eq, garment_id, location_id, material_id, quality,
            second_life
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _id_for_name(cursor, "fabric_block_types", fabric_block["type"]),
            fabric_block.get("co2eq"),
            garment_id,
            _id_for_name(cursor, "locations", fabric_block["location"]),
            _id_for_name(cursor, "materials", fabric_block["material"]),
            fabric_block["quality"],
            fabric_block["second_life"],
        ),
    )


def seed_demo_sales_data(cursor):
    cursor.execute("SELECT COUNT(*) FROM garments_inventory")
    if cursor.fetchone()[0] > 0:
        return

    seed_data = load_seed_data()
    for garment in seed_data["demo_garments"]:
        cursor.execute(
            """
            INSERT INTO garments_inventory (type_id, co2eq, price, sold)
            VALUES (?, ?, ?, ?)
            """,
            (
                _id_for_name(cursor, "garment_types", garment["garment_type"]),
                garment["co2eq"],
                garment["price"],
                garment["sold"],
            ),
        )
        garment_id = cursor.lastrowid
        for fabric_block in garment["fabric_blocks"]:
            _insert_demo_fabric_block(cursor, fabric_block, garment_id)

    for fabric_block in seed_data["loose_demo_fabric_blocks"]:
        _insert_demo_fabric_block(cursor, fabric_block)


def create_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS garment_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            price_chf REAL NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            kg_per_sqm REAL NOT NULL,
            cost_per_sqm_chf REAL,
            activity_id INTEGER NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fabric_block_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            sqm REAL NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS process_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT,
            activity_id INTEGER NOT NULL,
            UNIQUE(name, unit)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS garment_recipe_fabric_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            garment_type INTEGER NOT NULL,
            fabric_block_id INTEGER NOT NULL,
            amount INTEGER,
            FOREIGN KEY (garment_type) REFERENCES garment_types(id) ON DELETE CASCADE,
            FOREIGN KEY (fabric_block_id) REFERENCES fabric_block_types(id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS garment_recipe_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            garment_type INTEGER NOT NULL,
            material_id INTEGER NOT NULL,
            FOREIGN KEY (garment_type) REFERENCES garment_types(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
            UNIQUE(garment_type, material_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS garment_recipe_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            garment_type INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            amount REAL,
            FOREIGN KEY (garment_type) REFERENCES garment_types(id) ON DELETE CASCADE,
            FOREIGN KEY (process_id) REFERENCES process_types(id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fabric_block_recipe_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fabric_block_type INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            amount REAL,
            FOREIGN KEY (fabric_block_type) REFERENCES fabric_block_types(id) ON DELETE CASCADE,
            FOREIGN KEY (process_id) REFERENCES process_types(id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS garments_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_id INTEGER NOT NULL,
            co2eq INTEGER,
            price INTEGER,
            sold INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (type_id) REFERENCES garment_types (id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fabric_blocks_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_id INTEGER NOT NULL,
            co2eq INTEGER,
            garment_id INTEGER,
            location_id INTEGER,
            material_id INTEGER,
            quality REAL NOT NULL DEFAULT 100,
            second_life INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (type_id) REFERENCES fabric_block_types (id) ON DELETE CASCADE,
            FOREIGN KEY (garment_id) REFERENCES garments_inventory (id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE SET NULL,
            FOREIGN KEY (material_id) REFERENCES materials (id) ON DELETE SET NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processes_fabric_blocks_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_id INTEGER NOT NULL,
            amount REAL,
            fabric_block_id INTEGER,
            FOREIGN KEY (process_id) REFERENCES process_types (id) ON DELETE CASCADE,
            FOREIGN KEY (fabric_block_id) REFERENCES fabric_blocks_inventory (id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS processes_garments_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_id INTEGER NOT NULL,
            amount REAL,
            garment_id INTEGER NOT NULL,
            FOREIGN KEY (process_id) REFERENCES process_types (id) ON DELETE CASCADE,
            FOREIGN KEY (garment_id) REFERENCES garments_inventory (id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            role_group TEXT NOT NULL,
            location TEXT NOT NULL,
            UNIQUE(company, role_group)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS manufacturer_distances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_company TEXT NOT NULL,
            source_role_group TEXT NOT NULL,
            source_location TEXT NOT NULL,
            destination_company TEXT NOT NULL,
            destination_role_group TEXT NOT NULL,
            destination_location TEXT NOT NULL,
            distance_km REAL NOT NULL,
            UNIQUE(source_company, destination_company)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            garment_type_id INTEGER NOT NULL,
            material_id INTEGER,
            garment_inventory_id INTEGER,
            fulfillment_type TEXT NOT NULL CHECK (fulfillment_type IN ('stock', 'production')),
            status TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (garment_type_id) REFERENCES garment_types(id),
            FOREIGN KEY (material_id) REFERENCES materials(id),
            FOREIGN KEY (garment_inventory_id) REFERENCES garments_inventory(id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS material_manufacturer_distances (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            destination_manufacturer_id INTEGER NOT NULL,
            distance_km REAL NOT NULL,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
            FOREIGN KEY (destination_manufacturer_id) REFERENCES manufacturers(id) ON DELETE CASCADE,
            UNIQUE(material_id, destination_manufacturer_id)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_trigger TEXT NOT NULL,
            timestamp TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            request_type TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            co2eq REAL,
            status TEXT NOT NULL,
            lifecycle_node TEXT,
            lifecycle_edge TEXT,
            manufacturer_id INTEGER,
            manufacturer_distance_id INTEGER,
            material_id INTEGER,
            material_manufacturer_distance_id INTEGER,
            order_id INTEGER,
            FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(id) ON DELETE CASCADE,
            FOREIGN KEY (manufacturer_distance_id) REFERENCES manufacturer_distances(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE,
            FOREIGN KEY (material_manufacturer_distance_id) REFERENCES material_manufacturer_distances(id) ON DELETE CASCADE,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            CHECK (
                (manufacturer_id IS NOT NULL) +
                (manufacturer_distance_id IS NOT NULL) +
                (material_id IS NOT NULL) +
                (material_manufacturer_distance_id IS NOT NULL) <= 1
            )
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sync_state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS geocode_cache (
            address TEXT PRIMARY KEY,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS activity_emission_cache (
            activity_id INTEGER PRIMARY KEY,
            emission_per_unit REAL,
            cached_at REAL NOT NULL
        )
    """
    )


def seed_material_supply_chain(cursor):
    for distance in load_seed_data()["material_supply_chain"]:
        cursor.execute(
            """
            INSERT OR IGNORE INTO material_manufacturer_distances (
                material_id, destination_manufacturer_id, distance_km
            )
            SELECT materials.id, manufacturers.id, ?
            FROM materials CROSS JOIN manufacturers
            WHERE materials.name = ? AND manufacturers.role_group = 'fabric'
            """,
            (distance["distance_km"], distance["material"]),
        )


RESOURCE_EVENT_LINK_COLUMNS = {
    "manufacturer_id",
    "manufacturer_distance_id",
    "material_id",
    "material_manufacturer_distance_id",
}


def _resource_event_exists(cursor, column, value):
    if column not in RESOURCE_EVENT_LINK_COLUMNS | {
        "lifecycle_node",
        "lifecycle_edge",
    }:
        raise ValueError(f"Unsupported resource event identity: {column}")
    cursor.execute(
        f"SELECT 1 FROM resource_events WHERE {column} = ?",
        (value,),
    )
    return cursor.fetchone() is not None


def _insert_resource_event(cursor, event, timestamp_offset="0 minutes"):
    cursor.execute(
        """
        INSERT INTO resource_events (
            event_trigger, timestamp, request_type, resource_type, co2eq, status,
            lifecycle_node, lifecycle_edge, manufacturer_id,
            manufacturer_distance_id, material_id,
            material_manufacturer_distance_id
        ) VALUES (?, datetime('now', ?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_trigger"],
            timestamp_offset,
            event["request_type"],
            event["resource_type"],
            event["co2eq"],
            event["status"],
            event.get("lifecycle_node"),
            event.get("lifecycle_edge"),
            event.get("manufacturer_id"),
            event.get("manufacturer_distance_id"),
            event.get("material_id"),
            event.get("material_manufacturer_distance_id"),
        ),
    )


def seed_resource_events(cursor):
    """Seed resource events from JSON templates and current supply-chain rows."""
    seed_data = load_seed_data()["resource_events"]
    defaults = seed_data["defaults"]

    cursor.execute(
        "SELECT id, role, role_group FROM manufacturers ORDER BY id"
    )
    for manufacturer_id, role, role_group in cursor.fetchall():
        if _resource_event_exists(cursor, "manufacturer_id", manufacturer_id):
            continue
        template = seed_data["manufacturer_roles"].get(
            role_group,
            seed_data["manufacturer_roles"]["default"],
        )
        _insert_resource_event(
            cursor,
            {
                **defaults,
                **template,
                "resource_type": role,
                "manufacturer_id": manufacturer_id,
            },
            f"-{manufacturer_id} minutes",
        )

    lifecycle_nodes = seed_data["lifecycle_nodes"]
    for lifecycle_node in lifecycle_nodes["values"]:
        if _resource_event_exists(cursor, "lifecycle_node", lifecycle_node):
            continue
        _insert_resource_event(
            cursor,
            {
                **defaults,
                "event_trigger": lifecycle_node,
                "resource_type": lifecycle_nodes["resource_type"],
                "lifecycle_node": lifecycle_node,
            },
        )

    lifecycle_edges = seed_data["lifecycle_edges"]
    for lifecycle_edge in lifecycle_edges["values"]:
        if _resource_event_exists(cursor, "lifecycle_edge", lifecycle_edge):
            continue
        _insert_resource_event(
            cursor,
            {
                **defaults,
                "event_trigger": lifecycle_edge,
                "resource_type": lifecycle_edges["resource_type"],
                "lifecycle_edge": lifecycle_edge,
            },
        )

    materials = seed_data["materials"]
    cursor.execute("SELECT id, name FROM materials ORDER BY id")
    for material_id, material_name in cursor.fetchall():
        if (
            material_name not in materials["names"]
            or _resource_event_exists(cursor, "material_id", material_id)
        ):
            continue
        _insert_resource_event(
            cursor,
            {
                **defaults,
                "event_trigger": materials["event_trigger"],
                "resource_type": material_name,
                "lifecycle_node": materials["lifecycle_node"],
                "material_id": material_id,
            },
            f"-{200 + material_id} minutes",
        )

    material_transport = seed_data["material_transport"]
    cursor.execute("SELECT id FROM material_manufacturer_distances ORDER BY id")
    for (distance_id,) in cursor.fetchall():
        if _resource_event_exists(
            cursor, "material_manufacturer_distance_id", distance_id
        ):
            continue
        _insert_resource_event(
            cursor,
            {
                **defaults,
                **material_transport,
                "material_manufacturer_distance_id": distance_id,
            },
            f"-{300 + distance_id} minutes",
        )

    manufacturer_transport = seed_data["manufacturer_transport"]
    cursor.execute(
        """
        SELECT id, source_company, destination_company, source_role_group
        FROM manufacturer_distances
        ORDER BY id
        """
    )
    for distance_id, source, destination, source_role_group in cursor.fetchall():
        if (
            source == destination
            or _resource_event_exists(
                cursor, "manufacturer_distance_id", distance_id
            )
        ):
            continue
        lifecycle_edge = (
            manufacturer_transport["fabric_lifecycle_edge"]
            if source_role_group == "fabric"
            else manufacturer_transport["default_lifecycle_edge"]
        )
        _insert_resource_event(
            cursor,
            {
                **defaults,
                "event_trigger": manufacturer_transport["event_trigger"],
                "resource_type": manufacturer_transport["resource_type"],
                "lifecycle_edge": lifecycle_edge,
                "manufacturer_distance_id": distance_id,
            },
            f"-{100 + distance_id} minutes",
        )


def init_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    create_tables(cursor)
    seed_data(cursor)
    seed_demo_sales_data(cursor)
    seed_material_supply_chain(cursor)
    seed_resource_events(cursor)

    conn.commit()
    conn.close()

    disable_sync = os.getenv("CEIS_DISABLE_DISTANCE_SYNC", "0") == "1"
    is_pytest = "PYTEST_CURRENT_TEST" in os.environ
    print(f"Database path: {DB_PATH}")
    print(f"Manufacturer distance sync enabled: {not disable_sync and not is_pytest}")
    if disable_sync or is_pytest:
        print("Manufacturer distance sync skipped by environment.")
        return
    try:
        sync_result = sync_manufacturer_distances_if_changed()
        print(f"Manufacturer distance sync result: {sync_result}")
    except Exception:
        # Distance sync is best-effort and must not block DB startup.
        print("Manufacturer distance sync failed unexpectedly.")
        return

    # A fresh database receives manufacturers during sync, so seed graph events after it.
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    seed_material_supply_chain(cursor)
    seed_resource_events(cursor)
    conn.commit()
    conn.close()
