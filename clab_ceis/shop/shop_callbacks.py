import sys
import requests

import plotly.graph_objects as go
from pathlib import Path
from dash import dcc, html
from dash.dependencies import Input, Output

from shop import config

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

        # Fetch CO2 data for new garment
        new_garment_co2 = None
        try:
            garment_response = requests.get(
                f"{config.BACKEND_API_URL}/co2/1",
                timeout=10,
            )
            garment_response.raise_for_status()
            new_garment_data = garment_response.json()

            fabric_blocks_data = new_garment_data.get("fabric_blocks", {})
            processes_data = new_garment_data.get("processes", {})

            new_garment_co2 = {
                "fabric_total": fabric_blocks_data.get("total_emission", 0),
                "processes_total": processes_data.get("total_emission", 0),
                "fabric_details": fabric_blocks_data.get("details", []),
                "process_details": processes_data.get("details", []),
            }
        except Exception as e:
            print(f"Error fetching new garment CO2 data: {e}")

        scenario_labels = []
        scenario_values = []
        for scenario in scenarios:
            scenario_labels.append(scenario.get("use_case", "Scenario"))
            scenario_values.append(scenario.get("co2_kg", 0))

        # Add "Buy New" scenario with transport emissions
        # Use the same transport distance as shipping from production (Bucharest to customer)
        buy_new_transport = 0
        if new_garment_co2 and scenarios:
            # Use transport emission from first scenario (Bucharest to customer) for new garment
            buy_new_transport = (
                scenarios[0].get("co2_kg", 0)
                if scenarios[0].get("co2_kg") is not None
                else 0
            )
            scenario_labels.append("Buy New")
            scenario_values.append(buy_new_transport)

        block_details = replacement_blocks.get("details", [])
        block_material_emission = 0
        processes = []
        if block_details:
            block_material_emission = block_details[0].get("material_emission", 0)
            processes = block_details[0].get("processes", [])

        fig = go.Figure()
        fig.add_bar(
            name="Transport to/from customer",
            x=scenario_labels,
            y=scenario_values,
        )

        # Add replacement material emission
        replacement_values = [block_material_emission] * (
            len(scenario_labels) - (1 if new_garment_co2 else 0)
        )
        if new_garment_co2:
            replacement_values.append(0)  # No replacement material for "Buy New"
        fig.add_bar(
            name="Fabric Block to be replaced fabric material",
            x=scenario_labels,
            y=replacement_values,
        )

        # Add replacement process emissions
        for process in processes:
            process_name = process.get("process", "Unknown Process")
            process_emission = process.get("emission", 0)
            process_values = [process_emission] * (
                len(scenario_labels) - (1 if new_garment_co2 else 0)
            )
            if new_garment_co2:
                process_values.append(0)  # No replacement process for "Buy New"
            fig.add_bar(
                name=f"Fabric Block to be replaced process: {process_name}",
                x=scenario_labels,
                y=process_values,
            )

        # Add new garment fabric blocks emissions (split into material and individual processes)
        if new_garment_co2:
            # Add material emissions
            total_material_emission = sum(
                detail.get("material_emission", 0)
                for detail in new_garment_co2["fabric_details"]
            )
            material_values = [0] * (len(scenario_labels) - 1) + [
                total_material_emission
            ]
            fig.add_bar(
                name="New garment fabric material",
                x=scenario_labels,
                y=material_values,
            )

            # Add production emissions broken down by individual processes
            production_processes_totals = {}
            for detail in new_garment_co2["fabric_details"]:
                production_processes = detail.get("production_processes", [])
                for process in production_processes:
                    process_name = process.get("process", "Unknown")
                    process_emission = process.get("emission", 0)
                    if process_name not in production_processes_totals:
                        production_processes_totals[process_name] = 0
                    production_processes_totals[process_name] += process_emission

            for process_name, total_emission in production_processes_totals.items():
                production_process_values = [0] * (len(scenario_labels) - 1) + [
                    total_emission
                ]
                fig.add_bar(
                    name=f"New garment production process: {process_name}",
                    x=scenario_labels,
                    y=production_process_values,
                )

            # Add new garment process emissions
            for process_detail in new_garment_co2["process_details"]:
                process_name = process_detail.get("process", "Unknown")
                process_emission = process_detail.get("emission", 0)
                process_values = [0] * (len(scenario_labels) - 1) + [process_emission]
                fig.add_bar(
                    name=f"New garment production process: {process_name}",
                    x=scenario_labels,
                    y=process_values,
                )

        fig.update_layout(
            barmode="stack",
            title="CO2 Comparison: Repair vs Buy New Crop Top",
            xaxis_title="Scenario",
            yaxis_title="CO2 (kg CO2eq)",
            legend_title_text="Emission Source",
            margin=dict(l=20, r=20, t=40, b=20),
        )

        return html.Div(
            dcc.Graph(figure=fig),
        )
