from __future__ import annotations

from dash import Dash, Input, Output, html

from clab_ceis.ceis_dashboard import ceis_data
from .api import get_co2


def register_co2_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("co2-form-content", "children"),
        Input("url", "pathname"),
    )
    def load_co2_form(pathname):
        used_fabric_block_ids_top = []
        alternative_co2_top = None
        used_fabric_block_ids_skirt = []
        alternative_co2_skirt = None

        top_co2 = get_co2("croptop")
        if top_co2:
            co2_from_used_fabric_blocks_top = sum(
                (fb["alternative"]["emission"] if fb["alternative"] else fb["emission"])
                for fb in top_co2.fabric_blocks.details
            )
            co2_from_preparations_top = sum(
                (fb["alternative"]["emission"] if fb["alternative"] else 0)
                for fb in top_co2.fabric_blocks.details
            )

            alternative_co2_top = (
                top_co2.processes.total_emission + co2_from_used_fabric_blocks_top
            )
            used_fabric_block_ids_top = [
                fb["alternative"]["id"]
                for fb in top_co2.fabric_blocks.details
                if fb["alternative"] and fb["alternative"]["id"] is not None
            ]
            replaced_fabric_blocks_co2_top = sum(
                fb["emission"]
                for fb in top_co2.fabric_blocks.details
                if fb["alternative"] and fb["alternative"]["id"] is not None
            )
        skirt_co2 = get_co2("skirt")
        if skirt_co2:
            co2_from_used_fabric_blocks_skirt = sum(
                (fb["alternative"]["emission"] if fb["alternative"] else fb["emission"])
                for fb in skirt_co2.fabric_blocks.details
            )
            co2_from_preparations_skirt = sum(
                (fb["alternative"]["emission"] if fb["alternative"] else 0)
                for fb in skirt_co2.fabric_blocks.details
            )
            alternative_co2_skirt = (
                skirt_co2.processes.total_emission + co2_from_used_fabric_blocks_skirt
            )
            used_fabric_block_ids_skirt = [
                fb["alternative"]["id"]
                for fb in skirt_co2.fabric_blocks.details
                if fb["alternative"] and fb["alternative"]["id"] is not None
            ]
            replaced_fabric_blocks_co2_skirt = sum(
                fb["emission"]
                for fb in skirt_co2.fabric_blocks.details
                if fb["alternative"] and fb["alternative"]["id"] is not None
            )

        top_total_emissions = (
            round(
                top_co2.fabric_blocks.total_emission
                + top_co2.processes.total_emission,
                2,
            )
            if top_co2
            else "N/A"
        )
        top_alternative_emissions = (
            round(alternative_co2_top, 2) if alternative_co2_top is not None else "N/A"
        )
        skirt_total_emissions = (
            round(
                skirt_co2.fabric_blocks.total_emission
                + skirt_co2.processes.total_emission,
                2,
            )
            if skirt_co2
            else "N/A"
        )
        skirt_alternative_emissions = (
            round(alternative_co2_skirt, 2)
            if alternative_co2_skirt is not None
            else "N/A"
        )

        return html.Div(
            [
                html.H3("Crop Top"),
                html.P(
                    [
                        "Total CO2 Emissions for Crop Top: ",
                        html.B(f"{top_total_emissions}"),
                        " kg CO2eq, comprising of ",
                        html.B(f"{round(top_co2.fabric_blocks.total_emission, 2)}"),
                        " kg CO2eq from fabric blocks (raw materials) and ",
                        html.B(f"{round(top_co2.processes.total_emission, 2)}"),
                        " kg CO2eq from assembly processes.",
                    ]
                ),
                html.P(
                    [
                        "Alternatively, by using second-hand fabric blocks with ids ",
                        html.B(f"{used_fabric_block_ids_top or 'N/A'}"),
                        ", the CO2 emissions can be reduced to: ",
                        html.B(f"{top_alternative_emissions}"),
                        " kg CO2eq. By reusing fabric blocks, their initial combined emissions of raw materials ",
                        html.B(f"{round(replaced_fabric_blocks_co2_top, 2)}"),
                        " kg CO2eq can be avoided, but the emissions from the preparation which amount to ",
                        html.B(f"{round(co2_from_preparations_top, 2)}"),
                        " kg CO2eq still remain.",
                    ]
                ),
                html.H3("Skirt"),
                html.P(
                    [
                        "Total CO2 Emissions for Skirt: ",
                        html.B(f"{skirt_total_emissions}"),
                        " kg CO2eq, comprising of ",
                        html.B(f"{round(skirt_co2.fabric_blocks.total_emission, 2)}"),
                        " kg CO2eq from fabric blocks (raw materials) and ",
                        html.B(f"{round(skirt_co2.processes.total_emission, 2)}"),
                        " kg CO2eq from assembly processes.",
                    ]
                ),
                html.P(
                    [
                        "Alternatively, by using second-hand fabric blocks with ids ",
                        html.B(f"{used_fabric_block_ids_skirt or 'N/A'}"),
                        ", the CO2 emissions can be reduced to: ",
                        html.B(f"{skirt_alternative_emissions}"),
                        " kg CO2eq. By reusing fabric blocks, their initial combined emissions of raw materials ",
                        html.B(f"{round(replaced_fabric_blocks_co2_skirt, 2)}"),
                        " kg CO2eq can be avoided, but the emissions from the preparation which amount to ",
                        html.B(f"{round(co2_from_preparations_skirt, 2)}"),
                        " kg CO2eq still remain.",
                    ]
                ),
            ]
        )
