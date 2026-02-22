import sqlite3
import pytest
from unittest.mock import patch, MagicMock

# Best Practice: Import directly from modules without sys.path manipulation
from db_init import init_sqlite_db
from utils import get_recipe_for_fabric_block, get_co2
from models import Process


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
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create tables without seeding
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fabric_block_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            material TEXT,
            amount_kg INTEGER,
            activity_id INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS process_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS resource_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            unit TEXT,
            activity_id INTEGER NOT NULL
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS process_resource_consumption (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            process_id INTEGER NOT NULL,
            resource_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (process_id) REFERENCES process_types(id),
            FOREIGN KEY (resource_id) REFERENCES resource_types(id),
            UNIQUE(process_id, resource_id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fabric_block_recipe_processes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fabric_block_type INTEGER NOT NULL,
            process_id INTEGER NOT NULL,
            time INTEGER,
            FOREIGN KEY (fabric_block_type) REFERENCES fabric_block_types(id) ON DELETE CASCADE,
            FOREIGN KEY (process_id) REFERENCES process_types(id) ON DELETE CASCADE
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS garment_recipe_fabric_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            garment_type INTEGER NOT NULL,
            fabric_block_id INTEGER NOT NULL,
            amount INTEGER
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fabric_blocks_inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type_id INTEGER NOT NULL,
            co2eq INTEGER,
            garment_id INTEGER
        )
    """)
    
    conn.commit()
    conn.close()
    
    yield str(db_path)


class TestFabricBlockRecipeProcessesTableCreation:
    """Test case 1: fabric_block_recipe_processes table is created correctly."""
    
    def test_table_exists_after_init(self, test_db):
        """Verify the fabric_block_recipe_processes table exists after initialization."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='fabric_block_recipe_processes'
        """)
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
        assert "time" in column_names
    
    def test_table_seeded_with_data(self, test_db):
        """Verify the table is seeded with initial data."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM fabric_block_recipe_processes")
        count = cursor.fetchone()[0]
        conn.close()
        
        assert count > 0


class TestGetRecipeForFabricBlock:
    """Test cases 2 & 3: get_recipe_for_fabric_block function."""
    
    def test_returns_processes_for_existing_fabric_block(self, test_db):
        """Test case 2: Returns associated processes for a given fabric block."""
        material, activity_id, amount_kg, processes = get_recipe_for_fabric_block("FB1")
        
        assert material == "cotton"
        assert activity_id == 3878
        assert amount_kg == 1.5
        assert len(processes) > 0
        assert all(isinstance(p, Process) for p in processes)
        
        # Verify FB1 has the 'dyeing' process from seeded data
        process_names = [p.activity for p in processes]
        assert "dyeing" in process_names
    
    def test_returns_correct_process_details(self, test_db):
        """Verify process details match seeded data."""
        _, _, _, processes = get_recipe_for_fabric_block("FB1")
        
        dyeing_process = next((p for p in processes if p.activity == "dyeing"), None)
        assert dyeing_process is not None
        assert dyeing_process.time == 2
    
    def test_returns_empty_list_for_nonexistent_fabric_block(self, test_db):
        """Test case 3: Returns empty list for non-existent fabric block."""
        material, activity_id, amount_kg, processes = get_recipe_for_fabric_block("NonExistent")
        
        assert material is None
        assert activity_id is None
        assert amount_kg == 0
        assert processes == []
    
    def test_returns_processes_for_fb2(self, test_db):
        """Verify FB2 returns its associated washing process."""
        material, activity_id, amount_kg, processes = get_recipe_for_fabric_block("FB2")
        
        assert material == "polyester"
        assert activity_id == 5544
        assert amount_kg == 1.2
        
        process_names = [p.activity for p in processes]
        assert "washing" in process_names


