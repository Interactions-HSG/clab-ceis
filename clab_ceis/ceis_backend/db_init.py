import sqlite3
import os

from ceis_backend.config import DB_PATH
from ceis_backend.manufacturer_distance_sync import (
    sync_manufacturer_distances_if_changed,
)
from ceis_backend.data.location_details import (
    COTTON_DISTANCE_TO_MANUFACTURER_KM,
    HEMP_DISTANCE_TO_MANUFACTURER_KM,
    SILK_DISTANCE_TO_MANUFACTURER_KM,
)

MATERIAL_SEED_DATA = {
    "cotton": {
        "kg_per_sqm": 0.14,
        "cost_per_sqm_chf": 2.52,
        "activity_id": 6756,
    },
    "hemp": {
        "kg_per_sqm": 0.21,
        "cost_per_sqm_chf": 5.04,
        "activity_id": 276186,
    },
    "silk": {
        "kg_per_sqm": 0.082,
        "cost_per_sqm_chf": 3.444,
        "activity_id": 20936,
    },
    "mikado silk": {
        "kg_per_sqm": 0.13,
        "cost_per_sqm_chf": 6.37,
        "activity_id": 20936,
    },
}

GARMENT_PRICE_CHF = {
    "Basic Trousers": 246.70,
    "Full Trousers": 263.50,
    "Basic Jumpsuit short sleeves": 282.20,
    "Basic Jumpsuit long sleeves": 299.00,
    "Elegant cowl neck top": 124.00,
    "Elegant cowl neck dress": 146.40,
    "Wrap Skirt": 136.60,
    "Daily dress with pocket": 168.40,
    "Cocktail fitted dress": 339.20,
    "Long tabard": 128.80,
    "Cocoon jacket": 240.60,
    "Orka jacket": 101.60,
    "Nordlys Dress": 279.60,
    "Mangata Dress": 280.20,
    "Måne top": 127.80,
    "Sommar Skirt": 183.20,
    "Basic Unisex Shirt with pocket": 131.00,
    "Basic Crop Top": 97.40,
}


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

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS seed_meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            seeded INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO seed_meta (id, seeded) VALUES (1, 0);
    """
    )

    # Keep development databases created by an earlier revision forward-compatible.
    cursor.execute("PRAGMA table_info(resource_events)")
    resource_event_columns = {row[1] for row in cursor.fetchall()}
    for column, definition in (
        ("material_id", "INTEGER REFERENCES materials(id) ON DELETE CASCADE"),
        (
            "material_manufacturer_distance_id",
            "INTEGER REFERENCES material_manufacturer_distances(id) ON DELETE CASCADE",
        ),
    ):
        if column not in resource_event_columns:
            cursor.execute(
                f"ALTER TABLE resource_events ADD COLUMN {column} {definition}"
            )

    cursor.execute("PRAGMA table_info(materials)")
    material_columns = {row[1] for row in cursor.fetchall()}
    if "cost_per_sqm_chf" not in material_columns:
        cursor.execute("ALTER TABLE materials ADD COLUMN cost_per_sqm_chf REAL")
    cursor.executemany(
        """
        UPDATE materials
        SET cost_per_sqm_chf = ?
        WHERE name = ? AND cost_per_sqm_chf IS NULL
        """,
        [
            (material["cost_per_sqm_chf"], material_name)
            for material_name, material in MATERIAL_SEED_DATA.items()
        ],
    )

    cursor.execute(
        "SELECT 1 FROM sync_state WHERE key = 'workbook_garment_prices_v1'"
    )
    if cursor.fetchone() is None:
        cursor.executemany(
            """
            UPDATE garment_types
            SET price_chf = ?
            WHERE name = ? AND price_chf = 100
            """,
            [
                (price_chf, garment_name)
                for garment_name, price_chf in GARMENT_PRICE_CHF.items()
            ],
        )
        cursor.execute(
            """
            INSERT INTO sync_state (key, value)
            VALUES ('workbook_garment_prices_v1', 'applied')
            """
        )


def seed_data(cursor):
    cursor.execute("SELECT seeded FROM seed_meta WHERE id = 1;")
    if cursor.fetchone()[0] != 0:
        print("Database already seeded, skipping seeding.")
        return

    cursor.executemany(
        """
        INSERT OR IGNORE INTO materials (
            name, kg_per_sqm, cost_per_sqm_chf, activity_id
        ) VALUES (?, ?, ?, ?)
        """,
        [
            (
                material_name,
                material["kg_per_sqm"],
                material["cost_per_sqm_chf"],
                material["activity_id"],
            )
            for material_name, material in MATERIAL_SEED_DATA.items()
        ],
    )
    cursor.executemany(
        """
        INSERT OR IGNORE INTO garment_types (name, price_chf)
        VALUES (?, ?)
        """,
        list(GARMENT_PRICE_CHF.items()),
    )

    cursor.executescript(
        """
        INSERT OR IGNORE INTO locations (name) VALUES
        ('St. Gallen'),
        ('Sigmaringen'),
        ('Dornbirn'),
        ('Ravensburg');

        INSERT OR IGNORE INTO fabric_block_types (name, sqm) VALUES
        ('80x64', 0.512),
        ('40x14', 0.056),
        ('20x15', 0.03),
        ('64x40', 0.256),
        ('100x64', 0.64),
        ('100x80', 0.8),
        ('140x14', 0.196),
        ('140x28', 0.392),
        ('160x100', 1.6),
        ('4x48', 0.0192);

        INSERT OR IGNORE INTO process_types (name, unit, activity_id) VALUES
        ('sewing', 'kWh', 6566),
        ('steaming', 'kWh', 6566),
        ('washing', 'kWh', 6566),
        ('dyeing', 'kg', 21893),
        -- Transport of fabric to Cristina. Assumes lorry, >32 metric ton, diesel, EURO 5
        ('transport', 'tkm', 17901);

        INSERT OR IGNORE INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES
        -- Basic Trousers
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), (SELECT id FROM fabric_block_types WHERE name='100x64'), 2),
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), (SELECT id FROM fabric_block_types WHERE name='64x40'), 2),
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), (SELECT id FROM fabric_block_types WHERE name='20x15'), 4),
        -- Full Trousers
        ((SELECT id FROM garment_types WHERE name='Full Trousers'), (SELECT id FROM fabric_block_types WHERE name='100x64'), 2),
        ((SELECT id FROM garment_types WHERE name='Full Trousers'), (SELECT id FROM fabric_block_types WHERE name='64x40'), 4),
        ((SELECT id FROM garment_types WHERE name='Full Trousers'), (SELECT id FROM fabric_block_types WHERE name='20x15'), 4),
        -- Basic Jumpsuit short sleeves
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM fabric_block_types WHERE name='80x64'), 1),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM fabric_block_types WHERE name='100x64'), 2),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM fabric_block_types WHERE name='140x14'), 1),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 4),
        -- Basic Jumpsuit long sleeves
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM fabric_block_types WHERE name='80x64'), 1),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM fabric_block_types WHERE name='100x64'), 2),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM fabric_block_types WHERE name='140x14'), 1),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 4),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM fabric_block_types WHERE name='64x40'), 2),
        -- Elegant cowl neck top
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck top'), (SELECT id FROM fabric_block_types WHERE name='64x40'), 2),
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck top'), (SELECT id FROM fabric_block_types WHERE name='4x48'), 2),
        -- Elegant cowl neck dress
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck dress'), (SELECT id FROM fabric_block_types WHERE name='64x40'), 4),
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck dress'), (SELECT id FROM fabric_block_types WHERE name='4x48'), 2),
        -- Wrap Skirt
        ((SELECT id FROM garment_types WHERE name='Wrap Skirt'), (SELECT id FROM fabric_block_types WHERE name='100x80'), 1),
        ((SELECT id FROM garment_types WHERE name='Wrap Skirt'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 2),
        ((SELECT id FROM garment_types WHERE name='Wrap Skirt'), (SELECT id FROM fabric_block_types WHERE name='140x14'), 1),
        -- Daily dress with pocket
        ((SELECT id FROM garment_types WHERE name='Daily dress with pocket'), (SELECT id FROM fabric_block_types WHERE name='140x28'), 4),
        ((SELECT id FROM garment_types WHERE name='Daily dress with pocket'), (SELECT id FROM fabric_block_types WHERE name='140x14'), 2),
        ((SELECT id FROM garment_types WHERE name='Daily dress with pocket'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 2),
        -- Cocktail fitted dress
        ((SELECT id FROM garment_types WHERE name='Cocktail fitted dress'), (SELECT id FROM fabric_block_types WHERE name='100x80'), 2),
        ((SELECT id FROM garment_types WHERE name='Cocktail fitted dress'), (SELECT id FROM fabric_block_types WHERE name='140x28'), 4),
        -- Long tabard
        ((SELECT id FROM garment_types WHERE name='Long tabard'), (SELECT id FROM fabric_block_types WHERE name='140x28'), 4),
        ((SELECT id FROM garment_types WHERE name='Long tabard'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 1),
        -- Cocoon jacket
        ((SELECT id FROM garment_types WHERE name='Cocoon jacket'), (SELECT id FROM fabric_block_types WHERE name='100x80'), 3),
        ((SELECT id FROM garment_types WHERE name='Cocoon jacket'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 6),
        -- Orka jacket
        ((SELECT id FROM garment_types WHERE name='Orka jacket'), (SELECT id FROM fabric_block_types WHERE name='100x80'), 1),
        -- Nordlys Dress
        ((SELECT id FROM garment_types WHERE name='Nordlys Dress'), (SELECT id FROM fabric_block_types WHERE name='160x100'), 1),
        ((SELECT id FROM garment_types WHERE name='Nordlys Dress'), (SELECT id FROM fabric_block_types WHERE name='100x80'), 1),
        -- Mangata Dress
        ((SELECT id FROM garment_types WHERE name='Mangata Dress'), (SELECT id FROM fabric_block_types WHERE name='160x100'), 1),
        ((SELECT id FROM garment_types WHERE name='Mangata Dress'), (SELECT id FROM fabric_block_types WHERE name='100x80'), 1),
        ((SELECT id FROM garment_types WHERE name='Mangata Dress'), (SELECT id FROM fabric_block_types WHERE name='4x48'), 1),
        -- Måne top
        ((SELECT id FROM garment_types WHERE name='Måne top'), (SELECT id FROM fabric_block_types WHERE name='100x80'), 1),
        ((SELECT id FROM garment_types WHERE name='Måne top'), (SELECT id FROM fabric_block_types WHERE name='4x48'), 2),
        -- Sommar Skirt
        ((SELECT id FROM garment_types WHERE name='Sommar Skirt'), (SELECT id FROM fabric_block_types WHERE name='160x100'), 1),
        -- Basic Unisex Shirt with pocket
        ((SELECT id FROM garment_types WHERE name='Basic Unisex Shirt with pocket'), (SELECT id FROM fabric_block_types WHERE name='80x64'), 1),
        ((SELECT id FROM garment_types WHERE name='Basic Unisex Shirt with pocket'), (SELECT id FROM fabric_block_types WHERE name='64x40'), 4),
        ((SELECT id FROM garment_types WHERE name='Basic Unisex Shirt with pocket'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 3),
        -- Basic Crop Top
        ((SELECT id FROM garment_types WHERE name='Basic Crop Top'), (SELECT id FROM fabric_block_types WHERE name='80x64'), 1),
        ((SELECT id FROM garment_types WHERE name='Basic Crop Top'), (SELECT id FROM fabric_block_types WHERE name='40x14'), 3);

        INSERT OR IGNORE INTO garment_recipe_materials (garment_type, material_id) VALUES
        -- Basic Trousers (Hemp, Cotton)
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), (SELECT id FROM materials WHERE name='hemp')),
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), (SELECT id FROM materials WHERE name='cotton')),
        -- Full Trousers (Hemp, Cotton)
        ((SELECT id FROM garment_types WHERE name='Full Trousers'), (SELECT id FROM materials WHERE name='hemp')),
        ((SELECT id FROM garment_types WHERE name='Full Trousers'), (SELECT id FROM materials WHERE name='cotton')),
        -- Basic Jumpsuit short sleeves (Hemp, Cotton)
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM materials WHERE name='hemp')),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM materials WHERE name='cotton')),
        -- Basic Jumpsuit long sleeves (Hemp, Cotton)
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM materials WHERE name='hemp')),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM materials WHERE name='cotton')),
        -- Elegant cowl neck top (Silk)
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck top'), (SELECT id FROM materials WHERE name='silk')),
        -- Elegant cowl neck dress (Silk)
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck dress'), (SELECT id FROM materials WHERE name='silk')),
        -- Wrap Skirt (Hemp)
        ((SELECT id FROM garment_types WHERE name='Wrap Skirt'), (SELECT id FROM materials WHERE name='hemp')),
        -- Daily dress with pocket (Hemp, Cotton)
        ((SELECT id FROM garment_types WHERE name='Daily dress with pocket'), (SELECT id FROM materials WHERE name='hemp')),
        ((SELECT id FROM garment_types WHERE name='Daily dress with pocket'), (SELECT id FROM materials WHERE name='cotton')),
        -- Cocktail fitted dress (Silk)
        ((SELECT id FROM garment_types WHERE name='Cocktail fitted dress'), (SELECT id FROM materials WHERE name='silk')),
        -- Long tabard (Hemp)
        ((SELECT id FROM garment_types WHERE name='Long tabard'), (SELECT id FROM materials WHERE name='hemp')),
        -- Cocoon jacket (Hemp)
        ((SELECT id FROM garment_types WHERE name='Cocoon jacket'), (SELECT id FROM materials WHERE name='hemp')),
        -- Orka jacket (Cotton)
        ((SELECT id FROM garment_types WHERE name='Orka jacket'), (SELECT id FROM materials WHERE name='cotton')),
        -- Nordlys Dress (Cotton)
        ((SELECT id FROM garment_types WHERE name='Nordlys Dress'), (SELECT id FROM materials WHERE name='cotton')),
        -- Mangata Dress (Cotton)
        ((SELECT id FROM garment_types WHERE name='Mangata Dress'), (SELECT id FROM materials WHERE name='cotton')),
        -- Basic Crop Top (Hemp)
        ((SELECT id FROM garment_types WHERE name='Basic Crop Top'), (SELECT id FROM materials WHERE name='hemp'));
       
        INSERT OR IGNORE INTO garment_recipe_processes (garment_type, process_id, amount) VALUES
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),  -- Assuming 1 hour of sewing with a machine of 42 W
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), (SELECT id FROM process_types WHERE name='steaming'), 0.22), -- Assuming 10 minutes of steaming with a machine of 2200 W
        ((SELECT id FROM garment_types WHERE name='Full Trousers'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Full Trousers'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit short sleeves'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Basic Jumpsuit long sleeves'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck top'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck top'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck dress'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck dress'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Wrap Skirt'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Wrap Skirt'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Daily dress with pocket'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Daily dress with pocket'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Cocktail fitted dress'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Cocktail fitted dress'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Long tabard'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Long tabard'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Cocoon jacket'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Cocoon jacket'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Orka jacket'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Orka jacket'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Nordlys Dress'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Nordlys Dress'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Mangata Dress'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Mangata Dress'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Måne top'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Måne top'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Sommar Skirt'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Sommar Skirt'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Basic Unisex Shirt with pocket'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Basic Unisex Shirt with pocket'), (SELECT id FROM process_types WHERE name='steaming'), 0.22),
        ((SELECT id FROM garment_types WHERE name='Basic Crop Top'), (SELECT id FROM process_types WHERE name='sewing'), 0.042),
        ((SELECT id FROM garment_types WHERE name='Basic Crop Top'), (SELECT id FROM process_types WHERE name='steaming'), 0.22);

        INSERT OR IGNORE INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES
        -- transport to Cristina is calculated: Distance from Istanbul to Roermond to Bucharest: 4570 km / 1000 (because transport emission is per tkm) * weight of the fabric block (kg). This calculation might need to be automated.
        -- ((SELECT id FROM fabric_block_types WHERE name='80x64'), (SELECT id FROM process_types WHERE name='transport'), 0.49),
        ((SELECT id FROM fabric_block_types WHERE name='80x64'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        -- ((SELECT id FROM fabric_block_types WHERE name='40x14'), (SELECT id FROM process_types WHERE name='transport'), 0.054),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='20x15'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        -- ((SELECT id FROM fabric_block_types WHERE name='64x40'), (SELECT id FROM process_types WHERE name='transport'), 0.246),
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='100x64'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='100x80'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='140x14'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='140x28'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='160x100'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01),
        ((SELECT id FROM fabric_block_types WHERE name='4x48'), (SELECT id FROM process_types WHERE name='dyeing'), 0.01);
    """
    )
    cursor.execute("UPDATE seed_meta SET seeded = 1 WHERE id = 1;")


def seed_demo_sales_data(cursor):
    cursor.execute("SELECT COUNT(*) FROM garments_inventory")
    existing_garments = cursor.fetchone()[0]
    if existing_garments > 0:
        return

    cursor.executescript(
        """
        INSERT INTO garments_inventory (type_id, co2eq, price, sold) VALUES
        ((SELECT id FROM garment_types WHERE name='Basic Crop Top'), NULL, 100, 1),
        ((SELECT id FROM garment_types WHERE name='Wrap Skirt'), NULL, 100, 1),
        ((SELECT id FROM garment_types WHERE name='Basic Trousers'), NULL, 100, 1),
        ((SELECT id FROM garment_types WHERE name='Elegant cowl neck top'), NULL, 100, 0);

        INSERT INTO fabric_blocks_inventory (type_id, co2eq, garment_id, location_id, material_id, quality, second_life) VALUES
        -- Basic Crop Top: 80x64 x1, 40x14 x3
        ((SELECT id FROM fabric_block_types WHERE name='80x64'), NULL, 1, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='hemp'), 87, 1),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), NULL, 1, (SELECT id FROM locations WHERE name='Dornbirn'), (SELECT id FROM materials WHERE name='hemp'), 93, 1),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), NULL, 1, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='hemp'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), NULL, 1, (SELECT id FROM locations WHERE name='Sigmaringen'), (SELECT id FROM materials WHERE name='hemp'), 100, 0),
        -- Wrap Skirt: 100x80 x1, 40x14 x2, 140x14 x1
        ((SELECT id FROM fabric_block_types WHERE name='100x80'), NULL, 2, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='hemp'), 89, 1),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), NULL, 2, (SELECT id FROM locations WHERE name='Ravensburg'), (SELECT id FROM materials WHERE name='hemp'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='40x14'), NULL, 2, (SELECT id FROM locations WHERE name='Dornbirn'), (SELECT id FROM materials WHERE name='hemp'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='140x14'), NULL, 2, (SELECT id FROM locations WHERE name='Ravensburg'), (SELECT id FROM materials WHERE name='hemp'), 100, 0),
        -- Basic Trousers: 100x64 x2, 64x40 x2, 20x15 x4
        ((SELECT id FROM fabric_block_types WHERE name='100x64'), NULL, 3, (SELECT id FROM locations WHERE name='Sigmaringen'), (SELECT id FROM materials WHERE name='cotton'), 88, 1),
        ((SELECT id FROM fabric_block_types WHERE name='100x64'), NULL, 3, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='cotton'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), NULL, 3, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='cotton'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), NULL, 3, (SELECT id FROM locations WHERE name='Dornbirn'), (SELECT id FROM materials WHERE name='cotton'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='20x15'), NULL, 3, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='cotton'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='20x15'), NULL, 3, (SELECT id FROM locations WHERE name='Sigmaringen'), (SELECT id FROM materials WHERE name='cotton'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='20x15'), NULL, 3, (SELECT id FROM locations WHERE name='Ravensburg'), (SELECT id FROM materials WHERE name='cotton'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='20x15'), NULL, 3, (SELECT id FROM locations WHERE name='Dornbirn'), (SELECT id FROM materials WHERE name='cotton'), 100, 0),
        -- Elegant cowl neck top: 64x40 x2, 4x48 x2
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), NULL, 4, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='silk'), 86, 1),
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), NULL, 4, (SELECT id FROM locations WHERE name='Ravensburg'), (SELECT id FROM materials WHERE name='silk'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='4x48'), NULL, 4, (SELECT id FROM locations WHERE name='Dornbirn'), (SELECT id FROM materials WHERE name='silk'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='4x48'), NULL, 4, (SELECT id FROM locations WHERE name='Sigmaringen'), (SELECT id FROM materials WHERE name='silk'), 100, 0),
        ((SELECT id FROM fabric_block_types WHERE name='64x40'), NULL, NULL, (SELECT id FROM locations WHERE name='St. Gallen'), (SELECT id FROM materials WHERE name='silk'), 91, 1);
        """
    )


def seed_material_supply_chain(cursor):
    distances = {
        "hemp": HEMP_DISTANCE_TO_MANUFACTURER_KM,
        "cotton": COTTON_DISTANCE_TO_MANUFACTURER_KM,
        "silk": SILK_DISTANCE_TO_MANUFACTURER_KM,
    }
    for material_name, distance_km in distances.items():
        cursor.execute(
            """
            INSERT OR IGNORE INTO material_manufacturer_distances (
                material_id, destination_manufacturer_id, distance_km
            )
            SELECT materials.id, manufacturers.id, ?
            FROM materials CROSS JOIN manufacturers
            WHERE materials.name = ? AND manufacturers.role_group = 'fabric'
            """,
            (distance_km, material_name),
        )


def seed_resource_events(cursor):
    """Seed graph coverage without relying on the legacy dashboard CSV."""
    cursor.execute(
        """
        DELETE FROM resource_events
        WHERE request_type = 'Seed'
          AND manufacturer_distance_id IN (
              SELECT id
              FROM manufacturer_distances
              WHERE source_company = destination_company
          )
        """
    )
    cursor.execute(
        """
        INSERT INTO resource_events (
            event_trigger, timestamp, request_type, resource_type, co2eq, status,
            lifecycle_node, lifecycle_edge, manufacturer_id
        )
        SELECT
            CASE role_group
                WHEN 'fabric' THEN 'Supply'
                WHEN 'garment' THEN 'Production'
                WHEN 'repair' THEN 'Repair'
                ELSE 'Finishing'
            END,
            datetime('now', printf('-%d minutes', id)),
            'Seed', role, NULL, 'Done',
            CASE role_group
                WHEN 'fabric' THEN 'Extraction'
                WHEN 'repair' THEN NULL
                ELSE 'Production'
            END,
            CASE role_group
                WHEN 'repair' THEN 'Repair'
                ELSE NULL
            END,
            id
        FROM manufacturers
        WHERE NOT EXISTS (
            SELECT 1 FROM resource_events re WHERE re.manufacturer_id = manufacturers.id
        )
        ORDER BY id
        """
    )
    for lifecycle_node in ("Extraction", "Production", "Use", "Waste"):
        cursor.execute(
            """
            INSERT INTO resource_events (
                event_trigger, timestamp, request_type, resource_type, status,
                lifecycle_node
            )
            SELECT ?, datetime('now'), 'Seed', 'Lifecycle stage', 'Done', ?
            WHERE NOT EXISTS (
                SELECT 1 FROM resource_events WHERE lifecycle_node = ?
            )
            """,
            (lifecycle_node, lifecycle_node, lifecycle_node),
        )
    for lifecycle_edge in (
        "Supply",
        "Deliver",
        "Release",
        "Repair",
        "Remanufacture",
        "Recycle",
        "Composting",
    ):
        cursor.execute(
            """
            INSERT INTO resource_events (
                event_trigger, timestamp, request_type, resource_type, status,
                lifecycle_edge
            )
            SELECT ?, datetime('now'), 'Seed', 'Lifecycle transition', 'Done', ?
            WHERE NOT EXISTS (
                SELECT 1 FROM resource_events WHERE lifecycle_edge = ?
            )
            """,
            (lifecycle_edge, lifecycle_edge, lifecycle_edge),
        )
    cursor.execute(
        """
        INSERT INTO resource_events (
            event_trigger, timestamp, request_type, resource_type, co2eq, status,
            lifecycle_node, material_id
        )
        SELECT 'Extraction', datetime('now', printf('-%d minutes', 200 + id)),
               'Seed', name, NULL, 'Done', 'Extraction', id
        FROM materials
        WHERE name IN ('hemp', 'cotton', 'silk')
          AND NOT EXISTS (
              SELECT 1 FROM resource_events re WHERE re.material_id = materials.id
          )
        ORDER BY id
        """
    )
    cursor.execute(
        """
        INSERT INTO resource_events (
            event_trigger, timestamp, request_type, resource_type, co2eq, status,
            lifecycle_edge, material_manufacturer_distance_id
        )
        SELECT 'Supply', datetime('now', printf('-%d minutes', 300 + mmd.id)),
               'Seed', 'Material transport', NULL, 'Done', 'Supply', mmd.id
        FROM material_manufacturer_distances mmd
        WHERE NOT EXISTS (
            SELECT 1 FROM resource_events re
            WHERE re.material_manufacturer_distance_id = mmd.id
        )
        ORDER BY mmd.id
        """
    )
    cursor.execute(
        """
        INSERT INTO resource_events (
            event_trigger, timestamp, request_type, resource_type, co2eq, status,
            lifecycle_edge, manufacturer_distance_id
        )
        SELECT
            'Transport',
            datetime('now', printf('-%d minutes', 100 + id)),
            'Seed', 'Transport leg', NULL, 'Done',
            CASE
                WHEN source_role_group = 'fabric' THEN 'Supply'
                ELSE 'Deliver'
            END,
            id
        FROM manufacturer_distances
        WHERE source_company <> destination_company
          AND NOT EXISTS (
            SELECT 1 FROM resource_events re
            WHERE re.manufacturer_distance_id = manufacturer_distances.id
        )
        ORDER BY id
        """
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
