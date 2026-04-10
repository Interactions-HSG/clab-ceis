import sqlite3
from unittest.mock import MagicMock

import pytest

from ceis_backend.db_init import init_sqlite_db, create_tables
from ceis_backend.utils import get_co2_for_garment, get_co2_for_sold_garment
from ceis_backend.queries import get_fabric_block_recipe, get_used_fabric_block
from ceis_backend.models import Process
from ceis_backend.main import delete_fabric_block_type
from fastapi.testclient import TestClient
from ceis_backend.main import app


@pytest.fixture
def test_db(tmp_path, monkeypatch):
    """Create a temporary test database."""
    db_path = tmp_path / "test_ceis_backend.db"
    monkeypatch.chdir(tmp_path)

    # Initialize the database
    init_sqlite_db()

    yield str(db_path)


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Create a clean database without seeding for isolated tests."""
    db_path = tmp_path / "ceis_backend.db"
    monkeypatch.chdir(tmp_path)

    # Create tables without seeding
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_tables(cursor)
    conn.commit()
    conn.close()

    yield str(db_path)


def _build_mock_wiser_client(
    emissions_by_activity: dict[int, float | None],
) -> MagicMock:
    wiser_client = MagicMock()
    wiser_client.get_emission_per_unit.side_effect = emissions_by_activity.get
    return wiser_client


class TestFabricBlockRecipeProcessesTableCreation:
    """Test case 1: fabric_block_recipe_processes table is created correctly."""

    def test_table_exists_after_init(self, test_db):
        """Verify the fabric_block_recipe_processes table exists after initialization."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='fabric_block_recipe_processes'
        """
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "fabric_block_recipe_processes"

    def test_table_has_correct_columns(self, test_db):
        """Verify the table has the expected columns."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(fabric_block_recipe_processes)")
        columns = cursor.fetchall()
        conn.close()

        column_names = [col[1] for col in columns]

        assert "id" in column_names
        assert "fabric_block_type" in column_names
        assert "process_id" in column_names
        assert "amount" in column_names

    def test_table_seeded_with_data(self, test_db):
        """Verify the table is seeded with initial data."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM fabric_block_recipe_processes")
        count = cursor.fetchone()[0]
        conn.close()

        assert count > 0


class TestInventoryProcessTables:
    def test_inventory_process_tables_exist_after_init(self, test_db):
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name IN ('processes_fabric_blocks_inventory', 'processes_garments_inventory')
            ORDER BY name
            """
        )
        result = [row[0] for row in cursor.fetchall()]
        conn.close()

        assert result == [
            "processes_fabric_blocks_inventory",
            "processes_garments_inventory",
        ]

    def test_garments_inventory_has_sold_column_after_init(self, test_db):
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(garments_inventory)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "sold" in columns

    def test_fabric_blocks_inventory_has_second_life_column_after_init(self, test_db):
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(fabric_blocks_inventory)")
        columns = {row[1] for row in cursor.fetchall()}
        conn.close()

        assert "second_life" in columns


