from __future__ import annotations

from unittest.mock import Mock, patch

from ceis_shop.layouts.scenarios import scenarios_page
from ceis_shop.layouts.garment import garment_page, render_co2_content
from ceis_shop.layouts.home import home_page
from ceis_shop.main import app as shop_app


def test_app_shell_does_not_render_global_home_link():
    children = list(shop_app.layout.children)

    assert children[1].id == "page-content"
    assert "page-home-link" not in str(shop_app.layout)
    assert "shop-home-button" not in str(shop_app.layout)


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
    assert "page-home-link" not in text
    assert "shop-home-button" not in text


def test_scenarios_page_contains_scenarios_section():
    layout = scenarios_page()
    text = str(layout)

    assert "End of Life Options" in text
    assert "customer-repair-content" in text
    assert "page-home-link" in text
    assert "shop-home-button" in text
    assert "Button" in text
    assert "Back to Home" not in text


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
    assert "garment-material-dropdown" in text
    assert "page-home-link" in text
    assert "shop-home-button" in text
    assert "Button" in text
    assert "Back to Home" not in text


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
                        "emission": 1.1,
                        "alternative": {
                            "id": 11,
                            "quality": 80,
                            "material": "cotton",
                            "emission": 0.2,
                        },
                    },
                    {
                        "fabric_block": "64x40",
                        "material": "cotton",
                        "emission": 0.5,
                        "alternative": {
                            "id": 12,
                            "quality": 95,
                            "material": "linen",
                            "emission": 0.15,
                        },
                    },
                    {
                        "fabric_block": "32x32",
                        "material": "linen",
                        "emission": 0.4,
                        "alternative": {
                            "id": 13,
                            "quality": 70,
                            "material": "wool",
                            "emission": 0.1,
                        },
                    },
                    {
                        "fabric_block": "16x16",
                        "material": "silk",
                        "emission": 0.0,
                        "alternative": {
                            "id": 14,
                            "quality": 100,
                            "material": "silk",
                            "emission": 0.0,
                        },
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
    assert (
        "Choosing the available alternative fabric blocks would reduce this to "
        "1.450 kg CO2eq, saving 1.550 kg CO2eq." in text
    )
    assert "Price: CHF 40.00 (60% discount from CHF 100.00)" in text


def test_render_co2_content_shows_no_savings_message_without_replacements():
    layout = render_co2_content(
        "hemp",
        {
            "fabric_blocks": {
                "total_emission": 2.0,
                "details": [
                    {
                        "fabric_block": "80x64",
                        "material": "hemp",
                        "emission": 2.0,
                        "alternative": {},
                    }
                ],
            },
            "processes": {"total_emission": 1.0, "details": []},
        },
        base_price_chf=100.0,
    )

    text = str(layout)

    assert "No CO2-saving fabric block alternatives available." in text
