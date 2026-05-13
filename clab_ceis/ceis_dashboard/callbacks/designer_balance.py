from __future__ import annotations

from typing import Any, cast

from dash import Dash, Input, Output, html, dash_table
import dash_cytoscape as cyto

import ceis_data
from ceis_dashboard.callbacks.api import (
    fetch_designer_balance_options,
    fetch_designer_balance_scenario,
    fetch_materials_for_garment,
)


def _metric_card(title: str, value: str, subtitle: str):
    return html.Div(
        [
            html.Div(title, className="designer-balance-metric-title"),
            html.Div(value, className="designer-balance-metric-value"),
            html.Div(subtitle, className="designer-balance-metric-subtitle"),
        ],
        className="designer-balance-metric-card",
    )


def _format_currency(value: float | int | None) -> str:
    return f"CHF {float(value or 0):.2f}"


def _format_co2(value: float | int | None) -> str:
    return f"{float(value or 0):.3f} kg CO2eq"


def _format_days(value: float | int | None) -> str:
    return f"{float(value or 0):.2f} days"


def _build_supply_chain_graph(supply_chain: dict):
    actors = supply_chain.get("actors", [])
    legs = supply_chain.get("legs", [])
    if not actors:
        return html.Div("No supplier data available for this scenario.")

    positions = {
        "fabric": {"x": 120, "y": 165},
        "garment": {"x": 480, "y": 165},
        "finishing": {"x": 840, "y": 165},
    }

    elements = []
    for actor in actors:
        role_group = actor.get("role_group")
        elements.append(
            {
                "data": {
                    "id": role_group,
                    "label": (
                        f"{actor.get('company', 'Unknown')}\n"
                        f"{role_group.title()}\n"
                        f"Delay: {actor.get('delay_days', 0)} d"
                    ),
                },
                "position": positions.get(role_group, {"x": 0, "y": 0}),
            }
        )

    for index, leg in enumerate(legs):
        elements.append(
            {
                "data": {
                    "id": f"leg-{index}",
                    "source": leg.get("source_role_group"),
                    "target": leg.get("destination_role_group"),
                    "label": (
                        f"{leg.get('distance_km', 0)} km | "
                        f"{leg.get('delay_days', 0)} d"
                    ),
                }
            }
        )

    return cyto.Cytoscape(
        id="designer-balance-supply-chain-graph",
        layout={"name": "preset"},
        elements=elements,
        autolock=True,
        panningEnabled=True,
        zoomingEnabled=True,
        minZoom=0.6,
        maxZoom=2,
        style={"height": "380px", "width": "100%"},
        stylesheet=[
            {
                "selector": "node",
                "style": {
                    "label": "data(label)",
                    "shape": "round-rectangle",
                    "background-color": "#0b5f56",
                    "border-width": 3,
                    "border-color": "#99f6e4",
                    "color": "#f0fdfa",
                    "text-wrap": "wrap",
                    "text-max-width": 190,
                    "font-size": 13,
                    "font-weight": 700,
                    "text-valign": "center",
                    "text-halign": "center",
                    "padding": "14px",
                    "width": 210,
                    "height": 104,
                },
            },
            {
                "selector": "edge",
                "style": {
                    "label": "data(label)",
                    "line-color": "#0e7490",
                    "target-arrow-color": "#0e7490",
                    "target-arrow-shape": "triangle",
                    "curve-style": "straight",
                    "width": 4,
                    "font-size": 12,
                    "font-weight": 700,
                    "text-background-color": "#cffafe",
                    "text-background-opacity": 1,
                    "text-background-padding": 6,
                    "text-border-color": "#155e75",
                    "text-border-width": 1,
                },
            },
        ],
    )


def _build_supply_chain_leg_cards(supply_chain: dict):
    legs = supply_chain.get("legs", [])
    if not legs:
        return html.Div("No transport legs available.")

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        f"{leg.get('source_company', 'Unknown')} -> {leg.get('destination_company', 'Unknown')}",
                        className="designer-balance-leg-title",
                    ),
                    html.Div(
                        (
                            f"{leg.get('distance_km', 0)} km | "
                            f"{leg.get('delay_days', 0)} days | "
                            f"CHF {leg.get('economic_cost_chf', 0)} | "
                            f"{leg.get('co2eq_kg', 0)} kg CO2eq"
                        ),
                        className="designer-balance-leg-details",
                    ),
                ],
                className="designer-balance-leg-card",
            )
            for leg in legs
        ],
        className="designer-balance-leg-cards",
    )


