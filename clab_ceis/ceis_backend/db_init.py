import sqlite3

def init_sqlite_db():
    conn = sqlite3.connect('ceis_backend.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS garments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            co2eq INTEGER,
            price INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fabric_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            co2eq INTEGER,
            garment_id INTEGER,
            FOREIGN KEY (garment_id) REFERENCES garments (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS preparations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount INTEGER,
            fabric_block_id INTEGER,
            FOREIGN KEY (fabric_block_id) REFERENCES fabric_blocks (id)
        )
    ''')
    
    conn.commit()
    conn.close()