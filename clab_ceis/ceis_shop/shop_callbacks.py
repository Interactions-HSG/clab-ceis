import sys
import requests
from pathlib import Path

import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output

from ceis_shop import config

sys.path.insert(0, str(Path(__file__).parent.parent / "ceis_dashboard"))


def get_callbacks(app):
    @app.callback(
        Output("customer-repair-content", "children"),
        Input("url", "pathname"),
    )
    def load_customer_repair_content(pathname):
        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/scenarios",
            )
            response.raise_for_status()
            body = response.json()
            scenarios = body
        except Exception as e:
            print(f"Error fetching repair CO2 data: {e}")
            return html.Div("Unable to load repair CO2 comparison.")

        # Extract all unique activities across all scenarios
        all_activities = set()
        scenario_activity_map = {}

        for scenario in scenarios:
            scenario_label = scenario.get("label", "Scenario")
            activities = scenario.get("activities", [])
            scenario_activity_map[scenario_label] = {}

            for activity in activities:
                activity_name = activity.get("name", "Unknown Activity")
                emission = activity.get("costs", {}).get("co2_kg", 0)
                scenario_activity_map[scenario_label][activity_name] = emission
                all_activities.add(activity_name)

        # Sort scenario labels to maintain consistent order
        scenario_labels = [s.get("label", "Scenario") for s in scenarios]

        # Create bar chart with activities as separate traces
        fig = go.Figure()

        for activity_name in sorted(all_activities):
            activity_values = []
            for scenario_label in scenario_labels:
                emission = scenario_activity_map.get(scenario_label, {}).get(
                    activity_name, 0
                )
                activity_values.append(emission)

            fig.add_bar(
                name=activity_name,
                x=scenario_labels,
                y=activity_values,
            )

        fig.update_layout(
            barmode="stack",
            title="CO2 Comparison: Different Repairing Options (replacement of the fabric block 64x40) vs Buying new 'Basic Trousers'",
            xaxis_title="Scenario",
            yaxis_title="CO2 (kg CO2eq)",
            # legend_title_text="Emissions",
            margin=dict(l=20, r=20, t=40, b=20),
        )

        return html.Div(
            dcc.Graph(figure=fig),
        )