class TestDeleteFabricBlockType:
    """Test case 4: delete_fabric_block_type removes entries from fabric_block_recipe_processes."""
    
    def test_delete_removes_recipe_processes(self, clean_db):
        """Verify deleting a fabric block type removes its recipe processes."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        # Insert test data
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("TestFB", "wool", 2.0, 1234)
        )
        fb_type_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO process_types (name) VALUES (?)",
            ("test_process",)
        )
        process_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, time) VALUES (?, ?, ?)",
            (fb_type_id, process_id, 5)
        )
        conn.commit()
        
        # Verify data exists
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,)
        )
        assert cursor.fetchone()[0] == 1
        
        conn.close()
        
        # Import and call delete function
        from main import delete_fabric_block_type
        delete_fabric_block_type(fb_type_id)
        
        # Verify recipe processes are deleted
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,)
        )
        assert cursor.fetchone()[0] == 0
        
        # Verify fabric block type is deleted
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_types WHERE id = ?",
            (fb_type_id,)
        )
        assert cursor.fetchone()[0] == 0
        
        conn.close()
    
    def test_delete_removes_multiple_recipe_processes(self, clean_db):
        """Verify deleting removes all associated recipe processes."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("MultiFB", "silk", 1.0, 5678)
        )
        fb_type_id = cursor.lastrowid
        
        # Insert multiple processes
        for i, proc_name in enumerate(["cutting", "stitching", "finishing"]):
            cursor.execute("INSERT INTO process_types (name) VALUES (?)", (proc_name,))
            process_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, time) VALUES (?, ?, ?)",
                (fb_type_id, process_id, i + 1)
            )
        conn.commit()
        
        # Verify 3 recipe processes exist
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,)
        )
        assert cursor.fetchone()[0] == 3
        
        conn.close()
        
        # Delete fabric block type
        from main import delete_fabric_block_type
        delete_fabric_block_type(fb_type_id)
        
        # Verify all recipe processes are deleted
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM fabric_block_recipe_processes WHERE fabric_block_type = ?",
            (fb_type_id,)
        )
        assert cursor.fetchone()[0] == 0
        conn.close()


class TestGetLocationsEndpoint:
    """Test case: GET /locations endpoint returns correct list of locations."""
    
    def test_returns_all_locations(self, test_db):
        """Verify GET /locations returns all seeded locations."""
        from fastapi.testclient import TestClient
        from main import app
        
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
        from fastapi.testclient import TestClient
        from main import app
        
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
        from fastapi.testclient import TestClient
        from main import app
        
        # Add locations table to clean_db
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        conn.commit()
        conn.close()
        
        client = TestClient(app)
        response = client.get("/locations")
        
        assert response.status_code == 200
        assert response.json() == []


class TestCreateFabricBlockWithLocation:
    """Test case: create_fabric_block stores fabric block with location_id."""
    
    def test_creates_fabric_block_with_location_id(self, test_db):
        """Verify fabric block is stored with the specified location_id."""
        from fastapi.testclient import TestClient
        from main import app
        
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
        response = client.post("/fabric-blocks", json={
            "type_id": fb_type_id,
            "processes": [],
            "location_id": location_id
        })
        
        assert response.status_code == 200
        result = response.json()
        assert "id" in result
        
        # Verify location_id is stored in database
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT location_id FROM fabric_blocks_inventory WHERE id = ?",
            (result["id"],)
        )
        stored_location_id = cursor.fetchone()[0]
        conn.close()
        
        assert stored_location_id == location_id
    
    def test_creates_fabric_block_without_location_id(self, test_db):
        """Verify fabric block can be created without location_id (NULL)."""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM fabric_block_types LIMIT 1")
        fb_type_id = cursor.fetchone()[0]
        conn.close()
        
        response = client.post("/fabric-blocks", json={
            "type_id": fb_type_id,
            "processes": []
        })
        
        assert response.status_code == 200
        result = response.json()
        
        # Verify location_id is NULL
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT location_id FROM fabric_blocks_inventory WHERE id = ?",
            (result["id"],)
        )
        stored_location_id = cursor.fetchone()[0]
        conn.close()
        
        assert stored_location_id is None