def _build_table(
    columns: list[dict[str, str]], rows: list[dict[str, Any]], table_id: str
):
    return dash_table.DataTable(
        id=table_id,
        columns=cast(Any, columns),
        data=cast(Any, rows),
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "10px", "whiteSpace": "normal"},
        style_header={"fontWeight": "bold"},
        page_size=12,
    )


def _build_balance_content(scenario: dict):
    summary = scenario.get("summary", {})
    garment = scenario.get("garment", {})
    material = scenario.get("material", {})
    highest_delay_actor = summary.get("highest_delay_actor", {})
    supply_chain = scenario.get("supply_chain", {})

    return html.Div(
        [
            html.Div(
                [
                    _metric_card(
                        "Economic total",
                        _format_currency(summary.get("economic_total_chf")),
                        (
                            f"BOM { _format_currency(summary.get('bom_cost_chf')) } | "
                            f"BOP { _format_currency(summary.get('bop_cost_chf')) } | "
                            f"Transport { _format_currency(summary.get('transport_cost_chf')) }"
                        ),
                    ),
                    _metric_card(
                        "Environmental total",
                        _format_co2(summary.get("co2eq_total_kg")),
                        (
                            f"Fabric { _format_co2(summary.get('material_and_fabric_co2eq_kg')) } | "
                            f"Processes { _format_co2(summary.get('process_co2eq_kg')) } | "
                            f"Transport { _format_co2(summary.get('transport_co2eq_kg')) }"
                        ),
                    ),
                    _metric_card(
                        "Margin",
                        _format_currency(summary.get("margin_chf")),
                        f"Sales price for {garment.get('name', 'garment')}: { _format_currency(garment.get('price_chf')) }",
                    ),
                    _metric_card(
                        "Longevity",
                        f"{material.get('longevity_wears', 0)} wears",
                        f"Mock average for {material.get('name', 'the selected material')}",
                    ),
                    _metric_card(
                        "Delays",
                        _format_days(summary.get("total_delay_days")),
                        (
                            f"Highest delay at {highest_delay_actor.get('company', 'N/A')} "
                            f"({highest_delay_actor.get('role_group', 'n/a')})"
                        ),
                    ),
                ],
                className="designer-balance-metrics",
            ),
            html.Div(
                [
                    html.H2("Supply Chain"),
                    html.P(
                        "Switch suppliers above to see how transport, delays, and product balance change for the current garment scenario."
                    ),
                    _build_supply_chain_leg_cards(supply_chain),
                    _build_supply_chain_graph(supply_chain),
                ],
                className="designer-balance-panel designer-balance-panel-wide",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Scenario Snapshot"),
                            html.Ul(
                                [
                                    html.Li(
                                        f"Garment: {garment.get('name', 'Unknown')}"
                                    ),
                                    html.Li(
                                        f"Material: {material.get('name', 'Unknown')}"
                                    ),
                                    html.Li(
                                        f"Fabric supplier: {scenario.get('selection', {}).get('fabric_supplier', 'N/A')}"
                                    ),
                                    html.Li(
                                        f"Garment manufacturer: {scenario.get('selection', {}).get('garment_supplier', 'N/A')}"
                                    ),
                                    html.Li(
                                        f"Finishing supplier: {scenario.get('selection', {}).get('finishing_supplier', 'N/A')}"
                                    ),
                                ]
                            ),
                            html.H3("Transport Legs"),
                            _build_table(
                                [
                                    {"name": "From", "id": "source_company"},
                                    {"name": "To", "id": "destination_company"},
                                    {"name": "Distance (km)", "id": "distance_km"},
                                    {"name": "Delay (days)", "id": "delay_days"},
                                    {
                                        "name": "Economic Cost (CHF)",
                                        "id": "economic_cost_chf",
                                    },
                                    {"name": "CO2eq (kg)", "id": "co2eq_kg"},
                                ],
                                supply_chain.get("legs", []),
                                "designer-balance-transport-legs",
                            ),
                        ],
                        className="designer-balance-panel",
                    ),
                ],
                className="designer-balance-stack",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H2("Bill of Materials"),
                            _build_table(
                                [
                                    {"name": "Fabric block", "id": "fabric_block"},
                                    {"name": "Quantity", "id": "quantity"},
                                    {"name": "Material", "id": "material"},
                                    {"name": "sqm per unit", "id": "sqm_per_unit"},
                                    {"name": "Total sqm", "id": "total_sqm"},
                                    {"name": "Weight (kg)", "id": "weight_kg"},
                                    {
                                        "name": "Economic Cost (CHF)",
                                        "id": "economic_cost_chf",
                                    },
                                    {"name": "CO2eq (kg)", "id": "co2eq_kg"},
                                ],
                                scenario.get("bill_of_materials", []),
                                "designer-balance-bom",
                            ),
                        ],
                        className="designer-balance-panel",
                    ),
                    html.Div(
                        [
                            html.H2("Bill of Processes"),
                            _build_table(
                                [
                                    {"name": "Source", "id": "source"},
                                    {"name": "Process", "id": "process"},
                                    {"name": "Amount", "id": "amount"},
                                    {
                                        "name": "Economic Cost (CHF)",
                                        "id": "economic_cost_chf",
                                    },
                                    {"name": "CO2eq (kg)", "id": "co2eq_kg"},
                                ],
                                scenario.get("bill_of_processes", []),
                                "designer-balance-bop",
                            ),
                        ],
                        className="designer-balance-panel",
                    ),
                ],
                className="designer-balance-stack",
                style={"display": "grid", "gridTemplateColumns": "1fr", "gap": "18px"},
            ),
        ]
    )


