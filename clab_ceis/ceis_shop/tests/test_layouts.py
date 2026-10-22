from __future__ import annotations

from unittest.mock import Mock, patch

from ceis_shop.layouts.scenarios import (
    _component_bar_chart,
    _saved_components,
    repair_return_page,
    render_scenario_explorer,
    render_scenario_results,
    scenarios_page,
)
from ceis_shop.layouts.garment import (
    _render_returned_garment_offer,
    _format_condition,
    garment_page,
    render_co2_content,
    render_returned_garment_comparison,
)
from ceis_shop.layouts.home import home_page
from ceis_shop.main import app as shop_app
from ceis_shop.shop_callbacks import _remove_returned_garment_option


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

    assert "Choose clothes with a life beyond the first wear." in text
    assert "The collection" in text
    assert "/garment/1" in text
    assert "/garment/2" in text
    assert "/scenarios" in text
    assert "/repair-return" in text
    assert "page-home-link" not in text
    assert "shop-home-button" not in text


def test_home_page_hides_products_without_pictures():
    with patch("ceis_shop.layouts.home.requests.get") as mocked_get:
        mocked_response = Mock()
        mocked_response.json.return_value = [
            {"id": 1, "name": "Basic Trousers"},
            {"id": 99, "name": "Garment Without A Picture"},
        ]
        mocked_response.raise_for_status.return_value = None
        mocked_get.return_value = mocked_response

        text = str(home_page())

    assert "/garment/1" in text
    assert "Basic Trousers" in text
    assert "/garment/99" not in text
    assert "Garment Without A Picture" not in text


def test_home_page_shows_second_collection_before_first_collection():
    with patch("ceis_shop.layouts.home.requests.get") as mocked_get:
        mocked_response = Mock()
        mocked_response.json.return_value = [
            {"id": 1, "name": "Orka jacket"},
            {"id": 2, "name": "Wrap Skirt"},
            {"id": 3, "name": "Mangata Dress"},
            {"id": 4, "name": "Basic Trousers"},
        ]
        mocked_response.raise_for_status.return_value = None
        mocked_get.return_value = mocked_response

        text = str(home_page())

    assert text.index("Second collection") < text.index("First collection")
    assert text.index("Basic Trousers") < text.index("Wrap Skirt")
    assert text.index("Wrap Skirt") < text.index("Mangata Dress")
    assert text.index("Mangata Dress") < text.index("Orka jacket")


def test_scenarios_page_contains_scenarios_section():
    layout = scenarios_page()
    text = str(layout)

    assert "Understand the impact of what comes next" in text
    assert "Production in Bucharest" in text
    assert "customer-repair-content" in text
    assert "page-home-link" in text
    assert "shop-home-button" in text
    assert "Link" in text
    assert "Back to Home" not in text


def test_repair_return_page_is_separate_from_end_of_cycle_page():
    layout = repair_return_page()
    text = str(layout)

    assert "Find the best next step for your garment" in text
    assert "customer-circular-content" in text
    assert "/repair-return" in text
    assert "Manufacturer: Bucharest" not in text


def test_scenario_explorer_uses_bought_garment_and_damage_options():
    layout = render_scenario_explorer(
        {
            "garments": [
                {"id": 7, "label": "Basic Crop Top · garment #7"},
            ],
            "damages": [
                {"code": "small_hole", "label": "Small hole or puncture"},
            ],
        }
    )
    text = str(layout)

    assert "circular-garment" in text
    assert "Your garment" in text
    assert "Bought garment" not in text
    assert "Basic Crop Top" in text
    assert "garment #7" not in text
    assert "circular-distance" in text
    assert "value=1000" in text
    assert "circular-damage" in text
    assert "Small hole or puncture" in text
    assert "circular-use-higher-electricity-factor" in text
    assert "Use higher electricity emission factor" in text
    assert "circular-garment-return-result" in text


def test_returned_garment_is_removed_from_scenario_selector():
    remaining, selected = _remove_returned_garment_option(
        [
            {"label": "Garment #8", "value": 8},
            {"label": "Garment #9", "value": 9},
        ],
        8,
    )

    assert remaining == [{"label": "Garment #9", "value": 9}]
    assert selected == 9