class TestGetFabricBlocksWithLocation:
    """Test case: get_fabric_blocks returns location_name for fabric blocks."""
    
    def test_returns_location_name_for_fabric_block(self, test_db):
        """Verify get_fabric_blocks returns location_name when location_id is set."""
        from fastapi.testclient import TestClient
        from main import app
        
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
            (fb_type_id, location_id)
        )
        conn.commit()
        conn.close()
        
        response = client.get("/fabric-blocks")
        
        assert response.status_code == 200
        fabric_blocks = response.json()
        
        # Find the block with Dornbirn location
        block_with_location = next(
            (fb for fb in fabric_blocks if fb.get("location") == "Dornbirn"),
            None
        )
        assert block_with_location is not None
        assert block_with_location["location"] == "Dornbirn"
    
    def test_returns_null_location_for_fabric_block_without_location(self, test_db):
        """Verify get_fabric_blocks returns null location when location_id is not set."""
        from fastapi.testclient import TestClient
        from main import app
        
        client = TestClient(app)
        
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM fabric_block_types LIMIT 1")
        fb_type_id = cursor.fetchone()[0]
        
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, NULL)",
            (fb_type_id,)
        )
        fb_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        response = client.get("/fabric-blocks")
        
        assert response.status_code == 200
        fabric_blocks = response.json()
        
        # Find the block we just created
        block_without_location = next(
            (fb for fb in fabric_blocks if fb["id"] == fb_id),
            None
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                time INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        # Add location_id column to fabric_blocks_inventory if not exists
        cursor.execute("PRAGMA table_info(fabric_blocks_inventory)")
        columns = [col[1] for col in cursor.fetchall()]
        if "location_id" not in columns:
            cursor.execute("ALTER TABLE fabric_blocks_inventory ADD COLUMN location_id INTEGER")
        
        # Insert locations
        cursor.execute("INSERT INTO locations (name) VALUES ('St. Gallen')")
        st_gallen_id = cursor.lastrowid
        cursor.execute("INSERT INTO locations (name) VALUES ('Sigmaringen')")
        sigmaringen_id = cursor.lastrowid
        
        # Insert garment type
        cursor.execute("INSERT INTO garment_types (name) VALUES ('TransportTestGarment')")
        garment_id = cursor.lastrowid
        
        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("TransportTestBlock", "cotton", 2.0, 8001)
        )
        fb_type_id = cursor.lastrowid
        
        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1)
        )
        
        # Insert fabric block in inventory with St. Gallen location
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, ?)",
            (fb_type_id, st_gallen_id)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "garment_id": garment_id,
            "fb_type_id": fb_type_id,
            "st_gallen_id": st_gallen_id,
            "sigmaringen_id": sigmaringen_id,
        }
    
    def test_transport_emission_calculated_for_known_location(self, setup_transport_test_db):
        """Verify transport_emission is calculated based on location distance and API response."""
        test_data = setup_transport_test_db
        
        def mock_get_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            
            url = args[0] if args else kwargs.get('url', '')
            
            if "8001" in url:  # Material activity
                mock_response.json.return_value = {
                    "lcia_results": [{"method": {"name": "IPCC 2021"}, "emissions": 5.0}]
                }
            elif "7309" in url:  # Transport activity (activity_id_transport)
                mock_response.json.return_value = {
                    "lcia_results": [{"method": {"name": "IPCC 2021"}, "emissions": 0.1}]
                }
            else:
                mock_response.json.return_value = {"lcia_results": []}
            
            return mock_response
        
        with patch('utils.get_wiser_token', return_value="mock_token"):
            with patch('utils.requests.get', side_effect=mock_get_response):
                result = get_co2(test_data["garment_id"])
        
        # Check transport emission is calculated
        # St. Gallen distance = 10 km, amount_kg = 2.0
        # transport_emission = emission_per_unit / 1000 * distance * amount
        # = 0.1 / 1000 * 10 * 2.0 = 0.002
        fb_details = result.fabric_blocks.details[0]
        alternative = fb_details.get("alternative", {})
        
        assert "transport_emission" in alternative
        expected_transport = 0.1 / 1000 * 10 * 2.0  # 0.002
        assert alternative["transport_emission"] == pytest.approx(expected_transport)
    
    def test_transport_emission_zero_for_no_location(self, clean_db):
        """Verify transport_emission is zero when fabric block has no location."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                time INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        # Add location_id column
        cursor.execute("PRAGMA table_info(fabric_blocks_inventory)")
        columns = [col[1] for col in cursor.fetchall()]
        if "location_id" not in columns:
            cursor.execute("ALTER TABLE fabric_blocks_inventory ADD COLUMN location_id INTEGER")
        
        # Insert garment type
        cursor.execute("INSERT INTO garment_types (name) VALUES ('NoLocationGarment')")
        garment_id = cursor.lastrowid
        
        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("NoLocationBlock", "cotton", 1.5, 9001)
        )
        fb_type_id = cursor.lastrowid
        
        # Link fabric block to garment
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1)
        )
        
        # Insert fabric block WITHOUT location_id
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, NULL)",
            (fb_type_id,)
        )
        
        conn.commit()
        conn.close()
        
        def mock_get_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "lcia_results": [{"method": {"name": "IPCC 2021"}, "emissions": 5.0}]
            }
            return mock_response
        
        with patch('utils.get_wiser_token', return_value="mock_token"):
            with patch('utils.requests.get', side_effect=mock_get_response):
                result = get_co2(garment_id)
        
        fb_details = result.fabric_blocks.details[0]
        alternative = fb_details.get("alternative", {})
        
        # Transport emission should be 0 when no location
        assert alternative.get("transport_emission", 0) == 0
    
    def test_transport_emission_zero_for_unknown_location(self, clean_db):
        """Verify transport_emission is zero when location is not in distances_to_manufacturer."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                time INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        # Add location_id column
        cursor.execute("PRAGMA table_info(fabric_blocks_inventory)")
        columns = [col[1] for col in cursor.fetchall()]
        if "location_id" not in columns:
            cursor.execute("ALTER TABLE fabric_blocks_inventory ADD COLUMN location_id INTEGER")
        
        # Insert an unknown location (not in distances_to_manufacturer)
        cursor.execute("INSERT INTO locations (name) VALUES ('Unknown City')")
        unknown_location_id = cursor.lastrowid
        
        # Insert garment type
        cursor.execute("INSERT INTO garment_types (name) VALUES ('UnknownLocationGarment')")
        garment_id = cursor.lastrowid
        
        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("UnknownLocationBlock", "polyester", 1.0, 9002)
        )
        fb_type_id = cursor.lastrowid
        
        # Link fabric block to garment
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1)
        )
        
        # Insert fabric block WITH unknown location
        cursor.execute(
            "INSERT INTO fabric_blocks_inventory (type_id, location_id) VALUES (?, ?)",
            (fb_type_id, unknown_location_id)
        )
        
        conn.commit()
        conn.close()
        
        def mock_get_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "lcia_results": [{"method": {"name": "IPCC 2021"}, "emissions": 5.0}]
            }
            return mock_response
        
        with patch('utils.get_wiser_token', return_value="mock_token"):
            with patch('utils.requests.get', side_effect=mock_get_response):
                result = get_co2(garment_id)
        
        fb_details = result.fabric_blocks.details[0]
        alternative = fb_details.get("alternative", {})
        
        # Transport emission should be 0 for unknown location
        assert alternative.get("transport_emission", 0) == 0


