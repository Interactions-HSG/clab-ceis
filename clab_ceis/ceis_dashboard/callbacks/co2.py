from __future__ import annotations
from dash import Dash, Input, Output, html

import ceis_data
from ceis_dashboard.callbacks.api import (
    get_co2,
    fetch_garment_types,
    fetch_materials_for_garment,
)


def _format_percent(value: float, total: float) -> str:
    if total <= 0:
        return "0.0%"
    return f"{(value / total) * 100:.1f}%"


def _format_kg(value: float) -> str:
    return f"{value:.3f} kg CO2eq"


def _format_number(value: float) -> str:
    return f"{value:.3f}"


def _format_quality(value) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.0f}%"


def _format_processes(processes: list[dict]) -> str:
    if not processes:
        return "None"
    return ", ".join(
        f"{proc.get('process', 'Unknown')} ({proc.get('amount', 0)})"
        for proc in processes
    )


def _co2_metric_card(title: str, value: str, subtitle: str, modifier: str = ""):
    classes = "co2-metric-card"
    if modifier:
        classes = f"{classes} {modifier}"

    return html.Div(
        [
            html.Div(title, className="co2-metric-title"),
            html.Div(value, className="co2-metric-value"),
            html.Div(subtitle, className="co2-metric-subtitle"),
        ],
        className=classes,
    )


def _co2_table(headers: list[str], rows: list[list[str]], empty_message: str):
    if not rows:
        return html.Div(empty_message, className="panel-muted")

    return html.Table(
        [
            html.Thead(html.Tr([html.Th(header) for header in headers])),
            html.Tbody([html.Tr([html.Td(cell) for cell in row]) for row in rows]),
        ],
        className="co2-table",
    )


