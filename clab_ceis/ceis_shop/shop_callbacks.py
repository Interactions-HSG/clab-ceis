import sys
import requests
from pathlib import Path

import plotly.graph_objects as go
from dash import ctx, dcc, html
from dash.dependencies import Input, Output, State

from ceis_shop import config
from ceis_shop.layouts.garment import (
    render_co2_content,
    render_returned_garment_comparison,
    render_waiting_for_material_co2_content,
)
from ceis_shop.layouts.scenarios import (
    render_scenario_explorer,
    render_scenario_results,
)

sys.path.insert(0, str(Path(__file__).parent.parent / "ceis_dashboard"))


def get_callbacks(app):
    @app.callback(
        Output("garment-order-result", "children"),
        Input("garment-order-button", "n_clicks"),
        State("garment-type-id-store", "data"),
        State("garment-material-dropdown", "value"),
        prevent_initial_call=True,
    )
    def place_order(n_clicks, garment_type_id, material_id):
        if not n_clicks:
            return html.Div()
        if material_id is None:
            return html.P("Select a material before placing the order.")
        try:
            response = requests.post(
                f"{config.BACKEND_API_URL}/orders",
                json={
                    "garment_type_id": garment_type_id,
                    "material_id": material_id,
                },
                timeout=30,
            )
            response.raise_for_status()
            order = response.json()
        except Exception as exc:
            return html.P(f"Unable to place order: {exc}")

        if order.get("fulfillment_type") == "stock":
            message = "In stock — delivery has started."
        else:
            message = "Not in stock — production has been requested."
        return html.Div(
            [html.Strong(f"Order #{order['id']}"), html.P(message)],
            className="panel-muted",
        )

    @app.callback(
        Output("returned-garment-order-result", "children"),
        Input("returned-garment-order-button", "n_clicks"),
        State("garment-type-id-store", "data"),
        State("garment-material-dropdown", "value"),
        State("returned-garment-dropdown", "value"),
        prevent_initial_call=True,
    )
    def place_returned_garment_order(
        n_clicks, garment_type_id, material_id, garment_inventory_id
    ):
        if not n_clicks:
            return html.Div()
        try:
            response = requests.post(
                f"{config.BACKEND_API_URL}/orders",
                json={
                    "garment_type_id": garment_type_id,
                    "material_id": material_id,
                    "garment_inventory_id": garment_inventory_id,
                },
                timeout=30,
            )
            response.raise_for_status()
            order = response.json()
        except Exception as exc:
            return html.P(f"Unable to order returned garment: {exc}")

        return html.Div(
            [
                html.Strong(f"Order #{order['id']}"),
                html.P(
                    f"Returned garment reserved for CHF {float(order['price_chf']):.2f}. "
                    "Delivery has started."
                ),
            ],
            className="panel-muted",
        )

    @app.callback(
        Output("returned-garment-comparison", "children"),
        Input("garment-material-dropdown", "value"),
        Input("returned-garment-dropdown", "value"),
        State("garment-type-id-store", "data"),
    )
    def update_returned_garment_comparison(
        material_id, garment_inventory_id, garment_type_id
    ):
        if material_id is None:
            return "Select a material above to compare it with the equivalent new garment."
        if garment_inventory_id is None:
            return "No returned garment is currently available."
        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/garment-types/{garment_type_id}/"
                f"returned-garments/{garment_inventory_id}/co2-comparison"
                f"?material_id={material_id}",
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:
            return html.P(f"Unable to calculate returned-garment CO2: {exc}")

        return render_returned_garment_comparison(payload)

    @app.callback(
        Output("customer-repair-content", "children"),
        Input("url", "pathname"),
    )
    def load_end_of_life_content(pathname):
        if pathname != "/scenarios":
            return html.Div()

        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/scenarios",
            )
            response.raise_for_status()
            scenarios = response.json()
        except Exception as exc:
            print(f"Error fetching repair CO2 data: {exc}")
            return html.Div("Unable to load repair CO2 comparison.")

        all_activities = set()
        scenario_activity_map = {}
        for scenario in scenarios:
            scenario_label = scenario.get("label", "Scenario")
            scenario_activity_map[scenario_label] = {}
            for activity in scenario.get("activities", []):
                activity_name = activity.get("name", "Unknown Activity")
                emission = activity.get("costs", {}).get("co2_kg", 0)
                scenario_activity_map[scenario_label][activity_name] = emission
                all_activities.add(activity_name)

        scenario_labels = [
            scenario.get("label", "Scenario") for scenario in scenarios
        ]
        figure = go.Figure()
        for activity_name in sorted(all_activities):
            figure.add_bar(
                name=activity_name,
                x=scenario_labels,
                y=[
                    scenario_activity_map.get(label, {}).get(activity_name, 0)
                    for label in scenario_labels
                ],
            )

        figure.update_layout(
            barmode="stack",
            title=(
                "CO2 Comparison: Different Repairing Options (replacement of "
                "the fabric block 64x40) vs Buying new 'Basic Crop Top'"
            ),
            xaxis_title="Scenario",
            yaxis_title="CO2 (kg CO2eq)",
            margin={"l": 20, "r": 20, "t": 40, "b": 20},
        )
        return html.Div(dcc.Graph(figure=figure))

    @app.callback(
        Output("customer-circular-content", "children"),
        Input("url", "pathname"),
    )
    def load_customer_circular_content(pathname):
        if pathname != "/repair-return":
            return html.Div()

        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/circular-scenarios/options",
                timeout=30,
            )
            response.raise_for_status()
            return render_scenario_explorer(response.json())
        except Exception as exc:
            print(f"Error fetching circular scenario options: {exc}")
            return html.Div("Unable to load repair and return comparisons.")

    @app.callback(
        Output("circular-scenario-results", "children"),
        Input("circular-garment", "value"),
        Input("circular-distance", "value"),
        Input("circular-damage", "value"),
        Input("circular-use-higher-electricity-factor", "value"),
    )
    def update_customer_circular_scenarios(
        garment_id, distance_km, damage_code, electricity_mode
    ):
        if garment_id is None or distance_km is None or damage_code is None:
            return html.P("Select a garment, distance, and damage type.")

        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/circular-scenarios/{garment_id}",
                params={
                    "distance_km": distance_km,
                    "damage_code": damage_code,
                    "use_higher_electricity_factor": "higher_factor"
                    in (electricity_mode or []),
                },
                timeout=30,
            )
            response.raise_for_status()
            return render_scenario_results(response.json())
        except Exception as exc:
            print(f"Error fetching circular scenario calculation: {exc}")
            return html.Div("Unable to calculate the selected scenarios.")

    @app.callback(
        Output("circular-repair-order-result", "children"),
        Input("order-self-repair-kit", "n_clicks"),
        Input("request-professional-repair", "n_clicks"),
        State("circular-garment", "value"),
        State("circular-damage", "value"),
        prevent_initial_call=True,
    )
    def create_repair_order(
        _self_repair_clicks,
        _professional_repair_clicks,
        garment_id,
        damage_code,
    ):
        actions = {
            "order-self-repair-kit": "self_repair_kit",
            "request-professional-repair": "professional_repair",
        }
        action = actions.get(ctx.triggered_id)
        if action is None or garment_id is None or damage_code is None:
            return html.P("Select a garment and damage type before ordering.")

        try:
            response = requests.post(
                f"{config.BACKEND_API_URL}/repairs",
                json={
                    "garment_id": garment_id,
                    "action": action,
                    "damage_code": damage_code,
                },
                timeout=30,
            )
            response.raise_for_status()
            repair = response.json()
        except Exception as exc:
            return html.P(f"Unable to create repair request: {exc}")

        return html.Div(
            [
                html.Strong(f"Repair request #{repair['id']}"),
                html.P(f"{repair['action_label']} · {repair['status']}"),
            ],
            className="panel-muted",
        )

    @app.callback(
        Output("circular-garment-return-result", "children"),
        Input("return-garment-button", "n_clicks"),
        State("circular-garment", "value"),
        State("circular-damage", "value"),
        prevent_initial_call=True,
    )
    def return_garment(n_clicks, garment_id, damage_code):
        if not n_clicks or garment_id is None or damage_code is None:
            return html.P("Select a garment and damage type before returning it.")

        try:
            response = requests.post(
                f"{config.BACKEND_API_URL}/garment-returns",
                json={
                    "garment_id": garment_id,
                    "damage_code": damage_code,
                },
                timeout=30,
            )
            response.raise_for_status()
            returned = response.json()
        except Exception as exc:
            return html.P(f"Unable to return garment: {exc}")

        return html.Div(
            [
                html.Strong(
                    f"Returned garment #{returned['garment_id']} added to inventory"
                ),
                html.P(
                    f"{returned['fabric_block_count']} corresponding fabric blocks "
                    "were added with the whole-garment processes."
                ),
            ],
            className="panel-muted",
        )

    @app.callback(
        Output("circular-detailed-charts", "hidden"),
        Output("toggle-circular-charts", "children"),
        Input("toggle-circular-charts", "n_clicks"),
        prevent_initial_call=True,
    )
    def toggle_circular_charts(n_clicks):
        charts_are_open = bool(n_clicks and n_clicks % 2)
        button_label = (
            "Hide detailed bar charts"
            if charts_are_open
            else "View detailed bar charts"
        )
        return not charts_are_open, button_label

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
        material_cost_per_sqm_chf = (
            selected_material.get("cost_per_sqm_chf") if selected_material else None
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
            selected_material_name,
            co2_payload,
            garment_base_price,
            material_cost_per_sqm_chf,
        )
