import sqlite3
import os

from ceis_backend.config import DB_PATH
from ceis_backend.manufacturer_distance_sync import (
    sync_manufacturer_distances_if_changed,
)


def create_tables(cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS garment_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            kg_per_sqm REAL NOT NULL,
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
            material_id INTEGER,
            amount INTEGER,
            FOREIGN KEY (garment_type) REFERENCES garment_types(id) ON DELETE CASCADE,
            FOREIGN KEY (fabric_block_id) REFERENCES fabric_block_types(id) ON DELETE CASCADE,
            FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE SET NULL
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
            FOREIGN KEY (type_id) REFERENCES fabric_block_types (id) ON DELETE CASCADE,
            FOREIGN KEY (garment_id) REFERENCES garments_inventory (id) ON DELETE CASCADE,
            FOREIGN KEY (location_id) REFERENCES locations (id) ON DELETE SET NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_id INTEGER NOT NULL,
            amount REAL,
            fabric_block_id INTEGER,
            FOREIGN KEY (type_id) REFERENCES process_types (id) ON DELETE CASCADE,
            FOREIGN KEY (fabric_block_id) REFERENCES fabric_blocks_inventory (id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS manufacturers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL UNIQUE,
            role TEXT NOT NULL,
            role_group TEXT NOT NULL,
            location TEXT NOT NULL
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

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS seed_meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            seeded INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO seed_meta (id, seeded) VALUES (1, 0);
    """
    )


def seed_data(cursor):
    cursor.execute("SELECT seeded FROM seed_meta WHERE id = 1;")
    if cursor.fetchone()[0] != 0:
        print("Database already seeded, skipping seeding.")
        return

    cursor.executescript(
        """
        INSERT OR IGNORE INTO locations (name) VALUES
        ('St. Gallen'),
        ('Sigmaringen'),
        ('Dornbirn'),
        ('Ravensburg');

        INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES
        ('hemp', 0.21, 276186);

        INSERT OR IGNORE INTO garment_types (name) VALUES
        ('Crop Top'),
        ('Shirt');

        INSERT OR IGNORE INTO fabric_block_types (name, sqm) VALUES
        ('80x64', 0.512),
        ('40x14', 0.056),
        ('64x40', 0.256);

        INSERT OR IGNORE INTO process_types (name, unit, activity_id) VALUES
        ('sewing', 'kWh', 6566),
        ('steaming', 'kWh', 6566),
        ('washing', 'kWh', 6566),
        ('dyeing', 'kg', 21893),
        -- Transport of fabric to Cristina. Assumes lorry, >32 metric ton, diesel, EURO 5
        ('transport', 'tkm', 17901);

        INSERT OR IGNORE INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, material_id, amount) VALUES
        ((SELECT id FROM garment_types WHERE name='Crop Top'), (SELECT id FROM fabric_block_types WHERE name='80x64'), (SELECT id FROM materials WHERE name='hemp'), 1),
        ((SELECT id FROM garment_types WHERE name='Crop Top'), (SELECT id FROM fabric_block_types WHERE name='40x14'), (SELECT id FROM materials WHERE name='hemp'), 2),
        ((SELECT id FROM garment_types WHERE name='Shirt'), (SELECT id FROM fabric_block_types WHERE name='80x64'), (SELECT id FROM materials WHERE name='hemp'), 1),
        ((SELECT id FROM garment_types WHERE name='Shirt'), (SELECT id FROM fabric_block_types WHERE name='40x14'), (SELECT id FROM materials WHERE name='hemp'), 1),
        ((SELECT id FROM garment_types WHERE name='Shirt'), (SELECT id FROM fabric_block_types WHERE name='64x40'), (SELECT id FROM materials WHERE name='hemp'), 4);

        INSERT OR IGNORE INTO garment_recipe_processes (garment_type, process_id, amount) VALUES
        ((SELECT id FROM garment_types WHERE name='Crop Top'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Shirt'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Shirt'), (SELECT id FROM process_types WHERE name='steaming'), 0.22);

        INSERT OR IGNORE INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES
        -- transport to Cristina is calculated: Distance from Istanbul to Roermond to Bucharest: 4570 km / 1000 (because transport emission is per tkm) * weight of the fabric block (kg). This calculation might need to be automated.
        ((SELECT id FROM fabric_block_types WHERE name='80x64'), (SELECT id FROM process_types WHERE name='transport'), 0.49),
        ((SELECT id FROM fabric_block_types WHERE name='80x64'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), (SELECT id FROM process_types WHERE name='transport'), 0.054),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), (SELECT id FROM process_types WHERE name='transport'), 0.246),
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01);
    """
    )
    cursor.execute("UPDATE seed_meta SET seeded = 1 WHERE id = 1;")


def init_sqlite_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    create_tables(cursor)
    seed_data(cursor)

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
