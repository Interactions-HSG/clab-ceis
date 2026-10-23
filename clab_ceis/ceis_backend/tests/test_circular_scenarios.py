import sqlite3
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from ceis_backend.circular_scenarios import (
    DAMAGE_PROFILE_BY_CODE,
    calculate_circular_scenarios,
    get_circular_scenario_options,
    get_return_inventory_processes,
)
from ceis_backend.db_init import init_sqlite_db
from ceis_backend.main import app
from ceis_backend.queries import db_create_order, db_ship_order


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    init_sqlite_db()


def _mock_wiser_client():
    client = MagicMock()
    client.get_emission_per_unit.side_effect = {
        2660: 0.5,
        6566: 1.2525767471944982,
        4358: 5.0,
        6756: 4.0,
        20936: 8.0,
        276385: 0.2,
        7309: 0.1,
    }.get
    return client


def _component_total(scenario):
    return sum(component["co2eq"] for component in scenario["components"])


def test_options_use_actual_sold_garments(seeded_db):
    payload = get_circular_scenario_options()

    assert payload["garments"]
    assert all(
        "garment #" in garment["label"] for garment in payload["garments"]
    )
    assert {damage["code"] for damage in payload["damages"]} >= {
        "small_hole",
        "zipper",
        "burn",
    }


def test_shipped_production_order_supports_circular_scenarios(seeded_db):
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT gt.id, grm.material_id
        FROM garment_types gt
        JOIN garment_recipe_materials grm ON grm.garment_type = gt.id
        ORDER BY gt.id, grm.id
        LIMIT 1
        """
    )
    garment_type_id, material_id = cursor.fetchone()
    cursor.execute(
        """
        UPDATE garments_inventory
        SET sold = 1
        WHERE type_id = ? AND returned_from_garment_id IS NULL
        """,
        (garment_type_id,),
    )
    conn.commit()
    conn.close()

    order = db_create_order(garment_type_id, material_id)
    assert order["fulfillment_type"] == "production"
    shipped = db_ship_order(order["id"])

    payload = calculate_circular_scenarios(
        garment_id=shipped["garment_inventory_id"],
        distance_km=100,
        damage_code="small_hole",
        wiser_client=_mock_wiser_client(),
    )

    assert payload["garment"]["id"] == shipped["garment_inventory_id"]
    assert payload["garment"]["fabric_block_count"] > 0
    assert payload["repair"]["self_repair"]["available"] is True


def test_shop_repair_request_is_visible_in_repair_queue(seeded_db):
    garment_id = get_circular_scenario_options()["garments"][0]["id"]

    with TestClient(app) as client:
        created = client.post(
            "/repairs",
            json={
                "garment_id": garment_id,
                "action": "professional_repair",
                "damage_code": "small_hole",
            },
        )
        queue = client.get("/repairs")

    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    assert queue.status_code == 200
    assert queue.json()[0]["id"] == created.json()["id"]
    assert queue.json()[0]["garment_id"] == garment_id
    assert queue.json()[0]["action"] == "professional_repair"
    assert queue.json()[0]["action_label"] == "Perform professional repair"
    assert queue.json()[0]["damage_code"] == "small_hole"


def test_garment_return_copies_blocks_with_processes_only_on_garment(seeded_db):
    source_garment_id = get_circular_scenario_options()["garments"][0]["id"]
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM fabric_blocks_inventory WHERE garment_id = ?",
        (source_garment_id,),
    )
    source_block_count = cursor.fetchone()[0]
    conn.close()

    with TestClient(app) as client:
        response = client.post(
            "/garment-returns",
            json={
                "garment_id": source_garment_id,
                "damage_code": "small_hole",
            },
        )
        duplicate = client.post(
            "/garment-returns",
            json={
                "garment_id": source_garment_id,
                "damage_code": "small_hole",
            },
        )

    assert response.status_code == 201
    assert duplicate.status_code == 409
    returned = response.json()
    assert returned["source_garment_id"] == source_garment_id
    assert returned["fabric_block_count"] == source_block_count
    assert returned["discount_percent"] == 50
    assert source_garment_id not in {
        garment["id"] for garment in get_circular_scenario_options()["garments"]
    }

    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT sold, returned_from_garment_id
        FROM garments_inventory
        WHERE id = ?
        """,
        (returned["garment_id"],),
    )
    assert cursor.fetchone() == (0, source_garment_id)
    cursor.execute(
        "SELECT COUNT(*) FROM fabric_blocks_inventory WHERE garment_id = ?",
        (returned["garment_id"],),
    )
    assert cursor.fetchone()[0] == source_block_count
    cursor.execute(
        """
        SELECT pt.name, SUM(pgi.amount)
        FROM processes_garments_inventory pgi
        JOIN process_types pt ON pt.id = pgi.process_id
        WHERE pgi.garment_id = ?
        GROUP BY pt.name
        """,
        (returned["garment_id"],),
    )
    garment_processes = dict(cursor.fetchall())
    assert garment_processes["sewing"] == pytest.approx(0.0042)
    assert garment_processes["washing"] == pytest.approx(0.10)
    assert garment_processes["steaming"] == pytest.approx(0.11)
    cursor.execute(
        """
        SELECT pt.name, SUM(pfbi.amount)
        FROM processes_fabric_blocks_inventory pfbi
        JOIN process_types pt ON pt.id = pfbi.process_id
        JOIN fabric_blocks_inventory fbi ON fbi.id = pfbi.fabric_block_id
        WHERE fbi.garment_id = ?
        GROUP BY pt.name
        """,
        (returned["garment_id"],),
    )
    block_processes = dict(cursor.fetchall())
    conn.close()
    assert block_processes == {}


