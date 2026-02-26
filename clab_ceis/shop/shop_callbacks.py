import copy
import sys
from pathlib import Path

import httpx
import requests
import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output, State

from . import config

sys.path.insert(0, str(Path(__file__).parent.parent / "ceis_dashboard"))


def get_callbacks(app):
    @app.callback(
        Output("customer-repair-content", "children"),
        Input("url", "pathname"),
    )
    def load_customer_repair_content(pathname):
        amount_kg = 0.131  # Weight of crop top: 80 x 64 + 2 * 40 x 14 = 0.624 m2, 0.131 kg/m2 (with 210 g/m2 fabric)
        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/co2/repair",
                params={"amount_kg": amount_kg, "replacements": ["40x14"]},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            scenarios = payload.get("scenarios", [])
            replacement_blocks = payload.get("replacement_fabric_blocks", {})
        except Exception as e:
            print(f"Error fetching repair CO2 data: {e}")
            return html.Div("Unable to load repair CO2 comparison.")

        scenario_labels = []
        scenario_values = []
        for scenario in scenarios:
            scenario_labels.append(scenario.get("use_case", "Scenario"))
            scenario_values.append(scenario.get("co2_kg", 0))

        block_details = replacement_blocks.get("details", [])
        block_material_emission = 0
        processes = []
        if block_details:
            block_material_emission = block_details[0].get("material_emission", 0)
            processes = block_details[0].get("processes", [])

        fig = go.Figure()
        fig.add_bar(
            name="Scenario transport CO2",
            x=scenario_labels,
            y=scenario_values,
        )
        fig.add_bar(
            name="Replacement material emission",
            x=scenario_labels,
            y=[block_material_emission] * len(scenario_labels),
        )
        for process in processes:
            process_name = process.get("process", "Unknown Process")
            process_emission = process.get("emission", 0)
            fig.add_bar(
                name=f"Replacement {process_name}",
                x=scenario_labels,
                y=[process_emission] * len(scenario_labels),
            )
        fig.update_layout(
            barmode="stack",
            title="Repairing a crop top using a new replacement fabric block (40x14).",
            xaxis_title="End of Life Scenario",
            yaxis_title="CO2 (kg CO2eq)",
            legend_title_text="Metric",
            margin=dict(l=20, r=20, t=40, b=20),
        )

        return html.Div(
            dcc.Graph(figure=fig),
        )
