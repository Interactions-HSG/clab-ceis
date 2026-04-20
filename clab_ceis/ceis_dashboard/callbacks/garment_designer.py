from __future__ import annotations

from typing import Any, cast

from dash import Dash, Input, Output, State, dash_table, html

import ceis_data
from ceis_dashboard.callbacks.api import (
    fetch_designer_balance_scenario,
    fetch_designer_garment_reference,
    fetch_materials_for_garment,
)


def _table(columns: list[dict[str, str]], rows: list[dict[str, Any]], table_id: str):
    return dash_table.DataTable(
        id=table_id,
        columns=cast(Any, columns),
        data=cast(Any, rows),
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "10px", "whiteSpace": "normal"},
        style_header={"fontWeight": "bold"},
        page_size=10,
    )


def _format_currency(value: float | int | None) -> str:
    return f"CHF {float(value or 0):.2f}"


def register_garment_designer_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("garment-designer-reference-garment", "options"),
        Output("garment-designer-reference-garment", "value"),
        Input("url", "pathname"),
    )
    def load_garment_designer_options(pathname):
        if pathname != "/garment-designer":
            return [], None

        reference = fetch_designer_garment_reference()
        garment_types = reference.get("garment_types", [])
        options = [{"label": row["name"], "value": row["id"]} for row in garment_types]
        return options, options[0]["value"] if options else None

    @app.callback(
        Output("garment-designer-content", "children"),
        Input("garment-designer-reference-garment", "value"),
        State("garment-designer-name", "value"),
        State("garment-designer-target-price", "value"),
    )
    def render_garment_designer_content(
        reference_garment_id,
        new_garment_name,
        target_price,
    ):
        reference = fetch_designer_garment_reference()
        materials = reference.get("materials", [])
        process_types = reference.get("process_types", [])
        fabric_block_types = reference.get("fabric_block_types", [])

        scenario_card = html.Div(
            "Select a reference garment to load BOM/BOP and scenario process costs."
        )
        if reference_garment_id:
            garment_materials = fetch_materials_for_garment(reference_garment_id)
            material_id = garment_materials[0]["id"] if garment_materials else None
            if material_id is not None:
                scenario = fetch_designer_balance_scenario(
                    reference_garment_id,
                    material_id,
                    None,
                    None,
                    None,
                )
                if scenario:
                    scenario_summary = scenario.get("summary", {})
                    margin = float(scenario_summary.get("margin_chf") or 0)
                    target_delta = None
                    if target_price is not None:
                        target_delta = float(target_price) - float(
                            scenario_summary.get("economic_total_chf") or 0
                        )

                    scenario_card = html.Div(
                        [
                            html.H2("Reference Garment Design Snapshot"),
                            html.Ul(
                                [
                                    html.Li(
                                        f"Reference garment: {scenario.get('garment', {}).get('name', 'Unknown')}"
                                    ),
                                    html.Li(
                                        f"Reference material longevity: {scenario.get('material', {}).get('longevity_wears', 0)} wears"
                                    ),
                                    html.Li(
                                        f"Economic total: {_format_currency(scenario_summary.get('economic_total_chf'))}"
                                    ),
                                    html.Li(
                                        f"Margin at current recipe price: {_format_currency(margin)}"
                                    ),
                                    html.Li(
                                        (
                                            f"Target price delta: {_format_currency(target_delta)}"
                                            if target_delta is not None
                                            else "Set target price to compare design viability."
                                        )
                                    ),
                                    html.Li(
                                        f"Ecological total: {float(scenario_summary.get('co2eq_total_kg') or 0):.3f} kg CO2eq"
                                    ),
                                ]
                            ),
                            html.H3("Reference Bill of Materials"),
                            _table(
                                [
                                    {"name": "Fabric block", "id": "fabric_block"},
                                    {"name": "Quantity", "id": "quantity"},
                                    {"name": "Material", "id": "material"},
                                    {
                                        "name": "Economic Cost (CHF)",
                                        "id": "economic_cost_chf",
                                    },
                                    {"name": "CO2eq (kg)", "id": "co2eq_kg"},
                                ],
                                scenario.get("bill_of_materials", []),
                                "garment-designer-reference-bom",
                            ),
                            html.H3("Reference Bill of Processes"),
                            _table(
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
                                "garment-designer-reference-bop",
                            ),
                        ],
                        className="garment-designer-panel",
                    )

        return html.Div(
            [
                html.Div(
                    [
                        html.H2("Material Reference (Longevity + Economic)"),
                        _table(
                            [
                                {"name": "Material", "id": "name"},
                                {"name": "kg/sqm", "id": "kg_per_sqm"},
                                {"name": "Longevity (wears)", "id": "longevity_wears"},
                                {"name": "Cost per kg (CHF)", "id": "cost_per_kg_chf"},
                            ],
                            materials,
                            "garment-designer-material-reference",
                        ),
                    ],
                    className="garment-designer-panel",
                ),
                html.Div(
                    [
                        html.H2("Process Type Reference (Economic + Ecological)"),
                        _table(
                            [
                                {"name": "Process", "id": "name"},
                                {"name": "Unit", "id": "unit"},
                                {
                                    "name": "Economic Cost per Unit (CHF)",
                                    "id": "economic_cost_per_unit_chf",
                                },
                                {
                                    "name": "Ecological Cost per Unit (kg CO2eq)",
                                    "id": "ecological_cost_per_unit_co2eq",
                                },
                            ],
                            process_types,
                            "garment-designer-process-reference",
                        ),
                    ],
                    className="garment-designer-panel",
                ),
                html.Div(
                    [
                        html.H2("Fabric Block Catalog"),
                        _table(
                            [
                                {"name": "Fabric block type", "id": "name"},
                                {"name": "ID", "id": "id"},
                            ],
                            fabric_block_types,
                            "garment-designer-fabric-block-reference",
                        ),
                    ],
                    className="garment-designer-panel",
                ),
                scenario_card,
            ],
            className="garment-designer-stack",
        )
