import sys
import requests
from pathlib import Path

import plotly.graph_objects as go
from dash import dcc, html
from dash.dependencies import Input, Output

from ceis_shop import config
from ceis_shop.layouts.garment import (
    render_co2_content,
    render_waiting_for_material_co2_content,
)

sys.path.insert(0, str(Path(__file__).parent.parent / "ceis_dashboard"))


def get_callbacks(app):
    @app.callback(
        Output("customer-repair-content", "children"),
        Input("url", "pathname"),
    )
    def load_customer_repair_content(pathname):
        if pathname != "/scenarios":
            return html.Div()

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
            title="CO2 Comparison: Different Repairing Options (replacement of the fabric block 64x40) vs Buying new 'Basic Crop Top'",
            xaxis_title="Scenario",
            yaxis_title="CO2 (kg CO2eq)",
            # legend_title_text="Emissions",
            margin=dict(l=20, r=20, t=40, b=20),
        )

        return html.Div(
            dcc.Graph(figure=fig),
        )

    @app.callback(
        Output("garment-co2-content", "children"),
        Input("garment-material-dropdown", "value"),
        Input("garment-type-id-store", "data"),
        Input("garment-materials-store", "data"),
        Input("garment-base-price-store", "data"),
    )
    def update_garment_recipe_and_co2(
        material_id, garment_type_id, materials, garment_base_price
    ):
        if not garment_type_id or not materials:
            unavailable = html.Div("Material and garment information is unavailable.")
            return unavailable

        if material_id is None:
            return render_waiting_for_material_co2_content()

        selected_material = next(
            (material for material in materials if material.get("id") == material_id),
            None,
        )
        selected_material_name = (
            selected_material.get("name") if selected_material else "Unknown"
        )

        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/co2/{garment_type_id}?material_id={material_id}",
                timeout=30,
            )
            response.raise_for_status()
            co2_payload = response.json()
        except Exception as exc:
            co2_error = html.Div(
                [
                    html.H3("CO2 Emissions"),
                    html.P("Unable to calculate CO2 for selected material."),
                    html.P(str(exc)),
                ]
            )
            return co2_error

        return render_co2_content(
            selected_material_name, co2_payload, garment_base_price
        )
