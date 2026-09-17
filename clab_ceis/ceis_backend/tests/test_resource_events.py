import sqlite3
from unittest.mock import MagicMock

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
from ceis_backend.resource_event_emissions import enrich_resource_events_with_co2
from ceis_backend.wiser_bridge import WiserClientError


def _connect():
    return sqlite3.connect("ceis_backend.db")


def _build_mock_wiser_client(emissions_by_activity: dict[int, float | None]):
    wiser_client = MagicMock()
    wiser_client.get_emission_per_unit.side_effect = emissions_by_activity.get
    return wiser_client


def _build_failing_wiser_client():
    wiser_client = MagicMock()
    wiser_client.get_emission_per_unit.side_effect = WiserClientError("offline")
    return wiser_client


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
    cursor.execute(
        """
        INSERT INTO manufacturer_distances (
            source_company, source_role_group, source_location,
            destination_company, destination_role_group, destination_location,
            distance_km
        ) VALUES ('Fabric Co', 'fabric', 'Fabric town',
                  'Fabric Co', 'fabric', 'Fabric town', 0)
        """
    )
    seed_material_supply_chain(cursor)
    seed_resource_events(cursor)
    conn.commit()

    for target_column, source_table in (
        ("manufacturer_id", "manufacturers"),
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

    cursor.execute(
        """
        SELECT COUNT(*) FROM manufacturer_distances
        WHERE source_company <> destination_company
        """
    )
    non_self_distance_count = cursor.fetchone()[0]
    cursor.execute(
        """
        SELECT COUNT(DISTINCT manufacturer_distance_id)
        FROM resource_events
        WHERE manufacturer_distance_id IS NOT NULL
        """
    )
    assert cursor.fetchone()[0] == non_self_distance_count
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM resource_events re
        JOIN manufacturer_distances md ON md.id = re.manufacturer_distance_id
        WHERE md.source_company = md.destination_company
        """
    )
    assert cursor.fetchone()[0] == 0

    graph = db_get_supply_chain_graph()
    assert len(graph["nodes"]) == 2
    assert len(graph["edges"]) == 1
    assert len(graph["material_nodes"]) == 3
    assert len(graph["material_edges"]) == 3
    conn.close()


def test_supplier_filter_returns_events_to_and_from_supplier(clean_db):
    conn = _connect()
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("Fabric Co", "fabric manufacturer", "fabric", "Fabric town"),
            ("Garment Co", "garment manufacturer", "garment", "Garment town"),
            ("Finisher Co", "finishing", "finishing", "Finish town"),
        ],
    )
    cursor.execute("SELECT id FROM manufacturers WHERE company = 'Garment Co'")
    garment_supplier_id = cursor.fetchone()[0]
    cursor.executemany(
        """
        INSERT INTO manufacturer_distances (
            source_company, source_role_group, source_location,
            destination_company, destination_role_group, destination_location,
            distance_km
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "Fabric Co",
                "fabric",
                "Fabric town",
                "Garment Co",
                "garment",
                "Garment town",
                12.5,
            ),
            (
                "Garment Co",
                "garment",
                "Garment town",
                "Finisher Co",
                "finishing",
                "Finish town",
                20,
            ),
        ],
    )
    seed_resource_events(cursor)
    conn.commit()
    conn.close()

    events = db_get_resource_events(manufacturer_id=garment_supplier_id)
    event_pairs = {(event["from"], event["to"]) for event in events}

    assert all("date" in event and "time" in event for event in events)
    assert ("Fabric Co", "Garment Co") in event_pairs
    assert ("Garment Co", "Finisher Co") in event_pairs
    assert any(
        event["at"] == "Garment Co"
        and event["from"] is None
        and event["to"] is None
        for event in events
    )
    assert ("Fabric Co", "Finisher Co") not in event_pairs


def test_repair_shop_seeds_repair_lifecycle_event(clean_db):
    conn = _connect()
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("Takli Textil", "garment manufacturer / repair", "garment", "A"),
            ("Takli Textil", "repair", "repair", "A"),
            ("Die Manufaktur GmbH", "repair", "repair", "B"),
        ],
    )
    seed_resource_events(cursor)
    conn.commit()
    conn.close()

    events = db_get_resource_events(lifecycle_edge="Repair")
    repair_locations = {event["at"] for event in events}

    assert "Die Manufaktur GmbH" in repair_locations
    assert "Takli Textil" in repair_locations


