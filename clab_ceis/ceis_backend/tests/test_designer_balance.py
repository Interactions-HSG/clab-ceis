import sqlite3
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from ceis_backend.db_init import init_sqlite_db
from ceis_backend.main import app


def _build_mock_wiser_client(
    emissions_by_activity: dict[int, float | None],
) -> MagicMock:
    wiser_client = MagicMock()
    wiser_client.get_emission_per_unit.side_effect = emissions_by_activity.get
    return wiser_client


def _insert_manufacturer_data() -> None:
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()

    cursor.executemany(
        """
        INSERT INTO manufacturers (company, role, role_group, location)
        VALUES (?, ?, ?, ?)
        """,
        [
            ("Fabric Alpha", "fabric manufacturer", "fabric", "St. Gallen"),
            ("Fabric Beta", "fabric manufacturer", "fabric", "Dornbirn"),
            (
                "Garment Works",
                "garment manufacturer",
                "garment",
                "Burladingen",
            ),
            ("Finish Lab", "finishing", "finishing", "Ravensburg"),
        ],
    )

    cursor.executemany(
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
        [
            (
                "Fabric Alpha",
                "fabric",
                "St. Gallen",
                "Garment Works",
                "garment",
                "Burladingen",
                120.0,
            ),
            (
                "Fabric Beta",
                "fabric",
                "Dornbirn",
                "Garment Works",
                "garment",
                "Burladingen",
                260.0,
            ),
            (
                "Garment Works",
                "garment",
                "Burladingen",
                "Finish Lab",
                "finishing",
                "Ravensburg",
                80.0,
            ),
        ],
    )

    conn.commit()
    conn.close()


def test_designer_balance_endpoint_returns_balanced_scenario(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CEIS_DISABLE_DISTANCE_SYNC", "1")
    init_sqlite_db()
    _insert_manufacturer_data()

    with TestClient(app) as client:
        client.app.state.wiser_client = _build_mock_wiser_client(
            {
                276186: 8.0,
                6756: 6.0,
                6566: 1.0,
                21893: 2.0,
                7309: 0.2,
                17901: 0.1,
            }
        )

        options_response = client.get("/designer-balance/options")
        assert options_response.status_code == 200
        options_payload = options_response.json()
        assert any(
            role["company"] == "Fabric Alpha"
            for role in options_payload["suppliers"]["fabric"]
        )

        garment_types = client.get("/garment-types").json()
        basic_trousers = next(
            garment for garment in garment_types if garment["name"] == "Basic Trousers"
        )

        materials = client.get(
            f"/garment-types/{basic_trousers['id']}/materials"
        ).json()
        hemp = next(material for material in materials if material["name"] == "hemp")

        response = client.get(
            f"/designer-balance/{basic_trousers['id']}",
            params={
                "material_id": hemp["id"],
                "fabric_supplier": "Fabric Alpha",
                "garment_supplier": "Garment Works",
                "finishing_supplier": "Finish Lab",
            },
        )

    assert response.status_code == 200
    payload = response.json()

    assert payload["garment"]["name"] == "Basic Trousers"
    assert payload["material"]["name"] == "hemp"
    assert payload["selection"]["fabric_supplier"] == "Fabric Alpha"
    assert len(payload["supply_chain"]["legs"]) == 2
    assert payload["summary"]["economic_total_chf"] > 0
    assert payload["summary"]["co2eq_total_kg"] > 0
    assert payload["summary"]["average_lifetime_wears"] == 130
    assert any(row["process_type"] == "transport" for row in payload["process_table"])


def test_designer_balance_supplier_switch_changes_transport_balance(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CEIS_DISABLE_DISTANCE_SYNC", "1")
    init_sqlite_db()
    _insert_manufacturer_data()

    with TestClient(app) as client:
        client.app.state.wiser_client = _build_mock_wiser_client(
            {
                276186: 8.0,
                6756: 6.0,
                6566: 1.0,
                21893: 2.0,
                7309: 0.2,
                17901: 0.1,
            }
        )

        garment_types = client.get("/garment-types").json()
        basic_trousers = next(
            garment for garment in garment_types if garment["name"] == "Basic Trousers"
        )
        materials = client.get(
            f"/garment-types/{basic_trousers['id']}/materials"
        ).json()
        hemp = next(material for material in materials if material["name"] == "hemp")

        alpha_response = client.get(
            f"/designer-balance/{basic_trousers['id']}",
            params={
                "material_id": hemp["id"],
                "fabric_supplier": "Fabric Alpha",
                "garment_supplier": "Garment Works",
                "finishing_supplier": "Finish Lab",
            },
        )
        beta_response = client.get(
            f"/designer-balance/{basic_trousers['id']}",
            params={
                "material_id": hemp["id"],
                "fabric_supplier": "Fabric Beta",
                "garment_supplier": "Garment Works",
                "finishing_supplier": "Finish Lab",
            },
        )

    assert alpha_response.status_code == 200
    assert beta_response.status_code == 200

    alpha_payload = alpha_response.json()
    beta_payload = beta_response.json()

    assert (
        alpha_payload["summary"]["transport_cost_chf"]
        < beta_payload["summary"]["transport_cost_chf"]
    )
    assert (
        alpha_payload["summary"]["transport_co2eq_kg"]
        < beta_payload["summary"]["transport_co2eq_kg"]
    )
    assert (
        alpha_payload["summary"]["total_delay_days"]
        < beta_payload["summary"]["total_delay_days"]
    )


def test_designer_garment_reference_endpoint_returns_design_inputs(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CEIS_DISABLE_DISTANCE_SYNC", "1")
    init_sqlite_db()

    with TestClient(app) as client:
        client.app.state.wiser_client = _build_mock_wiser_client(
            {
                276186: 8.0,
                6756: 6.0,
                20936: 10.0,
                6566: 1.0,
                21893: 2.0,
                17901: 0.1,
            }
        )
        response = client.get("/designer-garment/reference")

    assert response.status_code == 200
    payload = response.json()
    assert payload["garment_types"]
    assert payload["materials"]
    assert payload["process_types"]
    assert payload["fabric_block_types"]
    assert "longevity_wears" in payload["materials"][0]
    assert "co2eq_per_kg" in payload["materials"][0]
    assert "economic_cost_per_unit_chf" in payload["process_types"][0]

    hemp_material = next(
        material for material in payload["materials"] if material["name"] == "hemp"
    )
    assert hemp_material["co2eq_per_kg"] == 8.0

    hemp_block = next(
        fabric_block
        for fabric_block in payload["fabric_block_types"]
        if fabric_block["name"] == "80x64" and fabric_block["material"] == "hemp"
    )
    assert hemp_block["sqm"] == 0.512
    assert hemp_block["weight_kg"] == 0.108
    assert hemp_block["material_cost_chf"] == 2.58
    assert hemp_block["block_process_cost_chf"] == 0.09
    assert hemp_block["co2eq_kg"] == 0.929
    assert hemp_block["processes"]