def test_returning_last_garment_clears_scenario_selector():
    remaining, selected = _remove_returned_garment_option(
        [{"label": "Garment #8", "value": 8}],
        8,
    )

    assert remaining == []
    assert selected is None


def test_scenario_results_show_alternatives_without_recommendation():
    scenario = {
        "available": True,
        "total_co2eq": 0.3,
        "saving_co2eq": 1.2,
        "saving_percent": 80.0,
        "components": [
            {"name": "Transport", "co2eq": 0.1},
            {"name": "Repair: sewing", "co2eq": 0.2},
        ],
        "reference_components": [
            {"name": "New material", "co2eq": 1.5},
        ],
    }
    layout = render_scenario_results(
        {
            "garment": {
                "id": 7,
                "name": "Basic Crop Top",
                "fabric_block_count": 4,
                "weight_kg": 0.2,
            },
            "damage": {
                "processes": [{"process": "sewing"}],
                "replacement_block_count": 1,
            },
            "repair": {
                "self_repair": scenario,
                "professional_repair": scenario,
                "new_garment": scenario,
            },
            "return": {
                "whole_garment": scenario,
                "fabric_blocks": scenario,
            },
            "assumptions": ["Mock assumption"],
        }
    )
    text = str(layout)

    assert "Self-repair" in text
    assert "Professional repair" in text
    assert "Order self-repair kit" in text
    assert "order-self-repair-kit" in text
    assert "Send for professional repair" in text
    assert "request-professional-repair" in text
    assert "circular-repair-order-result" in text
    assert "Return garment" in text
    assert "return-garment-button" in text
    assert "circular-garment-return-result" not in text
    assert "Expected CO2 saving" in text
    assert "1.200 kg CO2eq" in text
    assert (
        "Reusing this garment saves 1.200 kg CO2eq compared with buying a new one."
        in text
    )
    assert "Transport, repair, and preparation add 0.300 kg CO2eq." in text
    assert "Reuse whole garment" not in text
    assert "Recover fabric blocks" not in text
    assert text.index("Expected CO2 saving") < text.index("return-garment-button")
    assert "Pieces to replace: 1" in text
    assert "#7" not in text
    assert "View detailed bar charts" in text
    assert "circular-detailed-charts" in text
    assert "repair-component-chart" in text
    assert "return-component-chart" in text
    assert "Return alternative: CO2 needed (+) and CO2 saved (-)" in text
    assert "Saved: New material" in text
    assert "Calculation components" in text
    assert "80.0%" in text
    assert "Recommended" not in text


def test_component_bar_chart_lists_each_calculation_component():
    figure = _component_bar_chart(
        "Details",
        [
            (
                "Alternative A",
                [
                    {"name": "Transport", "co2eq": 0.1},
                    {"name": "Repair: sewing", "co2eq": 0.2},
                ],
            ),
            (
                "Alternative B",
                [
                    {"name": "Transport", "co2eq": 0.3},
                    {"name": "New material", "co2eq": 1.0},
                ],
            ),
        ],
    )

    traces = {trace.name: trace for trace in figure.data}
    assert list(traces) == ["Transport", "Repair: sewing", "New material"]
    assert list(traces["Transport"].y) == [0.1, 0.3]
    assert list(traces["Repair: sewing"].y) == [0.2, 0]
    assert list(traces["New material"].y) == [0, 1.0]
    assert figure.layout.barmode == "stack"
    assert figure.layout.hovermode == "closest"
    assert "%{x}" not in traces["Transport"].hovertemplate