def test_returned_garment_can_be_disassembled_into_fabric_inventory(seeded_db):
    source_garment_id = get_circular_scenario_options()["garments"][0]["id"]

    with TestClient(app) as client:
        client.app.state.wiser_client = _mock_wiser_client()
        returned = client.post(
            "/garment-returns",
            json={"garment_id": source_garment_id, "damage_code": "small_hole"},
        ).json()
        returned_id = returned["garment_id"]

        queue = client.get("/returned-garments")
        alternatives = client.get(
            f"/returned-garments/{returned_id}/return-alternatives",
            params={
                "distance_km": 100,
                "use_higher_electricity_factor": True,
            },
        )
        disassembled = client.post(
            f"/returned-garments/{returned_id}/disassemble"
        )
        queue_after = client.get("/returned-garments")
        available_blocks = client.get("/fabric-blocks")
        repeated = client.post(
            f"/returned-garments/{returned_id}/disassemble"
        )

    assert queue.status_code == 200
    assert queue.json()[0]["id"] == returned_id
    assert queue.json()[0]["fabric_block_count"] == returned["fabric_block_count"]
    assert queue.json()[0]["damage_code"] == "small_hole"
    assert alternatives.status_code == 200
    assert alternatives.json()["garment"]["id"] == returned_id
    assert alternatives.json()["return"]["whole_garment"]["components"]
    assert alternatives.json()["return"]["fabric_blocks"]["components"]
    assert alternatives.json()["calculation"]["electricity_mode"] == "higher_factor"
    assert disassembled.status_code == 200
    assert disassembled.json()["fabric_block_ids"] == returned["fabric_block_ids"]
    assert disassembled.json()["fabric_block_count"] == returned["fabric_block_count"]
    assert returned_id not in {garment["id"] for garment in queue_after.json()}
    assert set(returned["fabric_block_ids"]).issubset(
        {block["id"] for block in available_blocks.json()}
    )
    assert repeated.status_code == 409

    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT disassembled FROM garments_inventory WHERE id = ?",
        (returned_id,),
    )
    assert cursor.fetchone() == (1,)
    cursor.execute(
        "SELECT COUNT(*) FROM fabric_blocks_inventory "
        "WHERE id IN ({}) AND garment_id IS NULL".format(
            ",".join("?" for _ in returned["fabric_block_ids"])
        ),
        returned["fabric_block_ids"],
    )
    assert cursor.fetchone()[0] == returned["fabric_block_count"]
    conn.close()