class TestStrategistProgress:
    def test_strategy_progress_endpoint_returns_seeded_data(self, test_db):
        with TestClient(app) as client:
            client.app.state.wiser_client = _build_mock_wiser_client(
                {
                    276186: 5.0,
                    6756: 4.0,
                    6566: 0.5,
                    17901: 0.1,
                }
            )

            response = client.get("/strategy-progress")

            assert response.status_code == 200
            payload = response.json()
            assert payload["thresholds"]["circularity_pct"] == 30.0
            assert payload["aggregates"]["sold_garments"] >= 3
            assert payload["aggregates"]["circularity_pct"] > 0
            assert payload["aggregates"]["fabric_saved_pct"] > 0
            assert payload["aggregates"]["environmental_cost_co2eq"] > 0
            assert payload["aggregates"]["second_life_fabric_blocks_sold"] == 4
            assert len(payload["sold_garments"]) >= 3

        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM garments_inventory WHERE sold = 1 AND co2eq IS NOT NULL"
        )
        persisted_count = cursor.fetchone()[0]
        conn.close()
        assert persisted_count >= 3

    def test_strategy_progress_does_not_recalculate_existing_co2(self, test_db):
        with TestClient(app) as client:
            client.app.state.wiser_client = _build_mock_wiser_client(
                {
                    276186: 5.0,
                    6756: 4.0,
                    6566: 0.5,
                    17901: 0.1,
                    21893: 0.2,
                }
            )
            first_response = client.get("/strategy-progress")
            assert first_response.status_code == 200

            def _fail_if_called(_activity_id):
                raise AssertionError("CO2 should not be recalculated once persisted")

            failing_wiser_client = MagicMock()
            failing_wiser_client.get_emission_per_unit.side_effect = _fail_if_called
            client.app.state.wiser_client = failing_wiser_client

            second_response = client.get("/strategy-progress")
            assert second_response.status_code == 200

    def test_sold_garment_co2_includes_recipe_and_inventory_processes(self, clean_db):
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute("INSERT INTO locations (name) VALUES ('St. Gallen')")
        location_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 2.0, 1001),
        )
        material_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES (?, ?)",
            ("Sold Garment Test", 100),
        )
        garment_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("Sold Block Test", 1.5),
        )
        fabric_block_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("block-recipe-process", "kg", 2001),
        )
        block_recipe_process_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("block-inventory-process", "kg", 2002),
        )
        block_inventory_process_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("garment-recipe-process", "kg", 2003),
        )
        garment_recipe_process_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("garment-inventory-process", "kg", 2004),
        )
        garment_inventory_process_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_type_id, material_id),
        )
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_type_id, fabric_block_type_id, 1),
        )
        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES (?, ?, ?)",
            (fabric_block_type_id, block_recipe_process_id, 3),
        )
        cursor.execute(
            "INSERT INTO garment_recipe_processes (garment_type, process_id, amount) VALUES (?, ?, ?)",
            (garment_type_id, garment_recipe_process_id, 2),
        )
        cursor.execute(
            "INSERT INTO garments_inventory (type_id, co2eq, price, sold) VALUES (?, ?, ?, ?)",
            (garment_type_id, None, 100, 1),
        )
        garment_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO fabric_blocks_inventory (type_id, co2eq, garment_id, location_id, material_id, quality, second_life)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fabric_block_type_id, None, garment_id, location_id, material_id, 100, 1),
        )
        inventory_fabric_block_id = cursor.lastrowid
        cursor.execute(
            """
            INSERT INTO processes_fabric_blocks_inventory (process_id, amount, fabric_block_id)
            VALUES (?, ?, ?)
            """,
            (block_inventory_process_id, 4, inventory_fabric_block_id),
        )
        cursor.execute(
            """
            INSERT INTO processes_garments_inventory (process_id, amount, garment_id)
            VALUES (?, ?, ?)
            """,
            (garment_inventory_process_id, 1, garment_id),
        )
        conn.commit()
        conn.close()

        wiser_client = _build_mock_wiser_client(
            {
                1001: 10.0,
                2001: 2.0,
                2002: 5.0,
                2003: 7.0,
                2004: 11.0,
                7309: 0.0,
            }
        )

        result = get_co2_for_sold_garment(garment_id, garment_type_id, wiser_client)

        expected_block_emission = (3 * 2.0) + (4 * 5.0)
        expected_garment_process_emission = (2 * 7.0) + (1 * 11.0)

        assert result.fabric_blocks.total_emission == expected_block_emission
        assert result.processes.total_emission == expected_garment_process_emission
        assert result.fabric_blocks.details[0]["material_emission"] == 0
        assert result.fabric_blocks.details[0]["production_emission"] == 6.0
        assert result.fabric_blocks.details[0]["inventory_process_emission"] == 20.0
        assert len(result.processes.details) == 2