def test_saved_components_are_negative_for_return_saving_chart():
    saved = _saved_components(
        [
            {"name": "New material", "co2eq": 1.5},
            {"name": "Transport", "co2eq": 0.1},
        ]
    )
    figure = _component_bar_chart(
        "Return details",
        [("Expected CO2 saving", saved)],
        barmode="relative",
    )

    assert saved == [
        {"name": "Saved: New material", "co2eq": -1.5},
        {"name": "Saved: Transport", "co2eq": -0.1},
    ]
    assert figure.layout.barmode == "relative"
    assert all(value <= 0 for trace in figure.data for value in trace.y)


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
            {"id": 1, "name": "hemp", "cost_per_sqm_chf": 5.04},
            {"id": 2, "name": "cotton", "cost_per_sqm_chf": 2.52},
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

    assert "Cut efficiently, built for longevity" in text
    assert "See your price and impact" in text
    assert "Select a material to view recipe details." not in text
    assert "Choose a material to reveal available second-life alternatives" in text
    assert "garment-material-dropdown" in text
    assert "garment-order-button" in text
    assert "garment-order-result" in text
    assert "page-home-link" in text
    assert "shop-home-button" in text
    assert "Link" in text
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
        materials_response.json.return_value = [
            {"id": 1, "name": "hemp", "cost_per_sqm_chf": 5.04}
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

    assert "Choose a material to reveal available second-life alternatives" in text
    assert "value=1" in text
    assert mocked_get.call_count == 4


def test_garment_page_shows_available_returned_garment_at_half_price():
    responses = []
    for payload in (
        [{"id": 1, "name": "Basic Trousers", "price_chf": 100.0}],
        [{"id": 1, "name": "hemp", "cost_per_sqm_chf": 5.04}],
        [{"fabric_block": "80x64", "amount": 2}],
        [
            {
                "id": 42,
                "garment": "Basic Trousers",
                "base_price_chf": 100.0,
                "price_chf": 50.0,
            }
        ],
    ):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        responses.append(response)

    with patch("ceis_shop.layouts.garment.requests.get", side_effect=responses):
        text = str(garment_page(1))

    assert "Give a returned garment its next life" in text
    assert "50% OFF" in text
    assert "CHF 50.00" in text
    assert "CHF 100.00" in text
    assert "no new fabric required" in text
    assert "#42" not in text
    assert "returned-garment-order-button" in text


def test_returned_garment_offer_only_shows_first_available_option():
    text = str(
        _render_returned_garment_offer(
            [
                {
                    "id": 42,
                    "garment": "Basic Trousers",
                    "base_price_chf": 100.0,
                    "price_chf": 50.0,
                },
                {
                    "id": 43,
                    "garment": "Basic Trousers backup",
                    "base_price_chf": 120.0,
                    "price_chf": 60.0,
                },
            ]
        )
    )

    assert "Second-life Basic Trousers" in text
    assert "Basic Trousers backup" not in text
    assert "value=42" in text
    assert "value=43" not in text


def test_returned_garment_comparison_explains_zero_fabric_emissions():
    text = str(
        render_returned_garment_comparison(
            {
                "returned_total_co2eq": 0.14,
                "new_total_co2eq": 2.0,
                "saving_co2eq": 1.86,
                "saving_percent": 93.0,
                "preparation_processes": [
                    {"process": "steaming", "emission": 0.138}
                ],
            }
        )
    )

    assert "Second-life garment" in text
    assert "0.140 kg CO2eq" in text
    assert "Equivalent new" in text
    assert "2.000 kg CO2eq" in text
    assert "preparation details" not in text.lower()
    assert "steaming" not in text


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
        material_cost_per_sqm_chf=5.04,
    )

    text = str(layout)

    assert "Second-life cotton" in text
    assert "very good condition" in text
    assert "Second-life linen" in text
    assert "excellent condition" in text
    assert "Second-life wool" in text
    assert "good condition" in text
    assert "with quality" not in text
    assert "Second-life silk" not in text
    assert "save 1.550 kg CO2eq" in text
    assert "SAVE 60%" in text
    assert "CHF 40.00" in text
    assert "CHF 100.00" in text
    assert "/m²" not in text
    assert "80x64" not in text
    assert "64x40" not in text


def test_format_condition_uses_clear_quality_bands():
    assert _format_condition(90) == "excellent condition"
    assert _format_condition(89.9) == "very good condition"
    assert _format_condition(75) == "very good condition"
    assert _format_condition(74.9) == "good condition"
    assert _format_condition(50) == "good condition"
    assert _format_condition(49.9) == "fair condition"


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

    assert "No second-life fabric available right now" in text
