from __future__ import annotations

from dash import Dash, Input, Output, html, dash_table
import requests

import config


def register_repair_callbacks(app: Dash) -> None:
    @app.callback(
        Output("customer-repair-content", "children"),
        Input("url", "pathname"),
    )
    def load_customer_repair_content(pathname):
        amount_kg = 1.0
        try:
            response = requests.get(
                f"{config.BACKEND_API_URL}/co2/repair",
                params={"amount_kg": amount_kg},
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
            scenarios = payload.get("scenarios", [])
        except Exception as e:
            print(f"Error fetching repair CO2 data: {e}")
            return html.Div("Unable to load repair CO2 comparison.")

        rows = []
        for scenario in scenarios:
            co2_value = scenario.get("co2_kg")
            rows.append(
                {
                    "use_case": scenario.get("use_case"),
                    "route": scenario.get("route"),
                    "distance_km": scenario.get("distance_km"),
                    "co2_kg": round(co2_value, 4) if co2_value is not None else "N/A",
                }
            )

        table = dash_table.DataTable(
            columns=[
                {"name": "Use case", "id": "use_case"},
                {"name": "Route", "id": "route"},
                {"name": "Distance (km)", "id": "distance_km"},
                {"name": "CO2 (kg CO2eq)", "id": "co2_kg"},
            ],
            data=rows,
            style_table={"maxWidth": "900px"},
            style_cell={"textAlign": "left", "padding": "6px"},
            style_header={"fontWeight": "bold"},
        )

        return html.Div(
            [
                html.P(
                    "Assumes 1 kg of textile to be repaired and transported by truck. Excluding repair process emissions."
                ),
                html.P(
                    "Sites: Manufacturer Bucharest, Repair Center St. Gallen, Consumer Sigmaringen."
                ),
                table,
            ]
        )