class TestGetRecipeForFabricBlock:
    """Test cases 2 & 3: get_fabric_block_recipe function."""

    def test_returns_processes_for_existing_fabric_block(self, test_db):
        """Test case 2: Returns associated processes for a given fabric block."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("hemp",))
        material_id = cursor.fetchone()[0]
        conn.close()

        fabric_block = get_fabric_block_recipe("80x64", material_id)

        assert fabric_block is not None
        assert fabric_block.material == "hemp"
        assert fabric_block.activity_id == 276186
        assert len(fabric_block.processes) > 0
        assert all(isinstance(p, Process) for p in fabric_block.processes)

        # Verify 80x64 has the 'dyeing' process from seeded data
        process_names = [p.name for p in fabric_block.processes]
        assert "dyeing" in process_names


class TestUsedFabricBlockSelection:
    def test_prioritizes_same_material_for_alternative(self, clean_db):
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("PriorityBlock", 1.0),
        )
        fabric_block_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 1.0, 1001),
        )
        cotton_material_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("hemp", 1.0, 1002),
        )
        hemp_material_id = cursor.lastrowid

        # Insert non-matching material first to prove ordering prioritizes preferred material.
        cursor.execute(
            """
            INSERT INTO fabric_blocks_inventory (type_id, co2eq, garment_id, location_id, material_id, quality)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (fabric_block_type_id, None, None, None, cotton_material_id, 90),
        )
        cursor.execute(
            """
            INSERT INTO fabric_blocks_inventory (type_id, co2eq, garment_id, location_id, material_id, quality)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (fabric_block_type_id, None, None, None, hemp_material_id, 85),
        )
        conn.commit()
        conn.close()

        selected = get_used_fabric_block(
            "PriorityBlock", already_used_ids=[], preferred_material="hemp"
        )

        assert selected is not None
        assert selected.material == "hemp"

    def test_returns_correct_process_details(self, test_db):
        """Verify process details match seeded data."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("hemp",))
        material_id = cursor.fetchone()[0]
        conn.close()

        fabric_block = get_fabric_block_recipe("80x64", material_id)
        assert fabric_block is not None

        dyeing_process = next(
            (p for p in fabric_block.processes if p.name == "dyeing"), None
        )
        assert dyeing_process is not None
        assert dyeing_process.amount == 0.01

    def test_excludes_blocks_already_assigned_to_a_garment(self, clean_db):
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("AssignedBlock", 1.0),
        )
        fabric_block_type_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 1.0, 1001),
        )
        material_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES (?, ?)",
            ("Assigned Garment", 100),
        )
        garment_type_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO garments_inventory (type_id, price, sold) VALUES (?, ?, ?)",
            (garment_type_id, 100, 0),
        )
        garment_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO fabric_blocks_inventory (type_id, co2eq, garment_id, location_id, material_id, quality, second_life)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fabric_block_type_id, None, garment_id, None, material_id, 100, 1),
        )
        cursor.execute(
            """
            INSERT INTO fabric_blocks_inventory (type_id, co2eq, garment_id, location_id, material_id, quality, second_life)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (fabric_block_type_id, None, None, None, material_id, 100, 1),
        )
        unassigned_block_id = cursor.lastrowid
        conn.commit()
        conn.close()

        selected = get_used_fabric_block(
            "AssignedBlock", already_used_ids=[], preferred_material="cotton"
        )

        assert selected is not None
        assert selected.id == unassigned_block_id

    def test_returns_empty_list_for_nonexistent_fabric_block(self, test_db):
        """Test case 3: Returns None for non-existent fabric block."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("hemp",))
        material_id = cursor.fetchone()[0]
        conn.close()

        fabric_block = get_fabric_block_recipe("NonExistent", material_id)

        assert fabric_block is None

    def test_returns_processes_for_fb2(self, test_db):
        """Verify 40x14 returns its associated dyeing process."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("hemp",))
        material_id = cursor.fetchone()[0]
        conn.close()

        fabric_block = get_fabric_block_recipe("40x14", material_id)
        assert fabric_block is not None

        assert fabric_block.material == "hemp"
        assert fabric_block.activity_id == 276186

        process_names = [p.name for p in fabric_block.processes]
        assert "dyeing" in process_names


class TestDeleteFabricBlockType:
    """Test case 4: delete_fabric_block_type removes entries from fabric_block_recipe_processes."""

    def test_delete_removes_recipe_processes(self, clean_db):
        """Verify deleting a fabric block type removes its recipe processes."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Insert test data
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("TestFB", 2.0),
        )
        fb_type_id = cursor.lastrowid
        assert fb_type_id is not None

        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("test_process", "kWh", 1234),
        )
        process_id = cursor.lastrowid

        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES (?, ?, ?)",
            (fb_type_id, process_id, 5),
        )
        conn.commit()

        # Verify data exists
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,),
        )
        assert cursor.fetchone()[0] == 1

        conn.close()

        delete_fabric_block_type(fb_type_id)

        # Verify recipe processes are deleted
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,),
        )
        assert cursor.fetchone()[0] == 0

        # Verify fabric block type is deleted
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_types WHERE id = ?", (fb_type_id,)
        )
        assert cursor.fetchone()[0] == 0

        conn.close()

    def test_delete_removes_multiple_recipe_processes(self, clean_db):
        """Verify deleting removes all associated recipe processes."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("MultiFB", 1.0),
        )
        fb_type_id = cursor.lastrowid
        assert fb_type_id is not None

        # Insert multiple processes
        for i, proc_name in enumerate(["cutting", "stitching", "finishing"]):
            cursor.execute(
                "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
                (proc_name, "kWh", 5000 + i),
            )
            process_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES (?, ?, ?)",
                (fb_type_id, process_id, i + 1),
            )
        conn.commit()

        # Verify 3 recipe processes exist
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,),
        )
        assert cursor.fetchone()[0] == 3

        conn.close()

        delete_fabric_block_type(fb_type_id)

        # Verify all recipe processes are deleted
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,),
        )
        assert cursor.fetchone()[0] == 0
        conn.close()


class TestCreateFabricBlockTypeWithProcesses:
    def test_creates_recipe_process_links(self, clean_db):
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("test_process", "kWh", 4321),
        )
        process_id = cursor.lastrowid
        conn.commit()
        conn.close()

        client = TestClient(app)
        response = client.post(
            "/fabric-block-types",
            json={
                "name": "LinkedFB",
                "sqm": 1.5,
                "processes": [{"process_id": process_id, "amount": 2.5}],
            },
        )

        assert response.status_code == 200
        created_id = response.json()["id"]

        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT process_id, amount
            FROM fabric_block_recipe_processes
            WHERE fabric_block_type = ?
            """,
            (created_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        assert rows == [(process_id, 2.5)]

    def test_rejects_invalid_process_type(self, clean_db):
        client = TestClient(app)
        response = client.post(
            "/fabric-block-types",
            json={
                "name": "BadFB",
                "sqm": 1.0,
                "processes": [{"process_id": 999999, "amount": 1.0}],
            },
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid process type"


class TestGetLocationsEndpoint:
    """Test case: GET /locations endpoint returns correct list of locations."""

    def test_returns_all_locations(self, test_db):
        """Verify GET /locations returns all seeded locations."""

        client = TestClient(app)
        response = client.get("/locations")

        assert response.status_code == 200
        locations = response.json()

        # Check we get the 4 seeded locations
        assert len(locations) == 4

        location_names = [loc["name"] for loc in locations]
        assert "St. Gallen" in location_names
        assert "Sigmaringen" in location_names
        assert "Dornbirn" in location_names
        assert "Ravensburg" in location_names

    def test_returns_id_and_name_for_each_location(self, test_db):
        """Verify each location has id and name fields."""

        client = TestClient(app)
        response = client.get("/locations")

        locations = response.json()
        for loc in locations:
            assert "id" in loc
            assert "name" in loc
            assert isinstance(loc["id"], int)
            assert isinstance(loc["name"], str)

    def test_returns_empty_list_when_no_locations(self, clean_db):
        """Verify returns empty list when no locations in database."""

        # Add locations table to clean_db
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """
        )
        conn.commit()
        conn.close()

        client = TestClient(app)
        response = client.get("/locations")

        assert response.status_code == 200
        assert response.json() == []


class TestGetGarmentRecipeFabricBlocksEndpoint:
    def test_returns_fabric_blocks_for_existing_garment(self, test_db):
        client = TestClient(app)

        response = client.get("/garment-types/1/fabric-blocks")

        assert response.status_code == 200
        payload = response.json()
        assert isinstance(payload, list)
        assert len(payload) > 0
        assert "fabric_block" in payload[0]
        assert "amount" in payload[0]

    def test_returns_empty_list_for_unknown_garment(self, test_db):
        client = TestClient(app)

        response = client.get("/garment-types/999999/fabric-blocks")

        assert response.status_code == 200
        assert response.json() == []


class TestCreateFabricBlockWithLocation:
    """Test case: create_fabric_block stores fabric block with location_id."""

    def test_creates_fabric_block_with_location_id(self, test_db):
        """Verify fabric block is stored with the specified location_id."""

        client = TestClient(app)

        # Get a valid fabric block type id and location id
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM fabric_block_types LIMIT 1")
        fb_type_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM locations WHERE name = 'St. Gallen'")
        location_id = cursor.fetchone()[0]
        conn.close()

        # Create fabric block with location_id
        response = client.post(
            "/fabric-blocks",
            json={"type_id": fb_type_id, "processes": [], "location_id": location_id},
        )

        assert response.status_code == 200
        result = response.json()
        assert "id" in result

        # Verify location_id is stored in database
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT location_id FROM fabric_blocks_inventory WHERE id = ?",
            (result["id"],),
        )
        stored_location_id = cursor.fetchone()[0]
        conn.close()

        assert stored_location_id == location_id

    def test_creates_fabric_block_without_location_id(self, test_db):
        """Verify fabric block can be created without location_id (NULL)."""

        client = TestClient(app)

        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM fabric_block_types LIMIT 1")
        fb_type_id = cursor.fetchone()[0]
        conn.close()

        response = client.post(
            "/fabric-blocks", json={"type_id": fb_type_id, "processes": []}
        )

        assert response.status_code == 200
        result = response.json()

        # Verify location_id is NULL
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT location_id FROM fabric_blocks_inventory WHERE id = ?",
            (result["id"],),
        )
        stored_location_id = cursor.fetchone()[0]
        conn.close()

        assert stored_location_id is None


class TestGetFabricBlocksWithLocation:
    """Test case: get_fabric_blocks returns location_name for fabric blocks."""

    def test_returns_location_name_for_fabric_block(self, test_db):
        """Verify get_fabric_blocks returns location_name when location_id is set."""

        client = TestClient(app)

        # Create a fabric block with location
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM fabric_block_types LIMIT 1")
        fb_type_id = cursor.fetchone()[0]
        cursor.execute("SELECT id FROM locations WHERE name = 'Dornbirn'")
        location_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, ?)",
            (fb_type_id, location_id),
        )
        conn.commit()
        conn.close()

        response = client.get("/fabric-blocks")

        assert response.status_code == 200
        fabric_blocks = response.json()

        # Find the block with Dornbirn location
        block_with_location = next(
            (fb for fb in fabric_blocks if fb.get("location") == "Dornbirn"), None
        )
        assert block_with_location is not None
        assert block_with_location["location"] == "Dornbirn"

    def test_returns_null_location_for_fabric_block_without_location(self, test_db):
        """Verify get_fabric_blocks returns null location when location_id is not set."""

        client = TestClient(app)

        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM fabric_block_types LIMIT 1")
        fb_type_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, NULL)",
            (fb_type_id,),
        )
        fb_id = cursor.lastrowid
        conn.commit()
        conn.close()

        response = client.get("/fabric-blocks")

        assert response.status_code == 200
        fabric_blocks = response.json()

        # Find the block we just created
        block_without_location = next(
            (fb for fb in fabric_blocks if fb["id"] == fb_id), None
        )
        assert block_without_location is not None
        assert block_without_location["location"] is None


class TestGetCo2TransportEmissions:
    """Test case: get_co2 calculates transport_emission based on location."""

    @pytest.fixture
    def setup_transport_test_db(self, clean_db):
        """Set up database with test data for transport emission calculation."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Create additional tables
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
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                amount REAL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processes_fabric_blocks_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
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

        # Add location_id column to fabric_blocks_inventory if not exists
        cursor.execute("PRAGMA table_info(fabric_blocks_inventory)")
        columns = [col[1] for col in cursor.fetchall()]
        if "location_id" not in columns:
            cursor.execute(
                "ALTER TABLE fabric_blocks_inventory ADD COLUMN location_id INTEGER"
            )

        # Insert locations
        cursor.execute("INSERT INTO locations (name) VALUES ('St. Gallen')")
        st_gallen_id = cursor.lastrowid
        cursor.execute("INSERT INTO locations (name) VALUES ('Sigmaringen')")
        sigmaringen_id = cursor.lastrowid

        # Insert garment type
        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES ('TransportTestGarment', 0)"
        )
        garment_id = cursor.lastrowid

        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("TransportTestBlock", 2.0),
        )
        fb_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 1.0, 8001),
        )
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("cotton",))
        material_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_id, material_id),
        )

        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1),
        )

        # Insert fabric block in inventory with St. Gallen location
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, ?)",
            (fb_type_id, st_gallen_id),
        )

        conn.commit()
        conn.close()

        return {
            "garment_id": garment_id,
            "fb_type_id": fb_type_id,
            "material_id": material_id,
            "st_gallen_id": st_gallen_id,
            "sigmaringen_id": sigmaringen_id,
        }

    def test_transport_emission_calculated_for_known_location(
        self, setup_transport_test_db
    ):
        """Verify transport_emission is calculated based on location distance and API response."""
        test_data = setup_transport_test_db

        wiser_client = _build_mock_wiser_client({8001: 5.0, 7309: 0.1})
        result = get_co2_for_garment(
            test_data["garment_id"], wiser_client, test_data["material_id"]
        )

        # Check transport emission is calculated
        # St. Gallen distance = 10 km, amount_kg = 2.0
        # transport_emission = emission_per_unit / 1000 * distance * amount
        # = 0.1 / 1000 * 10 * 2.0 = 0.002
        fb_details = result.fabric_blocks.details[0]
        alternative = fb_details.get("alternative", {})

        assert "transport_emission" in alternative
        assert alternative["quality"] == pytest.approx(100.0)
        expected_transport = 0.1 / 1000 * 10 * 2.0  # 0.002
        assert alternative["transport_emission"] == pytest.approx(expected_transport)

    def test_transport_emission_zero_for_no_location(self, clean_db):
        """Verify transport_emission is zero when fabric block has no location."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Create tables
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
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                amount REAL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processes_fabric_blocks_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
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

        # Add location_id column
        cursor.execute("PRAGMA table_info(fabric_blocks_inventory)")
        columns = [col[1] for col in cursor.fetchall()]
        if "location_id" not in columns:
            cursor.execute(
                "ALTER TABLE fabric_blocks_inventory ADD COLUMN location_id INTEGER"
            )

        # Insert garment type
        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES ('NoLocationGarment', 0)"
        )
        garment_id = cursor.lastrowid

        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("NoLocationBlock", 1.5),
        )
        fb_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 1.0, 9001),
        )
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("cotton",))
        material_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_id, material_id),
        )

        # Link fabric block to garment
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1),
        )

        # Insert fabric block WITHOUT location_id
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, NULL)",
            (fb_type_id,),
        )

        conn.commit()
        conn.close()

        wiser_client = _build_mock_wiser_client({9001: 5.0})
        assert garment_id is not None
        result = get_co2_for_garment(int(garment_id), wiser_client, material_id)

        fb_details = result.fabric_blocks.details[0]
        alternative = fb_details.get("alternative", {})

        # Transport emission should be 0 when no location
        assert alternative.get("transport_emission", 0) == 0

    def test_transport_emission_zero_for_unknown_location(self, clean_db):
        """Verify transport_emission is zero when location is not in distances_to_manufacturer."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Create tables
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
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                amount REAL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processes_fabric_blocks_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
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

        # Add location_id column
        cursor.execute("PRAGMA table_info(fabric_blocks_inventory)")
        columns = [col[1] for col in cursor.fetchall()]
        if "location_id" not in columns:
            cursor.execute(
                "ALTER TABLE fabric_blocks_inventory ADD COLUMN location_id INTEGER"
            )

        # Insert an unknown location (not in distances_to_manufacturer)
        cursor.execute("INSERT INTO locations (name) VALUES ('Unknown City')")
        unknown_location_id = cursor.lastrowid

        # Insert garment type
        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES ('UnknownLocationGarment', 0)"
        )
        garment_id = cursor.lastrowid
        assert garment_id is not None

        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("UnknownLocationBlock", 1.0),
        )
        fb_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 1.0, 9002),
        )
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("cotton",))
        material_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_id, material_id),
        )

        # Link fabric block to garment
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1),
        )

        # Insert fabric block WITH unknown location
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, ?)",
            (fb_type_id, unknown_location_id),
        )

        conn.commit()
        conn.close()

        wiser_client = _build_mock_wiser_client({9002: 5.0})
        result = get_co2_for_garment(garment_id, wiser_client, material_id)

        fb_details = result.fabric_blocks.details[0]
        alternative = fb_details.get("alternative", {})

        # Transport emission should be 0 for unknown location
        assert alternative.get("transport_emission", 0) == 0

    def test_adds_supply_chain_transport_process_okutex_to_takli(self, clean_db):
        """Verify garment process includes transport inside supply chain for Okutex -> Takli Textil."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES (?, ?)",
            ("SupplyChainTransportGarment", 0),
        )
        garment_id = cursor.lastrowid
        assert garment_id is not None

        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("SupplyChainTransportBlock", 2.0),
        )
        fabric_block_type_id = cursor.lastrowid
        assert fabric_block_type_id is not None

        cursor.execute(
            "INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 1.0, 9101),
        )
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("cotton",))
        material_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_id, material_id),
        )
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fabric_block_type_id, 1),
        )

        cursor.execute(
            """
            INSERT INTO manufacturer_distances (
                source_company,
                source_role_group,
                source_location,
                destination_company,
                destination_role_group,
                destination_location,
                distance_km
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "Okutex",
                "fabric",
                "St. Gallen",
                "Takli Textil",
                "garment",
                "Burladingen",
                120.0,
            ),
        )

        conn.commit()
        conn.close()

        wiser_client = _build_mock_wiser_client({9101: 5.0, 7309: 0.2})
        result = get_co2_for_garment(garment_id, wiser_client, material_id)

        process_details = result.processes.details
        supply_chain_process = next(
            (
                process
                for process in process_details
                if process.get("process") == "transport inside supply chain"
            ),
            None,
        )

        assert supply_chain_process is not None
        assert supply_chain_process["amount"] == 120.0
        # amount_kg = 2.0 sqm * 1.0 kg_per_sqm = 2.0 kg
        # emission = 0.2 / 1000 * 120.0 * 2.0 = 0.048
        assert supply_chain_process["emission"] == pytest.approx(0.048)


