from __future__ import annotations

from unittest.mock import Mock, patch

from ceis_shop.layouts.scenarios import scenarios_page
from ceis_shop.layouts.garment import garment_page
from ceis_shop.layouts.home import home_page


def test_home_page_contains_expected_links():
    with patch("ceis_shop.layouts.home.requests.get") as mocked_get:
        mocked_response = Mock()
        mocked_response.json.return_value = [
            {"id": 1, "name": "Basic Trousers"},
            {"id": 2, "name": "Full Trousers"},
        ]
        mocked_response.raise_for_status.return_value = None
        mocked_get.return_value = mocked_response

        layout = home_page()
        text = str(layout)

    assert "Welcome to Our Clothing Order Website" in text
    assert "/garment/1" in text
    assert "/garment/2" in text
    assert "/scenarios" in text


def test_scenarios_page_contains_scenarios_section():
    layout = scenarios_page()
    text = str(layout)

    assert "End of Life Options" in text
    assert "customer-repair-content" in text
    assert "Back to Home" in text


def test_garment_page_contains_recipe_and_co2_sections():
    with patch("ceis_shop.layouts.garment.requests.get") as mocked_get:
        garment_types_response = Mock()
        garment_types_response.raise_for_status.return_value = None
        garment_types_response.json.return_value = [{"id": 1, "name": "Basic Trousers"}]

        materials_response = Mock()
        materials_response.raise_for_status.return_value = None
        materials_response.json.return_value = [
            {"id": 1, "name": "hemp"},
            {"id": 2, "name": "cotton"},
        ]

        recipe_fabric_blocks_response = Mock()
        recipe_fabric_blocks_response.raise_for_status.return_value = None
        recipe_fabric_blocks_response.json.return_value = [
            {"fabric_block": "80x64", "amount": 2}
        ]

        mocked_get.side_effect = [
            garment_types_response,
            materials_response,
            recipe_fabric_blocks_response,
        ]

        layout = garment_page(1)
        text = str(layout)

    assert "Fabric Blocks" in text
    assert "CO2 Emissions" in text
    assert "Select a material to view recipe details." not in text
    assert "Select a material to view CO2 emissions." in text
    assert "garment-material-dropdown" in text
    assert "Back to Home" in text


def test_garment_page_auto_uses_single_material_for_co2_without_blocking_layout():
    with patch("ceis_shop.layouts.garment.requests.get") as mocked_get:
        garment_types_response = Mock()
        garment_types_response.raise_for_status.return_value = None
        garment_types_response.json.return_value = [{"id": 1, "name": "Basic Trousers"}]

        materials_response = Mock()
        materials_response.raise_for_status.return_value = None
        materials_response.json.return_value = [{"id": 1, "name": "hemp"}]

        recipe_fabric_blocks_response = Mock()
        recipe_fabric_blocks_response.raise_for_status.return_value = None
        recipe_fabric_blocks_response.json.return_value = [
            {"fabric_block": "80x64", "amount": 2}
        ]

        mocked_get.side_effect = [
            garment_types_response,
            materials_response,
            recipe_fabric_blocks_response,
        ]

        layout = garment_page(1)
        text = str(layout)

    assert "Select a material to view CO2 emissions." in text
    assert "value=1" in text
    assert mocked_get.call_count == 3
