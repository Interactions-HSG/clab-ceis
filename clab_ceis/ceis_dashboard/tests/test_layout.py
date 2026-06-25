from unittest.mock import patch

from dash import Dash

from main import CeisMonitor
from pages.flow import get_supply_chain_elements
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


def test_supply_chain_places_repair_shops_below_finishing_actors():
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
    node_positions = {
        element["data"]["label"]: element["position"]
        for element in elements
        if "position" in element
    }

    finishing_y = [
        node_positions["Finisher A"]["y"],
        node_positions["Finisher B"]["y"],
    ]
    repair_y = [
        node_positions["Repair A"]["y"],
        node_positions["Repair B"]["y"],
    ]

    assert min(repair_y) > max(finishing_y)


def test_supply_chain_uses_top_to_bottom_role_flow():
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
        element["data"]["label"]: element["position"]
        for element in elements
        if "position" in element
    }

    assert node_positions["Cotton\n0 km upstream"]["y"] < node_positions["Fabric A"]["y"]
    assert node_positions["Fabric A"]["y"] < node_positions["Garment A"]["y"]
    assert node_positions["Garment A"]["y"] < node_positions["Finisher A"]["y"]
    assert node_positions["Finisher A"]["y"] < node_positions["Repair A"]["y"]
