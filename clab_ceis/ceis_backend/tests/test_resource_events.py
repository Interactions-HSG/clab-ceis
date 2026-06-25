import sqlite3

import pytest

from ceis_backend.db_init import (
    create_tables,
    seed_material_supply_chain,
    seed_resource_events,
)
from ceis_backend.queries import (
    db_create_order,
    db_get_resource_events,
    db_get_supply_chain_graph,
)


def _connect():
    return sqlite3.connect("ceis_backend.db")


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    conn = _connect()
    create_tables(conn.cursor())
    conn.commit()
    conn.close()


def test_seeded_events_cover_every_supply_chain_node_and_edge(clean_db):
    conn = _connect()
    cursor = conn.cursor()
    cursor.executemany(
        "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES (?, 1, 1)",
        [("hemp",), ("cotton",), ("silk",)],
    )
    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("Fabric Co", "fabric manufacturer", "fabric", "Fabric town"),
            ("Garment Co", "garment manufacturer", "garment", "Garment town"),
        ],
    )
    cursor.execute(
        """
        INSERT INTO manufacturer_distances (
            source_company, source_role_group, source_location,
            destination_company, destination_role_group, destination_location,
            distance_km
        ) VALUES ('Fabric Co', 'fabric', 'Fabric town',
                  'Garment Co', 'garment', 'Garment town', 12.5)
        """
    )
    seed_material_supply_chain(cursor)
    seed_resource_events(cursor)
    conn.commit()

    for target_column, source_table in (
        ("manufacturer_id", "manufacturers"),
        ("manufacturer_distance_id", "manufacturer_distances"),
        ("material_id", "materials"),
        ("material_manufacturer_distance_id", "material_manufacturer_distances"),
    ):
        cursor.execute(f"SELECT COUNT(*) FROM {source_table}")
        source_count = cursor.fetchone()[0]
        cursor.execute(
            f"SELECT COUNT(DISTINCT {target_column}) FROM resource_events "
            f"WHERE {target_column} IS NOT NULL"
        )
        assert cursor.fetchone()[0] == source_count

    graph = db_get_supply_chain_graph()
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert len(graph["material_nodes"]) == 3
    assert len(graph["material_edges"]) == 3
    conn.close()


def test_order_delivers_stock_then_requests_production(clean_db):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO garment_types (name, price_chf) VALUES ('Test coat', 100)"
    )
    garment_type_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES ('test wool', 1, 1)"
    )
    material_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
        (garment_type_id, material_id),
    )
    cursor.execute(
        "INSERT INTO garments_inventory (type_id, co2eq, price, sold) VALUES (?, 4.2, 100, 0)",
        (garment_type_id,),
    )
    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("Maker", "garment manufacturer", "garment", "A"),
            ("Finisher", "finishing", "finishing", "B"),
        ],
    )
    cursor.execute(
        """
        INSERT INTO manufacturer_distances (
            source_company, source_role_group, source_location,
            destination_company, destination_role_group, destination_location,
            distance_km
        ) VALUES ('Maker', 'garment', 'A', 'Finisher', 'finishing', 'B', 20)
        """
    )
    conn.commit()
    conn.close()

    stock_order = db_create_order(garment_type_id, material_id)
    production_order = db_create_order(garment_type_id, material_id)

    assert stock_order["event_trigger"] == "Deliver"
    assert stock_order["fulfillment_type"] == "stock"
    assert production_order["event_trigger"] == "Production"
    assert production_order["fulfillment_type"] == "production"

    events = db_get_resource_events()
    order_events = [event for event in events if event["order_id"] is not None]
    assert {event["event_trigger"] for event in order_events} == {
        "Deliver",
        "Production",
    }