class TestGetCo2FabricBlockProductionEmissions:
    """Test case 5: get_co2 calculates fabric_block_production_emissions correctly."""

    @pytest.fixture
    def setup_co2_test_db(self, clean_db):
        """Set up database with test data for CO2 calculation."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Create additional tables needed (if not already in clean_db)
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
            CREATE TABLE IF NOT EXISTS garment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS garment_recipe_fabric_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                fabric_block_id INTEGER NOT NULL,
                amount INTEGER
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                amount REAL
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
                location_id INTEGER
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processes_fabric_blocks_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """
        )

        # Insert garment type
        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES (?, ?)",
            ("TestGarment", 0),
        )
        garment_id = cursor.lastrowid

        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("TestBlock", 1.0),
        )
        fb_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("cotton", 1.0, 1001),
        )
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("cotton",))
        material_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_id, material_id),
        )

        # Insert process type with unit and activity_id
        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("test_dyeing", "L", 2001),
        )
        process_id = cursor.lastrowid

        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1),
        )

        # Insert fabric block into inventory (actual instance of the type)
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, co2eq, garment_id, location_id) VALUES (?, ?, ?, ?)",
            (fb_type_id, 0, None, None),
        )
        fb_inventory_id = cursor.lastrowid

        # Link fabric block to process (production recipe)
        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES (?, ?, ?)",
            (fb_type_id, process_id, 3),
        )

        conn.commit()
        conn.close()

        return {
            "garment_id": garment_id,
            "material_id": material_id,
            "fb_type_id": fb_type_id,
            "fb_inventory_id": fb_inventory_id,
            "process_id": process_id,
            "resource_amount": 2.5,
            "process_amount": 3,
        }

    def test_production_emissions_calculated_correctly(self, setup_co2_test_db):
        """Verify fabric_block_production_emissions is calculated from processes and resources."""
        test_data = setup_co2_test_db

        # Mock external API responses
        wiser_client = _build_mock_wiser_client({1001: 5.0, 2001: 0.5})
        result = get_co2_for_garment(
            test_data["garment_id"], wiser_client, test_data["material_id"]
        )

        # Verify fabric blocks emissions are calculated
        assert result.fabric_blocks.total_emission > 0

        # Check production emissions calculation
        # With new schema: process activity emission * amount
        # = 0.5 * 3 = 1.5 (no separate resource table anymore)
        fb_details = result.fabric_blocks.details[0]
        expected_production_emission = 0.5 * 3  # 1.5
        assert fb_details["production_emission"] == expected_production_emission

    def test_production_emissions_zero_when_no_processes(self, clean_db):
        """Verify production emissions is 0 when fabric block has no processes."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Create tables
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
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                amount REAL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processes_fabric_blocks_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """
        )

        # Insert garment type
        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES (?, ?)",
            ("NoProcessGarment", 0),
        )
        garment_id = cursor.lastrowid
        assert garment_id is not None

        # Insert fabric block type (no processes linked)
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("NoProcessBlock", 1.0),
        )
        fb_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("hemp", 1.0, 3001),
        )
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("hemp",))
        material_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_id, material_id),
        )

        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1),
        )

        conn.commit()
        conn.close()

        wiser_client = _build_mock_wiser_client({3001: 10.0})
        result = get_co2_for_garment(garment_id, wiser_client, material_id)

        # Verify production emissions is 0
        fb_details = result.fabric_blocks.details[0]
        assert fb_details["production_emission"] == 0

    def test_production_emissions_accumulates_multiple_resources(self, clean_db):
        """Verify emissions accumulate correctly from multiple processes."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()

        # Create tables
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
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                amount REAL
            )
        """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS processes_fabric_blocks_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                process_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """
        )

        # Insert garment type
        cursor.execute(
            "INSERT INTO garment_types (name, price_chf) VALUES (?, ?)",
            ("MultiProcessGarment", 0),
        )
        garment_id = cursor.lastrowid
        assert garment_id is not None

        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, sqm) VALUES (?, ?)",
            ("MultiProcBlock", 1.0),
        )
        fb_type_id = cursor.lastrowid

        cursor.execute(
            "INSERT OR IGNORE INTO materials (name, kg_per_sqm, activity_id) VALUES (?, ?, ?)",
            ("hemp", 1.0, 4001),
        )
        cursor.execute("SELECT id FROM materials WHERE name = ?", ("hemp",))
        material_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO garment_recipe_materials (garment_type, material_id) VALUES (?, ?)",
            (garment_id, material_id),
        )

        # Insert first process type
        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("dyeing_process", "L", 5001),
        )
        process_id_1 = cursor.lastrowid

        # Insert second process type
        cursor.execute(
            "INSERT INTO process_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("finishing_process", "kcal", 5002),
        )
        process_id_2 = cursor.lastrowid

        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1),
        )

        # Link fabric block to first process
        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES (?, ?, ?)",
            (fb_type_id, process_id_1, 2.0),
        )

        # Link fabric block to second process
        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, amount) VALUES (?, ?, ?)",
            (fb_type_id, process_id_2, 5.0),
        )

        conn.commit()
        conn.close()

        wiser_client = _build_mock_wiser_client({4001: 1.0, 5001: 0.4, 5002: 0.1})
        result = get_co2_for_garment(garment_id, wiser_client, material_id)

        # Calculate expected production emissions:
        # process 1 (dyeing): 0.4 * 2.0 = 0.8
        # process 2 (finishing): 0.1 * 5.0 = 0.5
        # total: 1.3
        fb_details = result.fabric_blocks.details[0]
        expected_production_emission = (0.4 * 2.0) + (0.1 * 5.0)
        assert fb_details["production_emission"] == expected_production_emission
