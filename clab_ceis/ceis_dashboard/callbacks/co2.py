from __future__ import annotations

from dash import Dash, Input, Output, html

import ceis_data
from .api import get_co2, fetch_garment_types


def register_co2_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("co2-form-content", "children"),
        Input("url", "pathname"),
    )
    def load_co2_form(pathname):
        # Fetch all garment types
        garment_types = fetch_garment_types()

        # Build sections for each garment type
        sections = []

        for garment_type in garment_types:
            garment_name = garment_type["name"]
            garment_id = garment_type["id"]

            # Get CO2 data for this garment type
            co2_data = get_co2(garment_id)

            if not co2_data:
                sections.extend(
                    [
                        html.H3(garment_name),
                        html.P(f"No recipe data available for {garment_name}."),
                    ]
                )
                continue

            # Calculate metrics
            co2_from_used_fabric_blocks = sum(
                (fb["alternative"]["emission"] if fb["alternative"] else fb["emission"])
                for fb in co2_data.fabric_blocks.details
            )
            co2_from_preparations = sum(
                (
                    sum(
                        prep["emission"]
                        for prep in fb["alternative"]["preparation_details"]
                    )
                    if fb["alternative"]
                    else 0
                )
                for fb in co2_data.fabric_blocks.details
            )
            co2_from_transport = sum(
                (
                    fb["alternative"].get("transport_emission", 0)
                    if fb["alternative"]
                    else 0
                )
                for fb in co2_data.fabric_blocks.details
            )

            alternative_co2 = (
                co2_data.processes.total_emission + co2_from_used_fabric_blocks
            )

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

            # Format output
            total_emissions = round(
                co2_data.fabric_blocks.total_emission
                + co2_data.processes.total_emission,
                2,
            )
            alternative_emissions = round(alternative_co2, 2)

            # Build HTML for this garment type
            sections.extend(
                [
                    html.H3(garment_name),
                    html.P(
                        [
                            f"Total CO2 Emissions for {garment_name}: ",
                            html.B(f"{total_emissions}"),
                            " kg CO2eq (excluding transportation to the customer), comprising of ",
                            html.B(
                                f"{round(co2_data.fabric_blocks.total_emission, 2)}"
                            ),
                            " kg CO2eq from fabric blocks (raw materials) and ",
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
                            " kg CO2eq can be avoided, but the emissions from the preparation which amount to ",
                            html.B(
                                f"{round(co2_from_preparations, 2) if co2_from_preparations else 'N/A'}"
                            ),
                            " kg CO2eq and transport emissions of ",
                            html.B(
                                f"{round(co2_from_transport, 2) if co2_from_transport else 'N/A'}"
                            ),
                            " kg CO2eq need to be added.",
                        ]
                    ),
                ]
            )

        return html.Div(sections)
