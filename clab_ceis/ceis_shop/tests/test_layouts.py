from __future__ import annotations

from unittest.mock import Mock, patch

from ceis_shop.layouts.scenarios import scenarios_page
from ceis_shop.layouts.garment import garment_page, render_co2_content
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
        garment_types_response.json.return_value = [
            {"id": 1, "name": "Basic Trousers", "price_chf": 100.0}
        ]

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
    assert "Base price: CHF 100.00" in text
    assert "garment-material-dropdown" in text
    assert "Back to Home" in text


def test_garment_page_auto_uses_single_material_for_co2_without_blocking_layout():
    with patch("ceis_shop.layouts.garment.requests.get") as mocked_get:
        garment_types_response = Mock()
        garment_types_response.raise_for_status.return_value = None
        garment_types_response.json.return_value = [
            {"id": 1, "name": "Basic Trousers", "price_chf": 100.0}
        ]

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


def test_render_co2_content_shows_alternatives_and_capped_discount():
    layout = render_co2_content(
        "hemp",
        {
            "fabric_blocks": {
                "total_emission": 2.0,
                "details": [
                    {
                        "fabric_block": "80x64",
                        "material": "hemp",
                        "alternative": {"id": 11, "quality": 80, "material": "cotton"},
                    },
                    {
                        "fabric_block": "64x40",
                        "material": "cotton",
                        "alternative": {"id": 12, "quality": 95, "material": "linen"},
                    },
                    {
                        "fabric_block": "32x32",
                        "material": "linen",
                        "alternative": {"id": 13, "quality": 70, "material": "wool"},
                    },
                    {
                        "fabric_block": "16x16",
                        "material": "silk",
                        "alternative": {"id": 14, "quality": 100, "material": "silk"},
                    },
                ],
            },
            "processes": {"total_emission": 1.0, "details": []},
        },
        base_price_chf=100.0,
    )

    text = str(layout)

    assert (
        "80x64 can be replaced by a second-life cotton block with quality 80 %" in text
    )
    assert (
        "64x40 can be replaced by a second-life linen block with quality 95 %" in text
    )
    assert "32x32 can be replaced by a second-life wool block with quality 70 %" in text
    assert "16x16 can be replaced" not in text
    assert "Price: CHF 40.00 (60% discount from CHF 100.00)" in text