def test_returned_garment_shop_offer_uses_only_preparation_co2(seeded_db):
    source_garment_id = get_circular_scenario_options()["garments"][0]["id"]
    conn = sqlite3.connect("ceis_backend.db")
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT gi.type_id, gt.price_chf
        FROM garments_inventory gi
        JOIN garment_types gt ON gt.id = gi.type_id
        WHERE gi.id = ?
        """,
        (source_garment_id,),
    )
    garment_type_id, base_price = cursor.fetchone()
    cursor.execute(
        """
        SELECT material_id FROM garment_recipe_materials
        WHERE garment_type = ? ORDER BY material_id LIMIT 1
        """,
        (garment_type_id,),
    )
    material_id = cursor.fetchone()[0]
    conn.close()

    with TestClient(app) as client:
        client.app.state.wiser_client = _mock_wiser_client()
        created = client.post(
            "/garment-returns",
            json={"garment_id": source_garment_id, "damage_code": "small_hole"},
        ).json()
        returned_id = created["garment_id"]

        offers = client.get(
            f"/garment-types/{garment_type_id}/returned-garments"
        ).json()
        comparison_response = client.get(
            f"/garment-types/{garment_type_id}/returned-garments/"
            f"{returned_id}/co2-comparison?material_id={material_id}"
        )

        # The regular order must not silently consume the discounted return.
        regular_order = client.post(
            "/orders",
            json={"garment_type_id": garment_type_id, "material_id": material_id},
        ).json()
        returned_order = client.post(
            "/orders",
            json={
                "garment_type_id": garment_type_id,
                "material_id": material_id,
                "garment_inventory_id": returned_id,
            },
        )

    assert offers[0]["id"] == returned_id
    assert offers[0]["fabric_emission_co2eq"] == 0
    assert offers[0]["price_chf"] == pytest.approx(offers[0]["base_price_chf"] * 0.5)
    assert created["price_chf"] == pytest.approx(base_price * 0.5)
    assert comparison_response.status_code == 200
    comparison = comparison_response.json()
    assert comparison["fabric_is_second_life"] is True
    assert comparison["fabric_emission_co2eq"] == 0
    assert comparison["returned_total_co2eq"] == pytest.approx(
        sum(step["emission"] for step in comparison["preparation_processes"])
    )
    assert comparison["returned_total_co2eq"] > 0
    assert comparison["new_total_co2eq"] > comparison["returned_total_co2eq"]
    assert {step["process"] for step in comparison["preparation_processes"]} == {
        "sewing",
        "washing",
        "steaming",
    }
    assert regular_order["garment_inventory_id"] != returned_id
    assert returned_order.status_code == 201
    assert returned_order.json()["is_returned"] is True
    assert returned_order.json()["discount_percent"] == 50


def test_mock_repair_amounts_are_scaled_to_garment_assembly():
    expected_sewing_amounts = {
        "small_hole": 0.0042,
        "seam": 0.0105,
        "tear": 0.021,
        "burn": 0.042,
    }

    for damage_code, expected_amount in expected_sewing_amounts.items():
        requirement = DAMAGE_PROFILE_BY_CODE[damage_code].repair_processes[0]
        assert requirement.name == "sewing"
        assert requirement.amount == pytest.approx(expected_amount)


def test_every_returnable_damage_adds_washing_and_steaming_once():
    for damage_code, profile in DAMAGE_PROFILE_BY_CODE.items():
        if not profile.repair_available or not profile.whole_garment_available:
            continue

        process_names = [
            process["name"]
            for process in get_return_inventory_processes(damage_code)
        ]

        assert process_names.count("washing") == 1
        assert process_names.count("steaming") == 1


def test_repair_process_is_shared_but_transport_differs(seeded_db):
    garment_id = get_circular_scenario_options()["garments"][0]["id"]

    payload = calculate_circular_scenarios(
        garment_id=garment_id,
        distance_km=100,
        damage_code="small_hole",
        wiser_client=_mock_wiser_client(),
    )

    self_repair = payload["repair"]["self_repair"]
    professional = payload["repair"]["professional_repair"]
    new_garment = payload["repair"]["new_garment"]

    assert self_repair["shared_repair_co2eq"] == pytest.approx(
        professional["shared_repair_co2eq"]
    )
    assert self_repair["transport"]["legs"] == 1
    assert professional["transport"]["legs"] == 2
    assert (
        self_repair["transport"]["weight_kg"]
        < professional["transport"]["weight_kg"]
    )
    assert new_garment["transport"]["legs"] == 1
    assert new_garment["transport"]["weight_kg"] == pytest.approx(
        payload["garment"]["weight_kg"]
    )
    assert new_garment["total_co2eq"] == pytest.approx(
        new_garment["production_co2eq"] + new_garment["transport"]["co2eq"]
    )
    assert any(
        component["name"] == "Transport"
        for component in new_garment["components"]
    )
    assert self_repair["saving_percent"] == pytest.approx(
        self_repair["saving_co2eq"] / new_garment["total_co2eq"] * 100,
        abs=0.1,
    )
    assert professional["saving_percent"] == pytest.approx(
        professional["saving_co2eq"] / new_garment["total_co2eq"] * 100,
        abs=0.1,
    )
    assert new_garment["saving_percent"] == 0.0
    assert payload["return"]["whole_garment"]["available"] is True
    assert {
        detail["process"]
        for detail in payload["return"]["whole_garment"]["preparation"][
            "details"
        ]
    } == {"washing", "steaming"}
    assert payload["return"]["fabric_blocks"]["available"] is True
    assert "recommendation" not in payload


def test_higher_electricity_factor_mode_changes_page_calculations(seeded_db):
    garment_id = get_circular_scenario_options()["garments"][0]["id"]

    current = calculate_circular_scenarios(
        garment_id,
        100,
        "small_hole",
        _mock_wiser_client(),
    )
    higher_factor = calculate_circular_scenarios(
        garment_id,
        100,
        "small_hole",
        _mock_wiser_client(),
        use_higher_electricity_factor=True,
    )

    assert current["calculation"] == {
        "electricity_mode": "current",
        "electricity_activity_id": 2660,
        "electricity_emission_factor": None,
    }
    assert higher_factor["calculation"] == {
        "electricity_mode": "higher_factor",
        "electricity_activity_id": 6566,
        "electricity_emission_factor": 1.2525767471944982,
    }
    assert higher_factor["repair"]["self_repair"][
        "shared_repair_co2eq"
    ] > current["repair"]["self_repair"]["shared_repair_co2eq"]
    assert {
        detail["activity_id"]
        for detail in higher_factor["repair"]["new_garment"]["assembly_processes"]
    } == {6566}
    assert {
        detail["activity_id"]
        for detail in higher_factor["return"]["fabric_blocks"]["preparation"][
            "details"
        ]
    } == {6566}


def test_higher_electricity_factor_mode_requests_configured_activity(seeded_db):
    garment_id = get_circular_scenario_options()["garments"][0]["id"]
    wiser_client = _mock_wiser_client()

    calculate_circular_scenarios(
        garment_id,
        100,
        "small_hole",
        wiser_client,
        use_higher_electricity_factor=True,
    )

    assert any(
        call.args[0] == 6566
        for call in wiser_client.get_emission_per_unit.call_args_list
    )


def test_chart_components_reconcile_with_scenario_totals(seeded_db):
    garment_id = get_circular_scenario_options()["garments"][0]["id"]
    payload = calculate_circular_scenarios(
        garment_id=garment_id,
        distance_km=100,
        damage_code="burn",
        wiser_client=_mock_wiser_client(),
    )

    scenarios = [
        payload["repair"]["self_repair"],
        payload["repair"]["professional_repair"],
        payload["repair"]["new_garment"],
        payload["return"]["whole_garment"],
        payload["return"]["fabric_blocks"],
    ]
    for scenario in scenarios:
        assert _component_total(scenario) == pytest.approx(
            scenario["total_co2eq"], abs=1e-5
        )

    whole_garment = payload["return"]["whole_garment"]
    assert all(
        component["name"] != "Transport"
        for component in whole_garment["reference_components"]
    )
    assert sum(
        component["co2eq"]
        for component in whole_garment["reference_components"]
    ) == pytest.approx(whole_garment["avoided_new_garment_co2eq"], abs=1e-5)
    assert whole_garment["avoided_new_garment_co2eq"] == pytest.approx(
        payload["repair"]["new_garment"]["production_co2eq"], abs=1e-5
    )

    fabric_blocks = payload["return"]["fabric_blocks"]
    assert sum(
        component["co2eq"]
        for component in fabric_blocks["reference_components"]
    ) == pytest.approx(fabric_blocks["recoverable_material_co2eq"], abs=1e-5)


def test_block_recovery_uses_damage_block_loss_assumption(seeded_db):
    garment_id = get_circular_scenario_options()["garments"][0]["id"]

    small_hole = calculate_circular_scenarios(
        garment_id,
        50,
        "small_hole",
        _mock_wiser_client(),
    )
    burn = calculate_circular_scenarios(
        garment_id,
        50,
        "burn",
        _mock_wiser_client(),
    )

    assert (
        burn["return"]["fabric_blocks"]["recoverable_block_count"]
        == small_hole["return"]["fabric_blocks"]["recoverable_block_count"] - 1
    )
    assert (
        burn["return"]["fabric_blocks"]["recoverable_material_co2eq"]
        < small_hole["return"]["fabric_blocks"]["recoverable_material_co2eq"]
    )
