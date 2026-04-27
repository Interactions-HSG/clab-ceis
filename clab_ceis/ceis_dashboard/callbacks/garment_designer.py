from __future__ import annotations

from typing import Any, cast

from dash import Dash, Input, Output, State, callback_context, dash_table, dcc, html

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


def _format_signed_currency(value: float | int | None) -> str:
    return f"CHF {float(value or 0):+.2f}"


def _format_co2(value: float | int | None) -> str:
    return f"{float(value or 0):.3f} kg CO2eq"


def _format_signed_co2(value: float | int | None) -> str:
    return f"{float(value or 0):+.3f} kg CO2eq"


def _metric_card(title: str, value: str, subtitle: str):
    return html.Div(
        [
            html.Div(title, className="designer-balance-metric-title"),
            html.Div(value, className="designer-balance-metric-value"),
            html.Div(subtitle, className="designer-balance-metric-subtitle"),
        ],
        className="designer-balance-metric-card",
    )


def _build_reference_scenario_card(scenario: dict, target_price: float | int | None):
    if not scenario:
        return html.Div(
            "Select a reference garment to load BOM/BOP and scenario process costs."
        )

    scenario_summary = scenario.get("summary", {})
    margin = float(scenario_summary.get("margin_chf") or 0)
    target_delta = None
    if target_price is not None:
        target_delta = float(target_price) - float(
            scenario_summary.get("economic_total_chf") or 0
        )

    return html.Div(
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
                    {"name": "Economic Cost (CHF)", "id": "economic_cost_chf"},
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
                    {"name": "Economic Cost (CHF)", "id": "economic_cost_chf"},
                    {"name": "CO2eq (kg)", "id": "co2eq_kg"},
                ],
                scenario.get("bill_of_processes", []),
                "garment-designer-reference-bop",
            ),
        ],
        className="garment-designer-panel",
    )


def _default_material_name(reference: dict, scenario: dict) -> str | None:
    materials = reference.get("materials", [])
    scenario_material = scenario.get("material", {}).get("name")
    if scenario_material and any(
        material.get("name") == scenario_material for material in materials
    ):
        return scenario_material
    return materials[0]["name"] if materials else None


def _fabric_block_options(reference: dict) -> list[dict[str, Any]]:
    options_by_id: dict[int, dict[str, Any]] = {}
    for row in reference.get("fabric_block_types", []):
        options_by_id[int(row["id"])] = {
            "label": f"{row['name']} ({row['sqm']} sqm)",
            "value": row["id"],
        }
    return list(options_by_id.values())


def _process_options(reference: dict) -> list[dict[str, Any]]:
    options = []
    for process in reference.get("process_types", []):
        if process.get("name", "").lower() == "transport":
            continue
        options.append(
            {
                "label": f"{process['name']} ({process.get('unit') or 'unit'})",
                "value": process["id"],
            }
        )
    return options


def _fabric_block_reference_table_rows(reference: dict) -> list[dict[str, Any]]:
    rows = []
    for row in reference.get("fabric_block_types", []):
        rows.append(
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "sqm": row.get("sqm"),
                "material": row.get("material"),
                "weight_kg": row.get("weight_kg"),
                "material_cost_chf": row.get("material_cost_chf"),
                "co2eq_kg": row.get("co2eq_kg"),
            }
        )
    return rows