class TestGetCo2FabricBlockProductionEmissions:
    """Test case 5: get_co2 calculates fabric_block_production_emissions correctly."""
    
    @pytest.fixture
    def setup_co2_test_db(self, clean_db):
        """Set up database with test data for CO2 calculation."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        # Create additional tables needed
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                time INTEGER
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """)
        
        # Insert garment type
        cursor.execute("INSERT INTO garment_types (name) VALUES (?)", ("TestGarment",))
        garment_id = cursor.lastrowid
        
        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("TestBlock", "cotton", 1.0, 1001)
        )
        fb_type_id = cursor.lastrowid
        
        # Insert process type
        cursor.execute("INSERT INTO process_types (name) VALUES (?)", ("test_dyeing",))
        process_id = cursor.lastrowid
        
        # Insert resource type
        cursor.execute(
            "INSERT INTO resource_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("test_electricity", "kWh", 2001)
        )
        resource_id = cursor.lastrowid
        
        # Link process to resource consumption
        cursor.execute(
            "INSERT INTO process_resource_consumption (process_id, resource_id, amount) VALUES (?, ?, ?)",
            (process_id, resource_id, 2.5)
        )
        
        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1)
        )
        
        # Link fabric block to process (production recipe)
        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, time) VALUES (?, ?, ?)",
            (fb_type_id, process_id, 3)
        )
        
        conn.commit()
        conn.close()
        
        return {
            "garment_id": garment_id,
            "fb_type_id": fb_type_id,
            "process_id": process_id,
            "resource_id": resource_id,
            "resource_amount": 2.5,
            "process_time": 3
        }
    
    def test_production_emissions_calculated_correctly(self, setup_co2_test_db):
        """Verify fabric_block_production_emissions is calculated from processes and resources."""
        test_data = setup_co2_test_db
        
        # Mock external API responses
        def mock_get_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            
            url = args[0] if args else kwargs.get('url', '')
            
            if "1001" in url:  # Material activity
                mock_response.json.return_value = {
                    "lcia_results": [
                        {"method": {"name": "IPCC 2021"}, "emissions": 5.0}
                    ]
                }
            elif "2001" in url:  # Resource activity
                mock_response.json.return_value = {
                    "lcia_results": [
                        {"method": {"name": "IPCC 2021"}, "emissions": 0.5}
                    ]
                }
            else:
                mock_response.json.return_value = {"lcia_results": []}
            
            return mock_response
        
        with patch('utils.get_wiser_token', return_value="mock_token"):
            with patch('utils.requests.get', side_effect=mock_get_response):
                result = get_co2(test_data["garment_id"])
        
        # Verify fabric blocks emissions are calculated
        assert result.fabric_blocks.total_emission > 0
        
        # Check production emissions calculation
        # Expected: resource_emission_per_unit * resource_amount * process_time
        # = 0.5 * 2.5 * 3 = 3.75
        fb_details = result.fabric_blocks.details[0]
        expected_production_emission = 0.5 * 2.5 * 3  # 3.75
        assert fb_details["production_emission"] == expected_production_emission
    
    def test_production_emissions_zero_when_no_processes(self, clean_db):
        """Verify production emissions is 0 when fabric block has no processes."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                time INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """)
        
        # Insert garment type
        cursor.execute("INSERT INTO garment_types (name) VALUES (?)", ("NoProcessGarment",))
        garment_id = cursor.lastrowid
        
        # Insert fabric block type (no processes linked)
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("NoProcessBlock", "linen", 1.0, 3001)
        )
        fb_type_id = cursor.lastrowid
        
        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1)
        )
        
        conn.commit()
        conn.close()
        
        def mock_get_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            mock_response.json.return_value = {
                "lcia_results": [
                    {"method": {"name": "IPCC 2021"}, "emissions": 10.0}
                ]
            }
            return mock_response
        
        with patch('utils.get_wiser_token', return_value="mock_token"):
            with patch('utils.requests.get', side_effect=mock_get_response):
                result = get_co2(garment_id)
        
        # Verify production emissions is 0
        fb_details = result.fabric_blocks.details[0]
        assert fb_details["production_emission"] == 0
    
    def test_production_emissions_accumulates_multiple_resources(self, clean_db):
        """Verify emissions accumulate correctly from multiple resources."""
        conn = sqlite3.connect("ceis_backend.db")
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS garment_recipe_processes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                garment_type INTEGER NOT NULL,
                process_id INTEGER NOT NULL,
                time INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS preparations_used_fabric_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type_id INTEGER NOT NULL,
                amount INTEGER,
                fabric_block_id INTEGER
            )
        """)
        
        # Insert garment type
        cursor.execute("INSERT INTO garment_types (name) VALUES (?)", ("MultiResourceGarment",))
        garment_id = cursor.lastrowid
        
        # Insert fabric block type
        cursor.execute(
            "INSERT INTO fabric_block_types (name, material, amount_kg, activity_id) VALUES (?, ?, ?, ?)",
            ("MultiResBlock", "hemp", 1.0, 4001)
        )
        fb_type_id = cursor.lastrowid
        
        # Insert process type
        cursor.execute("INSERT INTO process_types (name) VALUES (?)", ("multi_res_process",))
        process_id = cursor.lastrowid
        
        # Insert two resource types
        cursor.execute(
            "INSERT INTO resource_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("electricity", "kWh", 5001)
        )
        elec_resource_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO resource_types (name, unit, activity_id) VALUES (?, ?, ?)",
            ("water", "L", 5002)
        )
        water_resource_id = cursor.lastrowid
        
        # Link process to both resources
        cursor.execute(
            "INSERT INTO process_resource_consumption (process_id, resource_id, amount) VALUES (?, ?, ?)",
            (process_id, elec_resource_id, 2.0)
        )
        cursor.execute(
            "INSERT INTO process_resource_consumption (process_id, resource_id, amount) VALUES (?, ?, ?)",
            (process_id, water_resource_id, 5.0)
        )
        
        # Link fabric block to garment recipe
        cursor.execute(
            "INSERT INTO garment_recipe_fabric_blocks (garment_type, fabric_block_id, amount) VALUES (?, ?, ?)",
            (garment_id, fb_type_id, 1)
        )
        
        # Link fabric block to process
        cursor.execute(
            "INSERT INTO fabric_block_recipe_processes (fabric_block_type, process_id, time) VALUES (?, ?, ?)",
            (fb_type_id, process_id, 2)
        )
        
        conn.commit()
        conn.close()
        
        def mock_get_response(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status = MagicMock()
            
            url = args[0] if args else kwargs.get('url', '')
            
            if "4001" in url:  # Material
                mock_response.json.return_value = {
                    "lcia_results": [{"method": {"name": "IPCC 2021"}, "emissions": 1.0}]
                }
            elif "5001" in url:  # Electricity
                mock_response.json.return_value = {
                    "lcia_results": [{"method": {"name": "IPCC 2021"}, "emissions": 0.4}]
                }
            elif "5002" in url:  # Water
                mock_response.json.return_value = {
                    "lcia_results": [{"method": {"name": "IPCC 2021"}, "emissions": 0.1}]
                }
            else:
                mock_response.json.return_value = {"lcia_results": []}
            
            return mock_response
        
        with patch('utils.get_wiser_token', return_value="mock_token"):
            with patch('utils.requests.get', side_effect=mock_get_response):
                result = get_co2(garment_id)
        
        # Calculate expected production emissions:
        # electricity: 0.4 * 2.0 * 2 = 1.6
        # water: 0.1 * 5.0 * 2 = 1.0
        # total: 2.6
        fb_details = result.fabric_blocks.details[0]
        expected_production_emission = (0.4 * 2.0 * 2) + (0.1 * 5.0 * 2)
        assert fb_details["production_emission"] == expected_production_emission