def _build_material_co2_section(garment_name: str, material_name: str, co2_data):
    co2_from_used_fabric_blocks = sum(
        (fb["alternative"]["emission"] if fb["alternative"] else fb["emission"])
        for fb in co2_data.fabric_blocks.details
    )
    co2_from_inventory_processes = sum(
        (
            sum(process["emission"] for process in fb["alternative"]["process_details"])
            if fb["alternative"]
            else 0
        )
        for fb in co2_data.fabric_blocks.details
    )
    co2_from_transport = sum(
        (fb["alternative"].get("transport_emission", 0) if fb["alternative"] else 0)
        for fb in co2_data.fabric_blocks.details
    )

    used_fabric_block_ids = [
        fb["alternative"]["id"]
        for fb in co2_data.fabric_blocks.details
        if fb["alternative"] and fb["alternative"]["id"] is not None
    ]
    has_second_life_alternatives = bool(used_fabric_block_ids)
    alternative_co2 = co2_data.processes.total_emission + co2_from_used_fabric_blocks

    replaced_fabric_blocks_co2 = sum(
        fb["emission"]
        for fb in co2_data.fabric_blocks.details
        if fb["alternative"] and fb["alternative"]["id"] is not None
    )

    total_emissions = round(
        co2_data.fabric_blocks.total_emission + co2_data.processes.total_emission,
        2,
    )
    alternative_emissions = round(alternative_co2, 2)
    raw_material_total = sum(
        float(fb.get("material_emission", 0)) for fb in co2_data.fabric_blocks.details
    )
    production_total = sum(
        float(fb.get("production_emission", 0)) for fb in co2_data.fabric_blocks.details
    )
    potential_saving = (
        total_emissions - alternative_emissions if has_second_life_alternatives else 0
    )

    fabric_block_rows = [
        [
            fb.get("fabric_block", "Unknown"),
            fb.get("material", "Unknown"),
            _format_number(float(fb.get("amount_kg", 0))),
            _format_number(float(fb.get("material_emission", 0))),
            _format_number(float(fb.get("production_emission", 0))),
            _format_processes(fb.get("production_processes", [])),
        ]
        for fb in co2_data.fabric_blocks.details
    ]

    assembly_process_rows = [
        [
            proc.get("process", "Unknown"),
            str(proc.get("duration", proc.get("amount", 0))),
            _format_number(float(proc.get("emission", 0))),
        ]
        for proc in co2_data.processes.details
    ]

    alternative_rows = []
    for fb in co2_data.fabric_blocks.details:
        alternative = fb.get("alternative") or {}
        if alternative.get("id") is None:
            continue

        prep_emission = sum(
            float(process.get("emission", 0))
            for process in alternative.get("process_details", [])
        )
        alternative_rows.append(
            [
                fb.get("fabric_block", "Unknown"),
                str(alternative.get("id")),
                alternative.get("material") or "Unknown",
                alternative.get("location") or "Unknown",
                _format_quality(alternative.get("quality")),
                _format_number(prep_emission),
                _format_number(float(alternative.get("transport_emission", 0))),
                _format_number(float(alternative.get("emission", 0))),
            ]
        )

    contribution_rows = []
    for fb in co2_data.fabric_blocks.details:
        fabric_block_name = fb.get("fabric_block", "Unknown")
        raw_material_emission = float(fb.get("material_emission", 0))
        production_emission = float(fb.get("production_emission", 0))
        contribution_rows.append(
            [
                "Fabric Block Raw Material",
                fabric_block_name,
                _format_number(raw_material_emission),
                _format_percent(raw_material_emission, total_emissions),
            ]
        )
        contribution_rows.append(
            [
                "Fabric Block Production",
                fabric_block_name,
                _format_number(production_emission),
                _format_percent(production_emission, total_emissions),
            ]
        )

    for proc in co2_data.processes.details:
        emission = float(proc.get("emission", 0))
        contribution_rows.append(
            [
                "Assembly Process",
                proc.get("process", "Unknown"),
                _format_number(emission),
                _format_percent(emission, total_emissions),
            ]
        )

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.Div("Material assessment", className="page-kicker"),
                            html.H3(garment_name),
                        ]
                    ),
                    html.Div(material_name, className="co2-material-badge"),
                ],
                className="co2-assessment-header",
            ),
            html.Div(
                [
                    _co2_metric_card(
                        "Baseline total",
                        _format_kg(total_emissions),
                        "Fabric blocks plus assembly processes",
                    ),
                    _co2_metric_card(
                        "Fabric blocks",
                        _format_kg(float(co2_data.fabric_blocks.total_emission)),
                        f"Raw {_format_kg(raw_material_total)} | Production {_format_kg(production_total)}",
                    ),
                    _co2_metric_card(
                        "Assembly",
                        _format_kg(float(co2_data.processes.total_emission)),
                        "Recipe-level assembly processes",
                    ),
                    _co2_metric_card(
                        "Second-life option",
                        (
                            _format_kg(alternative_emissions)
                            if has_second_life_alternatives
                            else "No match"
                        ),
                        (
                            f"Saves {_format_kg(potential_saving)}"
                            if has_second_life_alternatives
                            else "No second-life replacement available"
                        ),
                        "co2-metric-card-positive"
                        if has_second_life_alternatives
                        else "",
                    ),
                ],
                className="co2-metric-grid",
            ),
            html.Div(
                [
                    html.H4("Second-life alternatives"),
                    html.P(
                        (
                            "Replacement blocks avoid new raw material emissions, but add preparation and transport emissions."
                            if has_second_life_alternatives
                            else "No suitable second-life fabric block replacements were found for this material."
                        )
                    ),
                    _co2_table(
                        [
                            "Recipe block",
                            "Second-life ID",
                            "Material",
                            "Location",
                            "Quality",
                            "Preparation (kg CO2eq)",
                            "Transport (kg CO2eq)",
                            "Alternative total (kg CO2eq)",
                        ],
                        alternative_rows,
                        "No second-life fabric block replacements available.",
                    ),
                ],
                className="co2-detail-panel",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.H4("Fabric block recipe"),
                            _co2_table(
                                [
                                    "Fabric block",
                                    "Material",
                                    "Weight (kg)",
                                    "Raw material (kg CO2eq)",
                                    "Production (kg CO2eq)",
                                    "Processes",
                                ],
                                fabric_block_rows,
                                "No fabric blocks in recipe.",
                            ),
                        ],
                        className="co2-detail-panel",
                    ),
                    html.Div(
                        [
                            html.H4("Assembly processes"),
                            _co2_table(
                                ["Process", "Amount", "Emission (kg CO2eq)"],
                                assembly_process_rows,
                                "No assembly processes in recipe.",
                            ),
                        ],
                        className="co2-detail-panel",
                    ),
                ],
                className="co2-detail-grid",
            ),
            html.Div(
                [
                    html.H4("Contribution to total emissions"),
                    _co2_table(
                        [
                            "Type",
                            "Recipe item",
                            "Emission (kg CO2eq)",
                            "Share of total",
                        ],
                        contribution_rows,
                        "No contribution data available.",
                    ),
                ],
                className="co2-detail-panel",
            ),
        ],
        className="co2-assessment-card",
    )


def register_co2_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("co2-form-content", "children"),
        Input("co2-garment-id", "data"),
    )
    def load_co2_form(garment_id):
        if not garment_id:
            return html.Div("Garment not found.")

        garment_types = fetch_garment_types()
        garment_type = next((g for g in garment_types if g["id"] == garment_id), None)
        garment_name = garment_type["name"] if garment_type else f"Garment {garment_id}"

        materials = fetch_materials_for_garment(garment_id)
        if not materials:
            return html.Div(
                [
                    html.H3(garment_name),
                    html.P(
                        f"No materials configured for the recipe of {garment_name}."
                    ),
                ]
            )

        sections = []
        for material in materials:
            material_id = material["id"]
            material_name = material.get("name", "Unknown")
            co2_data = get_co2(garment_id, material_id)
            if not co2_data:
                sections.append(
                    html.Div(
                        [
                            html.H3(f"{garment_name} (material={material_name})"),
                            html.P("No recipe data available for this material."),
                            html.Hr(),
                        ]
                    )
                )
                continue

            sections.append(
                _build_material_co2_section(garment_name, material_name, co2_data)
            )

        return html.Div(sections, className="garment-designer-stack")
