from unittest.mock import patch

from dash import Dash

from main import CeisMonitor
from pages.flow import (
    CeStages,
    VALUE_CHAIN_BRAND_ID,
    VALUE_CHAIN_CUSTOMER_ID,
    VALUE_CHAIN_LOCAL_SERVICE_ID,
    VALUE_CHAIN_STEP_IDS,
    get_flow_chart_data,
    get_supply_chain_elements,
    get_supply_chain_stylesheet,
)
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


def test_value_chain_links_repair_shops_to_local_service_provider():
    elements = get_supply_chain_elements(
        {
            "nodes": [
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
    assert "2 partners" in nodes_by_id[VALUE_CHAIN_STEP_IDS["service"]]["data"][
        "label"
    ]
    assert "partners" not in nodes_by_id[VALUE_CHAIN_LOCAL_SERVICE_ID]["data"]["label"]
    assert nodes_by_id[VALUE_CHAIN_STEP_IDS["service"]]["data"]["manufacturer_ids"] == [
        3,
        4,
    ]
    assert nodes_by_id[VALUE_CHAIN_STEP_IDS["garment"]]["data"][
        "manufacturer_ids"
    ] == []
    assert edges_by_id["value-chain-customer-to-local-service"]["data"]["target"] == (
        VALUE_CHAIN_LOCAL_SERVICE_ID
    )
    assert (
        edges_by_id["value-chain-customer-to-local-service"]["data"]["label"]
        == "Repair"
    )
    assert "value-chain-local-service-to-customer" not in edges_by_id


def test_value_chain_matches_reference_actor_and_labeled_recovery_flow():
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
        < node_positions[VALUE_CHAIN_BRAND_ID]["y"]
    )
    assert (
        node_positions[VALUE_CHAIN_BRAND_ID]["y"]
        < node_positions[VALUE_CHAIN_CUSTOMER_ID]["y"]
    )
    assert (
        node_positions[VALUE_CHAIN_LOCAL_SERVICE_ID]["y"]
        == node_positions[VALUE_CHAIN_CUSTOMER_ID]["y"]
    )
    assert edges_by_id["value-chain-garment-to-brand"]["data"]["target"] == (
        VALUE_CHAIN_BRAND_ID
    )
    assert edges_by_id["value-chain-service-to-brand"]["data"]["target"] == (
        VALUE_CHAIN_BRAND_ID
    )
    assert edges_by_id["value-chain-brand-to-customer"]["data"]["target"] == (
        VALUE_CHAIN_CUSTOMER_ID
    )
    assert edges_by_id["value-chain-material-to-fabric"]["data"][
        "material_manufacturer_distance_ids"
    ] == []
    assert edges_by_id["value-chain-brand-to-material"]["data"]["target"] == (
        VALUE_CHAIN_STEP_IDS["material"]
    )
    assert (
        edges_by_id["value-chain-brand-to-material"]["data"]["label"]
        == "Fibre recycle"
    )
    assert edges_by_id["value-chain-brand-to-garment"]["data"]["target"] == (
        VALUE_CHAIN_STEP_IDS["garment"]
    )
    assert (
        edges_by_id["value-chain-brand-to-garment"]["data"]["label"]
        == "Remanufacture"
    )
    assert edges_by_id["value-chain-brand-to-service-repair"]["data"]["target"] == (
        VALUE_CHAIN_STEP_IDS["service"]
    )
    assert (
        edges_by_id["value-chain-brand-to-service-repair"]["data"]["label"]
        == "Repair"
    )
    assert (
        edges_by_id["value-chain-brand-to-service-reuse"]["data"]["label"]
        == "Reuse / redistribute"
    )
    assert (
        edges_by_id["value-chain-customer-to-brand"]["data"]["label"]
        == "Maintain / prolong"
    )

    actor_node_ids = {
        element["data"]["id"]
        for element in elements
        if "position" in element
    }
    assert actor_node_ids == {
        *VALUE_CHAIN_STEP_IDS.values(),
        VALUE_CHAIN_BRAND_ID,
        VALUE_CHAIN_LOCAL_SERVICE_ID,
        VALUE_CHAIN_CUSTOMER_ID,
    }
    assert all("process-node" not in element.get("classes", "") for element in elements)


def test_value_chain_recovery_routes_use_separate_lanes_and_horizontal_labels():
    styles_by_selector = {
        rule["selector"]: rule["style"] for rule in get_supply_chain_stylesheet()
    }

    assert styles_by_selector["edge"]["text-rotation"] == "none"
    local_service_style = styles_by_selector[".local-service-loop"]
    assert local_service_style["source-arrow-shape"] == "triangle"

    recovery_selectors = (
        ".repair-loop",
        ".reuse-loop",
        ".remanufacture-loop",
        ".recycle-loop",
    )
    lane_distances = []
    source_endpoints = []
    for selector in recovery_selectors:
        style = styles_by_selector[selector]
        distances = style["control-point-distances"].split()
        assert len(distances) == 2
        assert distances[0] == distances[1]
        lane_distances.append(distances[0])
        source_endpoints.append(style["source-endpoint"])

    assert len(set(lane_distances)) == len(recovery_selectors)
    assert len(set(source_endpoints)) == len(recovery_selectors)
