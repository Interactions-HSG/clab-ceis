from unittest.mock import patch

from dash import Dash

from main import CeisMonitor
from pages.flow import CeStages, get_flow_chart_data, get_supply_chain_elements
from pages.ui import page_hero


def test_app_shell_does_not_render_global_home_link():
    with (
        patch("pages.home.fetch_garment_types", return_value=[]),
        patch("ceis_callbacks.get_callbacks"),
    ):
        monitor = CeisMonitor(Dash(__name__))

    children = list(monitor.layout.children)

    assert children[1].id == "page-content"
    assert "page-home-link" not in str(monitor.layout)


def test_page_hero_home_link_is_opt_in_for_subpages():
    home_hero = page_hero("Operations", "Welcome", "Intro")
    subpage_hero = page_hero("Strategy", "Board", "Intro", show_home=True)

    assert "page-home-link" not in str(home_hero)
    assert "page-home-link" in str(subpage_hero)
    assert "page-hero-with-action" in str(subpage_hero)


def test_product_lifecycle_uses_top_to_bottom_flow():
    elements = get_flow_chart_data()["elements"]
    node_positions = {
        element["data"]["label"]: element["position"]
        for element in elements
        if "position" in element
    }

    assert (
        node_positions[CeStages.Extraction.name]["y"]
        < node_positions[CeStages.Production.name]["y"]
    )
    assert (
        node_positions[CeStages.Production.name]["y"]
        < node_positions[CeStages.Use.name]["y"]
    )
    assert (
        node_positions[CeStages.Use.name]["y"]
        < node_positions[CeStages.Waste.name]["y"]
    )


def test_value_chain_folds_repair_shops_into_garment_manufacturer_step():
    elements = get_supply_chain_elements(
        {
            "nodes": [
                {
                    "id": 1,
                    "company": "Finisher A",
                    "role": "finishing",
                    "role_group": "finishing",
                    "location": "A",
                },
                {
                    "id": 2,
                    "company": "Finisher B",
                    "role": "finishing",
                    "role_group": "finishing",
                    "location": "B",
                },
                {
                    "id": 3,
                    "company": "Repair A",
                    "role": "repair",
                    "role_group": "repair",
                    "location": "C",
                },
                {
                    "id": 4,
                    "company": "Repair B",
                    "role": "repair",
                    "role_group": "repair",
                    "location": "D",
                },
            ],
            "edges": [],
            "material_nodes": [],
            "material_edges": [],
        }
    )
    nodes_by_id = {
        element["data"]["id"]: element
        for element in elements
        if "position" in element
    }
    edges_by_id = {
        element["data"]["id"]: element
        for element in elements
        if "source" in element.get("data", {})
    }

    assert "value-chain-repair" not in nodes_by_id
    assert "2 repair partners" in nodes_by_id["value-chain-garment"]["data"]["label"]
    assert edges_by_id["value-chain-customer-to-service"]["data"]["target"] == (
        "value-chain-service"
    )
    assert edges_by_id["value-chain-customer-to-garment"]["data"]["target"] == (
        "value-chain-garment"
    )
    assert edges_by_id["value-chain-customer-to-service"]["data"]["label"] == "repair"
    assert edges_by_id["value-chain-customer-to-garment"]["data"]["label"] == (
        "repair / remanufacture"
    )
    assert edges_by_id["value-chain-customer-self-repair"]["data"]["source"] == (
        "value-chain-customer"
    )
    assert edges_by_id["value-chain-customer-self-repair"]["data"]["target"] == (
        "value-chain-customer"
    )
    assert (
        edges_by_id["value-chain-customer-self-repair"]["data"]["label"]
        == "self-repair"
    )
    assert nodes_by_id["value-chain-garment"]["data"]["manufacturer_ids"] == [3, 4]


def test_value_chain_uses_butterfly_role_flow():
    elements = get_supply_chain_elements(
        {
            "nodes": [
                {
                    "id": 1,
                    "company": "Fabric A",
                    "role": "fabric manufacturer",
                    "role_group": "fabric",
                    "location": "A",
                },
                {
                    "id": 2,
                    "company": "Garment A",
                    "role": "garment manufacturer",
                    "role_group": "garment",
                    "location": "B",
                },
                {
                    "id": 3,
                    "company": "Finisher A",
                    "role": "finishing",
                    "role_group": "finishing",
                    "location": "C",
                },
                {
                    "id": 4,
                    "company": "Repair A",
                    "role": "repair",
                    "role_group": "repair",
                    "location": "D",
                },
            ],
            "edges": [],
            "material_nodes": [{"id": 5, "name": "cotton"}],
            "material_edges": [],
        }
    )
    node_positions = {
        element["data"]["id"]: element["position"]
        for element in elements
        if "position" in element
    }
    nodes_by_id = {
        element["data"]["id"]: element
        for element in elements
        if "position" in element
    }
    edges_by_id = {
        element["data"]["id"]: element
        for element in elements
        if "source" in element.get("data", {})
    }

    assert (
        node_positions["value-chain-materials"]["y"]
        < node_positions["value-chain-fabric"]["y"]
    )
    assert (
        node_positions["value-chain-fabric"]["y"]
        < node_positions["value-chain-garment"]["y"]
    )
    assert (
        node_positions["value-chain-garment"]["y"]
        < node_positions["value-chain-service"]["y"]
    )
    assert (
        node_positions["value-chain-service"]["y"]
        < node_positions["value-chain-customer"]["y"]
    )
    assert (
        edges_by_id["value-chain-service-to-customer"]["data"]["target"]
        == "value-chain-customer"
    )
    assert nodes_by_id["value-chain-customer"]["data"]["label"] == "Customer"
    assert (
        node_positions["deliver-label"]["x"]
        > node_positions["value-chain-service"]["x"]
    )
    assert (
        edges_by_id["value-chain-fabric-to-garment"]["data"]["label"]
        == "raw fabrics"
    )
    assert (
        edges_by_id["value-chain-garment-to-service"]["data"]["label"]
        == "raw garments"
    )
    assert edges_by_id["value-chain-service-to-customer"]["data"]["label"] == "deliver"
    assert edges_by_id["value-chain-material-to-fabric"]["classes"] == "feedstock-leg"
    assert edges_by_id["value-chain-material-to-fabric"]["data"][
        "material_manufacturer_distance_ids"
    ] == []
    assert edges_by_id["value-chain-customer-to-material"]["data"]["target"] == (
        "value-chain-materials"
    )
    assert edges_by_id["value-chain-customer-to-fabric"]["data"]["target"] == (
        "value-chain-fabric"
    )
    assert edges_by_id["value-chain-customer-to-garment"]["data"]["target"] == (
        "value-chain-garment"
    )
    assert edges_by_id["value-chain-customer-to-service"]["data"]["target"] == (
        "value-chain-service"
    )
    assert edges_by_id["value-chain-customer-to-service"]["data"]["label"] == "repair"
    assert edges_by_id["value-chain-customer-to-garment"]["data"]["label"] == (
        "repair / remanufacture"
    )
    assert (
        edges_by_id["value-chain-customer-self-repair"]["data"]["label"]
        == "self-repair"
    )

    step_node_ids = {
        element["data"]["id"]
        for element in elements
        if "position" in element
        and element["data"]["id"].startswith("value-chain")
    }
    assert step_node_ids == {
        "value-chain-materials",
        "value-chain-fabric",
        "value-chain-garment",
        "value-chain-service",
        "value-chain-customer",
    }
