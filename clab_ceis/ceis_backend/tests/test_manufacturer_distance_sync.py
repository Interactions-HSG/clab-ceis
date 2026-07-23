import sqlite3
from unittest.mock import MagicMock, patch

from ceis_backend.db_init import create_tables
from ceis_backend import manufacturer_distance_sync as sync


def _init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    create_tables(cursor)
    conn.commit()
    conn.close()


def test_sync_populates_distances_when_csv_changed(tmp_path, monkeypatch):
    db_path = tmp_path / "ceis_backend.db"
    csv_path = tmp_path / "manufacturers.csv"
    csv_path.write_text(
        (
            "COMPANY,ROLE,LOCATION,WEBSITE,NOTES,CERTIFICATIONS & DPP\n"
            "Fabric A,fabric manufacturer,\"A Street 1, City A\",,,\n"
            "Garment A,garment manufacturer,\"B Street 1, City B\",,,\n"
            "Finish A,finishing,\"C Street 1, City C\",,,\n"
        ),
        encoding="utf-8",
    )

    _init_db(str(db_path))

    monkeypatch.setattr(sync, "DB_PATH", str(db_path))
    monkeypatch.setattr(sync, "CSV_PATH", csv_path)

    def mock_get(url, params=None, headers=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        if "nominatim" in url:
            query = params.get("q", "")
            if "City A" in query:
                response.json.return_value = [{"lat": "47.0", "lon": "9.0"}]
            elif "City B" in query:
                response.json.return_value = [{"lat": "47.1", "lon": "9.1"}]
            else:
                response.json.return_value = [{"lat": "47.2", "lon": "9.2"}]
            return response

        response.json.return_value = {"routes": [{"distance": 12345.0}]}
        return response

    with patch("ceis_backend.manufacturer_distance_sync.requests.get", side_effect=mock_get):
        result = sync.sync_manufacturer_distances_if_changed()

    assert result["updated"] is True
    assert result["manufacturers"] == 2
    assert result["distances"] == 1

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM manufacturers")
    assert cursor.fetchone()[0] == 2
    cursor.execute("SELECT COUNT(*) FROM manufacturer_distances")
    assert cursor.fetchone()[0] == 1
    cursor.execute(
        "SELECT COUNT(*) FROM manufacturers WHERE role_group = 'finishing'"
    )
    assert cursor.fetchone()[0] == 0
    conn.close()


def test_sync_imports_repair_shops_and_duplicate_company_roles(tmp_path, monkeypatch):
    db_path = tmp_path / "ceis_backend.db"
    csv_path = tmp_path / "manufacturers.csv"
    csv_path.write_text(
        (
            "COMPANY,ROLE,LOCATION,WEBSITE,NOTES,CERTIFICATIONS & DPP\n"
            "Fabric A,fabric manufacturer,\"A Street 1, City A\",,,\n"
            "Takli Textil,garment manufacturer,\"B Street 1, City B\",,,\n"
            "Takli Textil,repair,\"B Street 1, City B\",,,\n"
            "Die Manufaktur GmbH,repair,\"C Street 1, City C\",,,\n"
            "Finish A,finishing,\"D Street 1, City D\",,,\n"
        ),
        encoding="utf-8",
    )

    _init_db(str(db_path))

    monkeypatch.setattr(sync, "DB_PATH", str(db_path))
    monkeypatch.setattr(sync, "CSV_PATH", csv_path)

    def mock_get(url, params=None, headers=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        if "nominatim" in url:
            query = params.get("q", "")
            if "City A" in query:
                response.json.return_value = [{"lat": "47.0", "lon": "9.0"}]
            elif "City B" in query:
                response.json.return_value = [{"lat": "47.1", "lon": "9.1"}]
            elif "City C" in query:
                response.json.return_value = [{"lat": "47.2", "lon": "9.2"}]
            else:
                response.json.return_value = [{"lat": "47.3", "lon": "9.3"}]
            return response

        response.json.return_value = {"routes": [{"distance": 12345.0}]}
        return response

    with patch("ceis_backend.manufacturer_distance_sync.requests.get", side_effect=mock_get):
        result = sync.sync_manufacturer_distances_if_changed()

    assert result["updated"] is True
    assert result["manufacturers"] == 4
    assert result["distances"] == 1

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT company, role_group
        FROM manufacturers
        WHERE company IN ('Takli Textil', 'Die Manufaktur GmbH')
        ORDER BY company, role_group
        """
    )
    assert cursor.fetchall() == [
        ("Die Manufaktur GmbH", "repair"),
        ("Takli Textil", "garment"),
        ("Takli Textil", "repair"),
    ]
    conn.close()


def test_sync_removes_existing_finishers_and_reuses_unchanged_distance(
    tmp_path, monkeypatch
):
    db_path = tmp_path / "ceis_backend.db"
    csv_path = tmp_path / "manufacturers.csv"
    csv_path.write_text(
        (
            "COMPANY,ROLE,LOCATION,WEBSITE,NOTES,CERTIFICATIONS & DPP\n"
            "Fabric A,fabric manufacturer,\"A Street 1, City A\",,,\n"
            "Garment A,garment manufacturer,\"B Street 1, City B\",,,\n"
        ),
        encoding="utf-8",
    )
    _init_db(str(db_path))

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("Fabric A", "fabric manufacturer", "fabric", "A Street 1, City A"),
            ("Garment A", "garment manufacturer", "garment", "B Street 1, City B"),
            ("Finish A", "finishing", "finishing", "C Street 1, City C"),
        ],
    )
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
                "Fabric A",
                "fabric",
                "A Street 1, City A",
                "Garment A",
                "garment",
                "B Street 1, City B",
                12.5,
            ),
            (
                "Garment A",
                "garment",
                "B Street 1, City B",
                "Finish A",
                "finishing",
                "C Street 1, City C",
                20.0,
            ),
        ],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(sync, "DB_PATH", str(db_path))
    monkeypatch.setattr(sync, "CSV_PATH", csv_path)

    with patch("ceis_backend.manufacturer_distance_sync.requests.get") as mocked:
        result = sync.sync_manufacturer_distances_if_changed()
        mocked.assert_not_called()

    assert result["updated"] is True
    assert result["manufacturers"] == 2
    assert result["distances"] == 1

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT role_group FROM manufacturers ORDER BY role_group")
    assert cursor.fetchall() == [("fabric",), ("garment",)]
    cursor.execute(
        """
        SELECT source_role_group, destination_role_group, distance_km
        FROM manufacturer_distances
        """
    )
    assert cursor.fetchall() == [("fabric", "garment", 12.5)]
    conn.close()


def test_sync_skips_when_csv_unchanged(tmp_path, monkeypatch):
    db_path = tmp_path / "ceis_backend.db"
    csv_path = tmp_path / "manufacturers.csv"
    csv_path.write_text(
        (
            "COMPANY,ROLE,LOCATION,WEBSITE,NOTES,CERTIFICATIONS & DPP\n"
            "Fabric A,fabric manufacturer,\"A Street 1, City A\",,,\n"
            "Garment A,garment manufacturer,\"B Street 1, City B\",,,\n"
        ),
        encoding="utf-8",
    )

    _init_db(str(db_path))

    monkeypatch.setattr(sync, "DB_PATH", str(db_path))
    monkeypatch.setattr(sync, "CSV_PATH", csv_path)

    def mock_get(url, params=None, headers=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        if "nominatim" in url:
            q = params.get("q", "")
            if "City A" in q:
                response.json.return_value = [{"lat": "47.0", "lon": "9.0"}]
            else:
                response.json.return_value = [{"lat": "47.1", "lon": "9.1"}]
            return response
        response.json.return_value = {"routes": [{"distance": 10000.0}]}
        return response

    with patch("ceis_backend.manufacturer_distance_sync.requests.get", side_effect=mock_get):
        first = sync.sync_manufacturer_distances_if_changed()
        assert first["updated"] is True

    with patch("ceis_backend.manufacturer_distance_sync.requests.get") as mocked:
        second = sync.sync_manufacturer_distances_if_changed()
        assert second["updated"] is False
        assert second["reason"] == "unchanged"
        mocked.assert_not_called()


def test_sync_retries_when_distance_resolution_failed(tmp_path, monkeypatch):
    db_path = tmp_path / "ceis_backend.db"
    csv_path = tmp_path / "manufacturers.csv"
    csv_path.write_text(
        (
            "COMPANY,ROLE,LOCATION,WEBSITE,NOTES,CERTIFICATIONS & DPP\n"
            "Fabric A,fabric manufacturer,\"A Street 1, City A\",,,\n"
            "Garment A,garment manufacturer,\"B Street 1, City B\",,,\n"
        ),
        encoding="utf-8",
    )

    _init_db(str(db_path))

    monkeypatch.setattr(sync, "DB_PATH", str(db_path))
    monkeypatch.setattr(sync, "CSV_PATH", csv_path)

    # First run: geocoding fails for all addresses.
    with patch("ceis_backend.manufacturer_distance_sync.requests.get") as mocked:
        mocked.return_value.status_code = 200
        mocked.return_value.raise_for_status = MagicMock()
        mocked.return_value.json.return_value = []
        first = sync.sync_manufacturer_distances_if_changed()
        assert first["updated"] is False
        assert first["reason"] == "distance_resolution_failed"

    # Second run: should retry (not treated as unchanged) and succeed.
    def mock_get(url, params=None, headers=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        if "nominatim" in url:
            q = params.get("q", "")
            if "City A" in q:
                response.json.return_value = [{"lat": "47.0", "lon": "9.0"}]
            else:
                response.json.return_value = [{"lat": "47.1", "lon": "9.1"}]
            return response
        response.json.return_value = {"routes": [{"distance": 10000.0}]}
        return response

    with patch("ceis_backend.manufacturer_distance_sync.requests.get", side_effect=mock_get):
        second = sync.sync_manufacturer_distances_if_changed()
        assert second["updated"] is True
        assert second["distances"] == 1


def test_sync_retries_when_hash_matches_but_distances_are_empty(tmp_path, monkeypatch):
    db_path = tmp_path / "ceis_backend.db"
    csv_path = tmp_path / "manufacturers.csv"
    csv_text = (
        "COMPANY,ROLE,LOCATION,WEBSITE,NOTES,CERTIFICATIONS & DPP\n"
        "Fabric A,fabric manufacturer,\"A Street 1, City A\",,,\n"
        "Garment A,garment manufacturer,\"B Street 1, City B\",,,\n"
    )
    csv_path.write_text(csv_text, encoding="utf-8")

    _init_db(str(db_path))

    monkeypatch.setattr(sync, "DB_PATH", str(db_path))
    monkeypatch.setattr(sync, "CSV_PATH", csv_path)

    # Simulate old state: hash stored, but no distances persisted.
    csv_hash = sync._csv_sha256(csv_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sync_state (key, value) VALUES (?, ?)",
        (sync.SYNC_HASH_KEY, csv_hash),
    )
    conn.commit()
    conn.close()

    def mock_get(url, params=None, headers=None, timeout=None):
        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()
        if "nominatim" in url:
            q = params.get("q", "")
            if "City A" in q:
                response.json.return_value = [{"lat": "47.0", "lon": "9.0"}]
            else:
                response.json.return_value = [{"lat": "47.1", "lon": "9.1"}]
            return response
        response.json.return_value = {"routes": [{"distance": 10000.0}]}
        return response

    with patch("ceis_backend.manufacturer_distance_sync.requests.get", side_effect=mock_get):
        result = sync.sync_manufacturer_distances_if_changed()
        assert result["updated"] is True
        assert result["distances"] == 1
