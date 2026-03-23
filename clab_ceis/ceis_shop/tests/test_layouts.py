from __future__ import annotations

from unittest.mock import Mock, patch

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


def test_garment_page_contains_recipe_and_co2_sections():
    with patch("ceis_shop.layouts.garment.requests.get") as mocked_get:
        garment_types_response = Mock()
        garment_types_response.raise_for_status.return_value = None
        garment_types_response.json.return_value = [{"id": 1, "name": "Basic Trousers"}]

        materials_response = Mock()
        materials_response.raise_for_status.return_value = None
        materials_response.json.return_value = [{"id": 1, "name": "hemp"}]

        co2_response = Mock()
        co2_response.raise_for_status.return_value = None
        co2_response.json.return_value = {
            "fabric_blocks": {
                "details": [
                    {"fabric_block": "100x64"},
                    {"fabric_block": "100x64"},
                    {"fabric_block": "64x40"},
                ],
                "total_emission": 1.2,
            },
            "processes": {
                "details": [{"process": "sewing", "duration": 0.042}],
                "total_emission": 0.4,
            },
        }

        mocked_get.side_effect = [
            garment_types_response,
            materials_response,
            co2_response,
        ]

        layout = garment_page(1)
        text = str(layout)

    assert "Recipe" in text
    assert "CO2 Emissions" in text
    assert "100x64 x 2" in text
    assert "Select a material to view total CO2." in text
    assert "garment-material-dropdown" in text
    assert "Back to Home" in text
