import sqlite3


def init_sqlite_db():
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    # recipes tables
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
        CREATE TABLE IF NOT EXISTS fabric_block_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            material TEXT,
            amount_kg INTEGER,
            activity_id INTEGER NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS process_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resource_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT,
            activity_id INTEGER NOT NULL
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS process_resource_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (process_id) REFERENCES process_types(id),
            FOREIGN KEY (resource_id) REFERENCES resource_types(id),
            UNIQUE(process_id, resource_id)
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
        CREATE TABLE IF NOT EXISTS garment_recipe_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            garment_type INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            time INTEGER,
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
            time INTEGER,
            FOREIGN KEY (fabric_block_type) REFERENCES fabric_block_types(id) ON DELETE CASCADE,
            FOREIGN KEY (process_id) REFERENCES process_types(id) ON DELETE CASCADE
        )
    """
    )

    # inventory tables
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
            FOREIGN KEY (type_id) REFERENCES fabric_block_types (id) ON DELETE CASCADE,
            FOREIGN KEY (garment_id) REFERENCES garments_inventory (id) ON DELETE CASCADE
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_id INTEGER NOT NULL,
            amount INTEGER,
            fabric_block_id INTEGER,
            FOREIGN KEY (type_id) REFERENCES process_types (id) ON DELETE CASCADE,
            FOREIGN KEY (fabric_block_id) REFERENCES fabric_blocks_inventory (id) ON DELETE CASCADE
        )
    """
    )

    # seeding
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS seed_meta (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            seeded INTEGER NOT NULL
        );
        INSERT OR IGNORE INTO seed_meta (id, seeded) VALUES (1, 0);
    """
    )

    cursor.execute("SELECT seeded FROM seed_meta WHERE id = 1;")
    if cursor.fetchone()[0] == 0:
        cursor.executescript(
            """
            INSERT OR IGNORE INTO garment_types (name) VALUES
            ('Crop Top'),
            ('Skirt');

            INSERT OR IGNORE INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES
            ('FB1', 'cotton', 1.5, 3878),
            ('FB2', 'polyester', 1.2, 5544);

            INSERT OR IGNORE INTO process_types (name) VALUES
            ('sewing'),
            ('washing'),
            ('dyeing');

            INSERT OR IGNORE INTO resource_types (name, unit, activity_id) VALUES
            ('electricity', 'kWh', 6566),
            ('water', 'L', 20642);

            INSERT OR IGNORE INTO process_resource_consumption (process_id, resource_id, amount) VALUES
            ((SELECT id FROM process_types WHERE name='sewing'),
             (SELECT id FROM resource_types WHERE name='electricity'), 1.0),
            ((SELECT id FROM process_types WHERE name='washing'),
             (SELECT id FROM resource_types WHERE name='water'), 5.0),
            ((SELECT id FROM process_types WHERE name='washing'),
             (SELECT id FROM resource_types WHERE name='electricity'), 2.0),
            ((SELECT id FROM process_types WHERE name='dyeing'),
             (SELECT id FROM resource_types WHERE name='water'), 10.0);

            INSERT OR IGNORE INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES
            ((SELECT id FROM garment_types WHERE name='Crop Top'), (SELECT id FROM fabric_block_types WHERE name='FB1'), 2),
            ((SELECT id FROM garment_types WHERE name='Crop Top'), (SELECT id FROM fabric_block_types WHERE name='FB2'), 1),
            ((SELECT id FROM garment_types WHERE name='Skirt'), (SELECT id FROM fabric_block_types WHERE name='FB1'), 1),
            ((SELECT id FROM garment_types WHERE name='Skirt'), (SELECT id FROM fabric_block_types WHERE name='FB2'), 2);

            INSERT OR IGNORE INTO garment_recipe_processes (garment_type, process_id, time) VALUES
            ((SELECT id FROM garment_types WHERE name='Crop Top'), (SELECT id FROM process_types WHERE name='sewing'), 1),
            ((SELECT id FROM garment_types WHERE name='Crop Top'), (SELECT id FROM process_types WHERE name='washing'), 3),
            ((SELECT id FROM garment_types WHERE name='Skirt'), (SELECT id FROM process_types WHERE name='sewing'), 1),
            ((SELECT id FROM garment_types WHERE name='Skirt'), (SELECT id FROM process_types WHERE name='dyeing'), 2);

            INSERT OR IGNORE INTO fabric_block_recipe_processes (fabric_block_type, process_id, time) VALUES
            ((SELECT id FROM fabric_block_types WHERE name='FB1'), (SELECT id FROM process_types WHERE name='dyeing'), 2),
            ((SELECT id FROM fabric_block_types WHERE name='FB2'), (SELECT id FROM process_types WHERE name='washing'), 1);
        """
        )
        cursor.execute("UPDATE seed_meta SET seeded = 1 WHERE id = 1;")
    else:
        print("Database already seeded, skipping seeding.")

    conn.commit()
    conn.close()