def test_supply_chain_graph_uses_company_and_role_for_duplicate_suppliers(clean_db):
    conn = _connect()
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("Takli Textil", "garment manufacturer / repair", "garment", "A"),
            ("Takli Textil", "repair", "repair", "A"),
            ("Finisher Co", "finishing", "finishing", "B"),
        ],
    )
    cursor.execute(
        "SELECT id FROM manufacturers WHERE company = 'Takli Textil' AND role_group = 'garment'"
    )
    garment_takli_id = cursor.fetchone()[0]
    cursor.execute(
        "SELECT id FROM manufacturers WHERE company = 'Takli Textil' AND role_group = 'repair'"
    )
    repair_takli_id = cursor.fetchone()[0]
    cursor.execute(
        """
        INSERT INTO manufacturer_distances (
            source_company, source_role_group, source_location,
            destination_company, destination_role_group, destination_location,
            distance_km
        ) VALUES ('Takli Textil', 'garment', 'A',
                  'Finisher Co', 'finishing', 'B', 20)
        """
    )
    conn.commit()
    conn.close()

    graph = db_get_supply_chain_graph()
    takli_edges = [
        edge for edge in graph["edges"] if edge["source_company"] == "Takli Textil"
    ]

    assert takli_edges[0]["source_manufacturer_id"] == garment_takli_id
    assert takli_edges[0]["source_manufacturer_id"] != repair_takli_id


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


def test_resource_event_emissions_calculate_material_and_material_transport(
    clean_db,
):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES ('hemp', 2, 101)"
    )
    material_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES ('Fabric Co', 'fabric manufacturer', 'fabric', 'Fabric town')
        """
    )
    manufacturer_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO material_manufacturer_distances (
            material_id, destination_manufacturer_id, distance_km
        ) VALUES (?, ?, 50)
        """,
        (material_id, manufacturer_id),
    )
    material_distance_id = cursor.lastrowid
    seed_resource_events(cursor)
    conn.commit()
    conn.close()

    events = enrich_resource_events_with_co2(
        db_get_resource_events(),
        _build_mock_wiser_client({101: 3.0, 17901: 0.5}),
    )

    material_event = next(
        event for event in events if event["material_id"] == material_id
    )
    transport_event = next(
        event
        for event in events
        if event["material_manufacturer_distance_id"] == material_distance_id
    )

    assert material_event["co2eq"] == 6.0
    assert material_event["co2eq_calculation_status"] == "calculated"
    assert transport_event["co2eq"] == 0.05
    assert transport_event["co2eq_calculation_status"] == "calculated"


def test_resource_event_emissions_require_wiser_factor_when_wiser_is_unavailable(
    clean_db,
):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO materials (name, kg_per_sqm, activity_id)
        VALUES ('hemp', 0.21, 276186)
        """
    )
    material_id = cursor.lastrowid
    seed_resource_events(cursor)
    conn.commit()
    conn.close()

    events = enrich_resource_events_with_co2(
        db_get_resource_events(),
        _build_failing_wiser_client(),
    )
    material_event = next(
        event for event in events if event["material_id"] == material_id
    )

    assert material_event["co2eq"] is None
    assert material_event["co2eq_calculation_status"] == "missing_factor"

    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT co2eq FROM resource_events WHERE material_id = ?",
        (material_id,),
    )
    assert cursor.fetchone()[0] is None
    conn.close()


def test_resource_event_emissions_calculate_production_order_from_recipe(clean_db):
    conn = _connect()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO garment_types (name, price_chf) VALUES ('Test shirt', 100)"
    )
    garment_type_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES ('hemp', 0.5, 101)"
    )
    material_id = cursor.lastrowid
    cursor.execute("INSERT INTO fabric_block_types (name, sqm) VALUES ('block', 2)")
    fabric_block_type_id = cursor.lastrowid
    cursor.execute(
        "INSERT INTO process_types (name, unit, activity_id) VALUES ('sewing', 'kWh', 102)"
    )
    process_id = cursor.lastrowid
    cursor.execute(
        """
        INSERT INTO garment_recipe_fabric_blocks
            (garment_type, fabric_block_id, amount)
        VALUES (?, ?, 1)
        """,
        (garment_type_id, fabric_block_type_id),
    )
    cursor.execute(
        """
        INSERT INTO garment_recipe_materials (garment_type, material_id)
        VALUES (?, ?)
        """,
        (garment_type_id, material_id),
    )
    cursor.execute(
        """
        INSERT INTO garment_recipe_processes (garment_type, process_id, amount)
        VALUES (?, ?, 2)
        """,
        (garment_type_id, process_id),
    )
    cursor.execute(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES ('Maker', 'garment manufacturer', 'garment', 'A')
        """
    )
    conn.commit()
    conn.close()

    db_create_order(garment_type_id, material_id)

    events = enrich_resource_events_with_co2(
        db_get_resource_events(),
        _build_mock_wiser_client({101: 10.0, 102: 1.0, 17901: 0.0}),
    )
    order_event = next(event for event in events if event["order_id"] is not None)

    assert order_event["event_trigger"] == "Production"
    assert order_event["co2eq"] == 12.0
    assert order_event["co2eq_calculation_status"] == "calculated"
