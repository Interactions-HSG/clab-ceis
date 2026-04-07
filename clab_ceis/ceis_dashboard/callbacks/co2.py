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

    alternative_co2 = co2_data.processes.total_emission + co2_from_used_fabric_blocks

    used_fabric_block_ids = [
        fb["alternative"]["id"]
        for fb in co2_data.fabric_blocks.details
        if fb["alternative"] and fb["alternative"]["id"] is not None
    ]

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

    recipe_fabric_blocks = []
    for fb in co2_data.fabric_blocks.details:
        production_processes = fb.get("production_processes", [])
        if production_processes:
            process_text = ", ".join(
                f"{proc.get('process', 'Unknown')} ({proc.get('amount', 0)})"
                for proc in production_processes
            )
        else:
            process_text = "none"

        recipe_fabric_blocks.append(
            html.Li(
                f"{fb.get('fabric_block', 'Unknown')} | material: {fb.get('material', 'Unknown')} | production processes: {process_text}"
            )
        )

    recipe_processes = []
    for proc in co2_data.processes.details:
        recipe_processes.append(
            html.Li(
                f"{proc.get('process', 'Unknown')} | amount: {proc.get('duration', 0)}"
            )
        )

    contribution_rows = []
    for fb in co2_data.fabric_blocks.details:
        fabric_block_name = fb.get("fabric_block", "Unknown")
        raw_material_emission = float(fb.get("material_emission", 0))
        production_emission = float(fb.get("production_emission", 0))
        contribution_rows.append(
            html.Tr(
                [
                    html.Td("Fabric Block (Raw Material)"),
                    html.Td(fabric_block_name),
                    html.Td(_format_kg(raw_material_emission)),
                    html.Td(_format_percent(raw_material_emission, total_emissions)),
                ]
            )
        )
        contribution_rows.append(
            html.Tr(
                [
                    html.Td("Fabric Block (Production Process)"),
                    html.Td(fabric_block_name),
                    html.Td(_format_kg(production_emission)),
                    html.Td(_format_percent(production_emission, total_emissions)),
                ]
            )
        )

    for proc in co2_data.processes.details:
        emission = float(proc.get("emission", 0))
        contribution_rows.append(
            html.Tr(
                [
                    html.Td("Assembly Process"),
                    html.Td(proc.get("process", "Unknown")),
                    html.Td(_format_kg(emission)),
                    html.Td(_format_percent(emission, total_emissions)),
                ]
            )
        )

    return html.Div(
        [
            html.H3(f"{garment_name} (material={material_name})"),
            html.P(
                [
                    f"Total CO2 Emissions for {garment_name}: ",
                    html.B(f"{total_emissions}"),
                    " kg CO2eq (excluding transportation to the customer), comprising of ",
                    html.B(f"{round(co2_data.fabric_blocks.total_emission, 2)}"),
                    " kg CO2eq from fabric blocks (",
                    html.B(f"{round(raw_material_total, 2)}"),
                    " kg CO2eq raw materials + ",
                    html.B(f"{round(production_total, 2)}"),
                    " kg CO2eq production processes) and ",
                    html.B(f"{round(co2_data.processes.total_emission, 2)}"),
                    " kg CO2eq from assembly processes.",
                ]
            ),
            html.P(
                [
                    "Alternatively, by using second-hand fabric blocks with ids ",
                    html.B(f"{used_fabric_block_ids or 'N/A'}"),
                    ", the CO2 emissions can be reduced to: ",
                    html.B(f"{alternative_emissions}"),
                    " kg CO2eq. By reusing fabric blocks, their initial combined emissions of raw materials ",
                    html.B(
                        f"{round(replaced_fabric_blocks_co2, 2) if replaced_fabric_blocks_co2 else 'N/A'}"
                    ),
                    " kg CO2eq can be avoided, but the emissions from the added processes which amount to ",
                    html.B(
                        f"{round(co2_from_inventory_processes, 2) if co2_from_inventory_processes else 'N/A'}"
                    ),
                    " kg CO2eq and transport emissions of ",
                    html.B(
                        f"{round(co2_from_transport, 2) if co2_from_transport else 'N/A'}"
                    ),
                    " kg CO2eq need to be added.",
                ]
            ),
            html.H4("Recipe"),
            html.H5("Fabric Blocks"),
            html.Ul(recipe_fabric_blocks or [html.Li("No fabric blocks in recipe.")]),
            html.H5("Assembly Processes"),
            html.Ul(recipe_processes or [html.Li("No assembly processes in recipe.")]),
            html.H4("Contribution to Total Emissions"),
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th("Type"),
                                html.Th("Recipe Item"),
                                html.Th("Emission"),
                                html.Th("Share of total"),
                            ]
                        )
                    ),
                    html.Tbody(contribution_rows),
                ],
                style={"width": "100%", "maxWidth": "900px"},
            ),
            html.Hr(),
        ]
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

            sections.append(_build_material_co2_section(garment_name, material_name, co2_data))

        return html.Div(sections)