def register_designer_balance_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("designer-balance-garment", "options"),
        Output("designer-balance-garment", "value"),
        Output("designer-balance-fabric-supplier", "options"),
        Output("designer-balance-fabric-supplier", "value"),
        Output("designer-balance-garment-supplier", "options"),
        Output("designer-balance-garment-supplier", "value"),
        Output("designer-balance-finishing-supplier", "options"),
        Output("designer-balance-finishing-supplier", "value"),
        Input("url", "pathname"),
    )
    def load_designer_balance_options(pathname):
        if pathname != "/designer-balance":
            return [], None, [], None, [], None, [], None

        options = fetch_designer_balance_options()
        garment_types = options.get("garment_types", [])
        suppliers = options.get("suppliers", {})

        garment_options = [
            {"label": garment["name"], "value": garment["id"]}
            for garment in garment_types
        ]

        def _supplier_options(role_group: str):
            supplier_rows = suppliers.get(role_group, [])
            return [
                {
                    "label": f"{item['company']} ({item['location']})",
                    "value": item["company"],
                }
                for item in supplier_rows
            ]

        fabric_options = _supplier_options("fabric")
        garment_supplier_options = _supplier_options("garment")
        finishing_options = _supplier_options("finishing")

        return (
            garment_options,
            garment_options[0]["value"] if garment_options else None,
            fabric_options,
            fabric_options[0]["value"] if fabric_options else None,
            garment_supplier_options,
            garment_supplier_options[0]["value"] if garment_supplier_options else None,
            finishing_options,
            finishing_options[0]["value"] if finishing_options else None,
        )

    @app.callback(
        Output("designer-balance-material", "options"),
        Output("designer-balance-material", "value"),
        Input("designer-balance-garment", "value"),
    )
    def load_material_options(garment_type_id):
        if not garment_type_id:
            return [], None

        materials = fetch_materials_for_garment(garment_type_id)
        material_options = [
            {"label": material["name"], "value": material["id"]}
            for material in materials
        ]
        return material_options, (
            material_options[0]["value"] if material_options else None
        )

    @app.callback(
        Output("designer-balance-content", "children"),
        Input("designer-balance-garment", "value"),
        Input("designer-balance-material", "value"),
        Input("designer-balance-fabric-supplier", "value"),
        Input("designer-balance-garment-supplier", "value"),
        Input("designer-balance-finishing-supplier", "value"),
    )
    def render_designer_balance(
        garment_type_id,
        material_id,
        fabric_supplier,
        garment_supplier,
        finishing_supplier,
    ):
        if not garment_type_id or not material_id:
            return html.Div(
                "Select a garment type and a material to inspect the scenario."
            )

        scenario = fetch_designer_balance_scenario(
            garment_type_id,
            material_id,
            fabric_supplier,
            garment_supplier,
            finishing_supplier,
        )
        if not scenario:
            return html.Div("No balance scenario could be loaded from the backend.")

        return _build_balance_content(scenario)
