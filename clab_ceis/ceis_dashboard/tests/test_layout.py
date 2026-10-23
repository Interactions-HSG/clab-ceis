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
    get_dashboard_layout,
)
from pages.home import get_index_layout
from pages.order_table import (
    _return_alternatives_chart,
    render_return_alternative_details,
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


def test_homepage_shows_pending_repairs_below_fabric_block_form():
    with (
        patch("pages.home.fetch_garment_types", return_value=[]),
        patch("pages.home.fetch_orders", return_value=[]),
        patch("pages.home.fetch_returned_garments", return_value=[]),
        patch(
            "pages.home.fetch_repairs",
            return_value=[
            {
                "id": 3,
                "garment": "Basic Crop Top",
                "garment_id": 7,
                "action_label": "Prepare self-repair kit",
                "damage_code": "small_hole",
                "status": "pending",
                "created_at": "2026-10-21 12:00:00",
            }
            ],
        ),
    ):
        layout = get_index_layout()
    text = str(layout)

    assert "Pending Repair Actions" in text
    assert "repairs-table" in text
    assert "Prepare self-repair kit" in text
    assert text.index("Add Second-hand Fabric Blocks to inventory") < text.index(
        "Pending Repair Actions"
    )
    assert "Pending Repair Actions" not in str(get_dashboard_layout())


def test_homepage_shows_orders_at_top_with_ship_action():
    with (
        patch("pages.home.fetch_garment_types", return_value=[]),
        patch("pages.home.fetch_repairs", return_value=[]),
        patch(
            "pages.home.fetch_returned_garments",
            return_value=[
                {
                    "id": 18,
                    "returned_from_garment_id": 7,
                    "garment": "Returned coat",
                    "fabric_block_count": 4,
                    "damage_code": "small_hole",
                    "status": "Returned",
                }
            ],
        ),
        patch(
            "pages.home.fetch_orders",
            return_value=[
                {
                    "id": 12,
                    "garment": "Made coat",
                    "material": "new wool",
                    "fulfillment_type": "production",
                    "status": "Production requested",
                    "created_at": "2026-10-21 12:00:00",
                }
            ],
        ),
    ):
        layout = get_index_layout()
    text = str(layout)

    assert "Orders" in text
    assert "orders-card" in text
    assert "orders-table-container" in text
    assert "Made coat" in text
    assert "ship-order" in text
    assert "Pre-loved Garments" in text
    assert "returned-garments-card" in text
    assert "Pre-loved" in text
    assert "Returned coat" in text
    assert "disassemble-returned-garment" in text
    assert "view-return-alternatives" in text
    assert "returned-alternatives-distance" in text
    assert "returned-alternatives-higher-electricity-factor" in text
    assert "Use higher electricity emission factor" in text
    assert text.index("Orders") < text.index("Second-hand Fabric Block Inventory")
    assert text.index("Orders") < text.index("Pre-loved Garments")
    assert text.index("Pre-loved Garments") < text.index(
        "Second-hand Fabric Block Inventory"
    )


def test_return_alternative_details_match_shop_chart_structure():
    scenario = {
        "components": [{"name": "Transport", "co2eq": 0.2}],
        "reference_components": [
            {"name": "Material production avoided", "co2eq": 1.4}
        ],
    }
    layout = render_return_alternative_details(
        {
            "garment": {
                "id": 18,
                "name": "Returned coat",
                "fabric_block_count": 4,
            },
            "damage": {"label": "Small hole"},
            "return": {
                "whole_garment": scenario,
                "fabric_blocks": scenario,
            },
            "calculation": {"electricity_mode": "higher_factor"},
        }
    )
    text = str(layout)

    assert "dashboard-return-component-chart" in text
    assert "Return alternatives: impact (+) and CO2 saved (-)" in text
    assert "Reuse whole garment" in text
    assert "Recover fabric blocks" in text
    assert "Saved: Material production avoided" in text
    assert "Higher electricity factor" in text

    figure = _return_alternatives_chart(
        {
            "return": {
                "whole_garment": scenario,
                "fabric_blocks": scenario,
            }
        }
    )
    traces = {trace.name: trace for trace in figure.data}
    assert traces["Transport"].marker.color == "#d45d3a"
    assert traces["Saved: Material production avoided"].marker.color == "#e3a928"
    assert traces["Saved: Material production avoided"].marker.pattern.shape == "/"
    assert figure.layout.colorway[0] == "#1f6a52"


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