def _build_dynamic_designer_panel(reference: dict, scenario: dict):
    materials = reference.get("materials", [])
    default_material = _default_material_name(reference, scenario)
    fabric_block_options = _fabric_block_options(reference)
    process_options = _process_options(reference)

    return html.Div(
        [
            html.H2("Dynamic Garment Designer"),
            html.P(
                "Build the new garment one fabric block or garment process at a time. Changing the selected material updates all current fabric block impacts."
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Design material"),
                            dcc.Dropdown(
                                id="garment-designer-custom-material",
                                options=[
                                    {"label": material["name"], "value": material["name"]}
                                    for material in materials
                                ],
                                value=default_material,
                                clearable=False,
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                ],
                className="garment-designer-controls",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Add fabric block"),
                            dcc.Dropdown(
                                id="garment-designer-add-fabric-block",
                                options=fabric_block_options,
                                value=(
                                    fabric_block_options[0]["value"]
                                    if fabric_block_options
                                    else None
                                ),
                                clearable=False,
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                    html.Div(
                        [
                            html.Label("Quantity"),
                            dcc.Input(
                                id="garment-designer-add-fabric-block-qty",
                                type="number",
                                min=1,
                                step=1,
                                value=1,
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                    html.Button(
                        "Add fabric block",
                        id="garment-designer-add-fabric-block-button",
                        n_clicks=0,
                    ),
                    html.Button(
                        "Remove last fabric block",
                        id="garment-designer-remove-fabric-block-button",
                        n_clicks=0,
                    ),
                    html.Button(
                        "Clear fabric blocks",
                        id="garment-designer-clear-fabric-blocks-button",
                        n_clicks=0,
                    ),
                ],
                className="garment-designer-controls",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Add garment process"),
                            dcc.Dropdown(
                                id="garment-designer-add-process",
                                options=process_options,
                                value=(
                                    process_options[0]["value"]
                                    if process_options
                                    else None
                                ),
                                clearable=False,
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                    html.Div(
                        [
                            html.Label("Amount"),
                            dcc.Input(
                                id="garment-designer-add-process-amount",
                                type="number",
                                min=0,
                                step=0.01,
                                placeholder="e.g., 0.25",
                            ),
                        ],
                        className="garment-designer-control",
                    ),
                    html.Button(
                        "Add process",
                        id="garment-designer-add-process-button",
                        n_clicks=0,
                    ),
                    html.Button(
                        "Remove last process",
                        id="garment-designer-remove-process-button",
                        n_clicks=0,
                    ),
                    html.Button(
                        "Clear processes",
                        id="garment-designer-clear-processes-button",
                        n_clicks=0,
                    ),
                ],
                className="garment-designer-controls",
            ),
            html.Div(id="garment-designer-custom-impact"),
            html.Div(
                [
                    html.H3("Current Bill of Materials"),
                    html.P(
                        "Fabric block CO2 includes material, the fabric block recipe processes, and material transport to the manufacturer."
                    ),
                    html.Div(id="garment-designer-custom-bom-container"),
                ],
                className="garment-designer-panel",
            ),
            html.Div(
                [
                    html.H3("Current Bill of Processes"),
                    html.P(
                        "Fabric block recipe processes are added automatically when you add a fabric block. Garment assembly processes below are the extra processes you add explicitly."
                    ),
                    html.Div(id="garment-designer-custom-bop-container"),
                ],
                className="garment-designer-panel",
            ),
        ],
        className="garment-designer-panel garment-designer-panel-wide",
    )


def _lookup_material(reference: dict, material_name: str | None) -> dict | None:
    for material in reference.get("materials", []):
        if material.get("name") == material_name:
            return material
    return None


def _lookup_fabric_block(reference: dict, block_id: int, material_name: str | None) -> dict | None:
    for row in reference.get("fabric_block_types", []):
        if int(row.get("id") or 0) == int(block_id) and row.get("material") == material_name:
            return row
    return None


def _lookup_process(reference: dict, process_id: int) -> dict | None:
    for process in reference.get("process_types", []):
        if int(process.get("id") or 0) == int(process_id):
            return process
    return None


def _upsert_process_row(
    rows_by_key: dict[tuple[str, str], dict[str, Any]],
    source: str,
    process_name: str,
    amount: float,
    economic_cost: float,
    co2eq_kg: float,
) -> None:
    key = (source, process_name)
    current = rows_by_key.setdefault(
        key,
        {
            "source": source,
            "process": process_name,
            "amount": 0.0,
            "economic_cost_chf": 0.0,
            "co2eq_kg": 0.0,
        },
    )
    current["amount"] += amount
    current["economic_cost_chf"] += economic_cost
    current["co2eq_kg"] += co2eq_kg


def _build_custom_design_data(
    reference: dict,
    material_name: str | None,
    bom_entries: list[dict[str, Any]],
    process_entries: list[dict[str, Any]],
) -> dict:
    material = _lookup_material(reference, material_name)
    if material is None:
        return {
            "bom_rows": [],
            "bop_rows": [],
            "summary": {
                "material_name": None,
                "longevity_wears": 0,
                "bom_cost_chf": 0.0,
                "bop_cost_chf": 0.0,
                "economic_total_chf": 0.0,
                "fabric_block_co2eq_kg": 0.0,
                "added_process_co2eq_kg": 0.0,
                "co2eq_total_kg": 0.0,
                "fabric_block_count": 0,
                "added_process_count": 0,
            },
        }

    bom_by_name: dict[str, dict[str, Any]] = {}
    bop_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    total_bom_cost = 0.0
    total_bop_cost = 0.0
    total_fabric_block_co2 = 0.0
    total_added_process_co2 = 0.0
    total_fabric_block_count = 0
    total_added_process_count = 0

    for entry in bom_entries or []:
        block_id = int(entry.get("fabric_block_id") or 0)
        quantity = max(int(entry.get("quantity") or 1), 1)
        block = _lookup_fabric_block(reference, block_id, material_name)
        if block is None:
            continue

        total_fabric_block_count += quantity
        material_cost = float(block.get("material_cost_chf") or 0) * quantity
        total_cost = float(block.get("total_cost_chf") or 0) * quantity
        weight_kg = float(block.get("weight_kg") or 0) * quantity
        total_sqm = float(block.get("sqm") or 0) * quantity
        block_co2 = float(block.get("co2eq_kg") or 0) * quantity

        total_bom_cost += material_cost
        total_bop_cost += max(total_cost - material_cost, 0)
        total_fabric_block_co2 += block_co2

        current_bom = bom_by_name.setdefault(
            block["name"],
            {
                "fabric_block": block["name"],
                "quantity": 0,
                "material": material_name,
                "sqm_per_unit": float(block.get("sqm") or 0),
                "total_sqm": 0.0,
                "weight_kg": 0.0,
                "economic_cost_chf": 0.0,
                "co2eq_kg": 0.0,
            },
        )
        current_bom["quantity"] += quantity
        current_bom["total_sqm"] += total_sqm
        current_bom["weight_kg"] += weight_kg
        current_bom["economic_cost_chf"] += material_cost
        current_bom["co2eq_kg"] += block_co2

        for process in block.get("processes", []):
            process_name = process.get("process", "Unknown")
            process_amount = float(process.get("amount") or 0) * quantity
            process_cost = float(process.get("economic_cost_chf") or 0) * quantity
            process_co2 = float(process.get("co2eq_kg") or 0) * quantity
            _upsert_process_row(
                bop_by_key,
                f"Fabric block {block['name']}",
                process_name,
                process_amount,
                process_cost,
                process_co2,
            )

    for entry in process_entries or []:
        process_id = int(entry.get("process_id") or 0)
        amount = float(entry.get("amount") or 0)
        if amount <= 0:
            continue

        process = _lookup_process(reference, process_id)
        if process is None:
            continue

        total_added_process_count += 1
        process_cost = float(process.get("economic_cost_per_unit_chf") or 0) * amount
        process_co2 = float(process.get("ecological_cost_per_unit_co2eq") or 0) * amount
        total_bop_cost += process_cost
        total_added_process_co2 += process_co2
        _upsert_process_row(
            bop_by_key,
            "Garment assembly",
            process.get("name", "Unknown"),
            amount,
            process_cost,
            process_co2,
        )

    bom_rows = []
    for row in bom_by_name.values():
        bom_rows.append(
            {
                **row,
                "sqm_per_unit": round(float(row["sqm_per_unit"]), 3),
                "total_sqm": round(float(row["total_sqm"]), 3),
                "weight_kg": round(float(row["weight_kg"]), 3),
                "economic_cost_chf": round(float(row["economic_cost_chf"]), 2),
                "co2eq_kg": round(float(row["co2eq_kg"]), 3),
            }
        )

    bop_rows = []
    for row in bop_by_key.values():
        bop_rows.append(
            {
                **row,
                "amount": round(float(row["amount"]), 3),
                "economic_cost_chf": round(float(row["economic_cost_chf"]), 2),
                "co2eq_kg": round(float(row["co2eq_kg"]), 3),
            }
        )

    bom_rows.sort(key=lambda row: row["fabric_block"])
    bop_rows.sort(key=lambda row: (row["source"], row["process"]))

    return {
        "bom_rows": bom_rows,
        "bop_rows": bop_rows,
        "summary": {
            "material_name": material_name,
            "longevity_wears": int(material.get("longevity_wears") or 0),
            "bom_cost_chf": round(total_bom_cost, 2),
            "bop_cost_chf": round(total_bop_cost, 2),
            "economic_total_chf": round(total_bom_cost + total_bop_cost, 2),
            "fabric_block_co2eq_kg": round(total_fabric_block_co2, 3),
            "added_process_co2eq_kg": round(total_added_process_co2, 3),
            "co2eq_total_kg": round(total_fabric_block_co2 + total_added_process_co2, 3),
            "fabric_block_count": total_fabric_block_count,
            "added_process_count": total_added_process_count,
        },
    }


def register_garment_designer_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("garment-designer-reference-garment", "options"),
        Output("garment-designer-reference-garment", "value"),
        Output("garment-designer-reference-data-store", "data"),
        Input("url", "pathname"),
    )
    def load_garment_designer_options(pathname):
        if pathname != "/garment-designer":
            return [], None, {}

        reference = fetch_designer_garment_reference()
        garment_types = reference.get("garment_types", [])
        options = [{"label": row["name"], "value": row["id"]} for row in garment_types]
        return options, options[0]["value"] if options else None, reference

    @app.callback(
        Output("garment-designer-reference-scenario-store", "data"),
        Input("garment-designer-reference-garment", "value"),
    )
    def load_reference_garment_scenario(reference_garment_id):
        if reference_garment_id is None:
            return {}

        garment_materials = fetch_materials_for_garment(reference_garment_id)
        material_id = garment_materials[0]["id"] if garment_materials else None
        if material_id is None:
            return {}

        return fetch_designer_balance_scenario(
            reference_garment_id,
            material_id,
            None,
            None,
            None,
        )

    @app.callback(
        Output("garment-designer-content", "children"),
        Input("garment-designer-reference-data-store", "data"),
        Input("garment-designer-reference-scenario-store", "data"),
        State("garment-designer-target-price", "value"),
    )
    def render_garment_designer_content(reference, reference_scenario, target_price):
        reference = reference or {}
        materials = reference.get("materials", [])
        process_types = reference.get("process_types", [])
        fabric_block_types = _fabric_block_reference_table_rows(reference)

        return html.Div(
            [
                _build_dynamic_designer_panel(reference, reference_scenario or {}),
                _build_reference_scenario_card(reference_scenario or {}, target_price),
                html.Div(
                    [
                        html.H2("Material Reference"),
                        _table(
                            [
                                {"name": "Material", "id": "name"},
                                {"name": "kg/sqm", "id": "kg_per_sqm"},
                                {"name": "Longevity (wears)", "id": "longevity_wears"},
                                {"name": "Cost per kg (CHF)", "id": "cost_per_kg_chf"},
                                {"name": "CO2eq per kg", "id": "co2eq_per_kg"},
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
                        html.P(
                            "CO2eq includes the material itself, the fabric block recipe processes, and material transport to the manufacturer."
                        ),
                        _table(
                            [
                                {"name": "Fabric block type", "id": "name"},
                                {"name": "ID", "id": "id"},
                                {"name": "sqm", "id": "sqm"},
                                {"name": "Material", "id": "material"},
                                {"name": "Weight (kg)", "id": "weight_kg"},
                                {
                                    "name": "Material Cost (CHF)",
                                    "id": "material_cost_chf",
                                },
                                {
                                    "name": "CO2eq (kg, material + block processes + transport)",
                                    "id": "co2eq_kg",
                                },
                            ],
                            fabric_block_types,
                            "garment-designer-fabric-block-reference",
                        ),
                    ],
                    className="garment-designer-panel",
                ),
            ],
            className="garment-designer-stack",
        )

    @app.callback(
        Output("garment-designer-custom-bom-store", "data"),
        Output("garment-designer-add-fabric-block-qty", "value"),
        Input("garment-designer-add-fabric-block-button", "n_clicks"),
        Input("garment-designer-remove-fabric-block-button", "n_clicks"),
        Input("garment-designer-clear-fabric-blocks-button", "n_clicks"),
        State("garment-designer-add-fabric-block", "value"),
        State("garment-designer-add-fabric-block-qty", "value"),
        State("garment-designer-custom-bom-store", "data"),
        prevent_initial_call=True,
    )
    def update_custom_bom_store(
        add_clicks,
        remove_clicks,
        clear_clicks,
        selected_fabric_block,
        quantity,
        current_entries,
    ):
        trigger = (
            callback_context.triggered[0]["prop_id"].split(".")[0]
            if callback_context.triggered
            else None
        )
        entries = list(current_entries or [])

        if trigger == "garment-designer-clear-fabric-blocks-button":
            if not clear_clicks:
                return entries, quantity
            return [], 1

        if trigger == "garment-designer-remove-fabric-block-button":
            if not remove_clicks:
                return entries, quantity
            if entries:
                entries.pop()
            return entries, 1

        if trigger != "garment-designer-add-fabric-block-button":
            return entries, quantity

        if not add_clicks:
            return entries, quantity

        if selected_fabric_block is None:
            return entries, quantity

        entries.append(
            {
                "fabric_block_id": int(selected_fabric_block),
                "quantity": max(int(quantity or 1), 1),
            }
        )
        return entries, 1

    @app.callback(
        Output("garment-designer-custom-process-store", "data"),
        Output("garment-designer-add-process-amount", "value"),
        Input("garment-designer-add-process-button", "n_clicks"),
        Input("garment-designer-remove-process-button", "n_clicks"),
        Input("garment-designer-clear-processes-button", "n_clicks"),
        State("garment-designer-add-process", "value"),
        State("garment-designer-add-process-amount", "value"),
        State("garment-designer-custom-process-store", "data"),
        prevent_initial_call=True,
    )
    def update_custom_process_store(
        add_clicks,
        remove_clicks,
        clear_clicks,
        selected_process,
        amount,
        current_entries,
    ):
        trigger = (
            callback_context.triggered[0]["prop_id"].split(".")[0]
            if callback_context.triggered
            else None
        )
        entries = list(current_entries or [])

        if trigger == "garment-designer-clear-processes-button":
            if not clear_clicks:
                return entries, amount
            return [], None

        if trigger == "garment-designer-remove-process-button":
            if not remove_clicks:
                return entries, amount
            if entries:
                entries.pop()
            return entries, None

        if trigger != "garment-designer-add-process-button":
            return entries, amount

        if not add_clicks:
            return entries, amount

        if selected_process is None or amount is None or float(amount) <= 0:
            return entries, amount

        entries.append(
            {
                "process_id": int(selected_process),
                "amount": float(amount),
            }
        )
        return entries, None

    @app.callback(
        Output("garment-designer-custom-impact", "children"),
        Output("garment-designer-custom-bom-container", "children"),
        Output("garment-designer-custom-bop-container", "children"),
        Input("garment-designer-custom-bom-store", "data"),
        Input("garment-designer-custom-process-store", "data"),
        Input("garment-designer-custom-material", "value"),
        Input("garment-designer-reference-data-store", "data"),
        Input("garment-designer-reference-scenario-store", "data"),
        Input("garment-designer-target-price", "value"),
        Input("garment-designer-name", "value"),
    )
    def render_custom_design_impact(
        bom_entries,
        process_entries,
        material_name,
        reference,
        reference_scenario,
        target_price,
        garment_name,
    ):
        reference = reference or {}
        reference_scenario = reference_scenario or {}
        custom_design = _build_custom_design_data(
            reference,
            material_name,
            list(bom_entries or []),
            list(process_entries or []),
        )
        summary = custom_design["summary"]

        reference_summary = reference_scenario.get("summary", {})
        reference_cost = float(reference_summary.get("economic_total_chf") or 0)
        reference_co2 = float(reference_summary.get("co2eq_total_kg") or 0)
        custom_cost = float(summary["economic_total_chf"])
        custom_co2 = float(summary["co2eq_total_kg"])
        target_room = (
            float(target_price) - custom_cost if target_price is not None else None
        )

        title_name = garment_name or "new design"
        impact_cards = html.Div(
            [
                _metric_card(
                    "Economic total",
                    _format_currency(custom_cost),
                    (
                        f"Materials { _format_currency(summary['bom_cost_chf']) } | "
                        f"Block recipe + added processes { _format_currency(summary['bop_cost_chf']) }"
                    ),
                ),
                _metric_card(
                    "Environmental total",
                    _format_co2(custom_co2),
                    (
                        f"Fabric blocks { _format_co2(summary['fabric_block_co2eq_kg']) } | "
                        f"Added garment processes { _format_co2(summary['added_process_co2eq_kg']) }"
                    ),
                ),
                _metric_card(
                    "Longevity",
                    f"{summary['longevity_wears']} wears",
                    f"Current design material: {summary.get('material_name') or 'not selected'}",
                ),
                _metric_card(
                    "Target room",
                    (
                        _format_signed_currency(target_room)
                        if target_room is not None
                        else "Set target price"
                    ),
                    "Positive means the current design is under the target price.",
                ),
                _metric_card(
                    "Reference delta",
                    _format_signed_currency(custom_cost - reference_cost),
                    (
                        f"CO2 delta { _format_signed_co2(custom_co2 - reference_co2) } "
                        f"vs {reference_scenario.get('garment', {}).get('name', 'reference garment')}"
                    ),
                ),
            ],
            className="designer-balance-metrics",
        )

        impact_summary = html.Div(
            [
                impact_cards,
                html.Ul(
                    [
                        html.Li(f"Working design: {title_name}"),
                        html.Li(
                            f"Selected material: {summary.get('material_name') or 'None'}"
                        ),
                        html.Li(
                            f"Fabric blocks added: {summary['fabric_block_count']}"
                        ),
                        html.Li(
                            f"Explicit garment processes added: {summary['added_process_count']}"
                        ),
                    ]
                ),
            ]
        )

        bom_rows = custom_design["bom_rows"]
        if bom_rows:
            bom_content = _table(
                [
                    {"name": "Fabric block", "id": "fabric_block"},
                    {"name": "Quantity", "id": "quantity"},
                    {"name": "Material", "id": "material"},
                    {"name": "sqm per unit", "id": "sqm_per_unit"},
                    {"name": "Total sqm", "id": "total_sqm"},
                    {"name": "Weight (kg)", "id": "weight_kg"},
                    {"name": "Economic Cost (CHF)", "id": "economic_cost_chf"},
                    {"name": "CO2eq (kg)", "id": "co2eq_kg"},
                ],
                bom_rows,
                "garment-designer-custom-bom-table",
            )
        else:
            bom_content = html.Div("Add a fabric block to start building the BOM.")

        bop_rows = custom_design["bop_rows"]
        if bop_rows:
            bop_content = _table(
                [
                    {"name": "Source", "id": "source"},
                    {"name": "Process", "id": "process"},
                    {"name": "Amount", "id": "amount"},
                    {"name": "Economic Cost (CHF)", "id": "economic_cost_chf"},
                    {"name": "CO2eq (kg)", "id": "co2eq_kg"},
                ],
                bop_rows,
                "garment-designer-custom-bop-table",
            )
        else:
            bop_content = html.Div(
                "Add a fabric block or garment process to see process impact here."
            )

        return impact_summary, bom_content, bop_content
