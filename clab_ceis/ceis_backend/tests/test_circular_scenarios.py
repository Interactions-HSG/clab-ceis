from unittest.mock import MagicMock

import pytest

from ceis_backend.circular_scenarios import (
    DAMAGE_PROFILE_BY_CODE,
    calculate_circular_scenarios,
    get_circular_scenario_options,
)
from ceis_backend.db_init import init_sqlite_db


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
    assert sum(
        component["co2eq"]
        for component in whole_garment["reference_components"]
    ) == pytest.approx(whole_garment["avoided_new_garment_co2eq"], abs=1e-5)

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
