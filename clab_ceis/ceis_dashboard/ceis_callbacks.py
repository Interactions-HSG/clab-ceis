#!/usr/bin/env python
from dash import Dash, Input, Output, State, callback_context, html, dcc
import requests
import pandas as pd
import math
from clab_ceis.ceis_dashboard import ceis_data
from clab_ceis import config
from dash.dependencies import ALL
from dash import no_update


def get_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    
    # Callback to add/remove preparation input fields
    @app.callback(
        Output("preparations-container", "children"),
        [
            Input("add-prep-button", "n_clicks"),
            Input("remove-prep-button", "n_clicks"),
        ],
        [State("preparations-container", "children")],
    )
    def update_preparation_fields(add_clicks, remove_clicks, children):
        ctx = callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        if children is None:
            children = []

        # Add a new preparation field
        if triggered == "add-prep-button":
            new_id = len(children)
            children.append(
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id={"type": "prep-name", "index": new_id},
                                    options=[
                                        {"label": "Sewing", "value": "1"},
                                        {"label": "Dyeing", "value": "3"},
                                        {"label": "Steaming", "value": "2"},
                                    ],
                                    placeholder="Select preparation",
                                    clearable=False,
                                    style={"width": "200px"},
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        html.Div(
                            [
                                dcc.Input(
                                    id={"type": "prep-count", "index": new_id},
                                    placeholder="Count",
                                    type="number",
                                    min=1,
                                    value=1,
                                    style={"width": "100px"},
                                ),
                            ],
                            style={"marginLeft": "12px"},
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "gap": "8px",
                        "marginBottom": "8px",
                    },
                )
            )

        # Remove the last preparation field
        elif triggered == "remove-prep-button" and len(children) > 0:
            children = children[:-1]

        return children

    @app.callback(
        Output("fabric-blocks-table", "data"),
        Output("fabric-add-status", "children"),
        [
            Input("refresh-fabric-blocks", "n_clicks"),
            Input("add-fabric-blocks", "n_clicks"),
        ],
        [
            State("fabric-type", "value"),
            State({"type": "prep-name", "index": ALL}, "value"),
            State({"type": "prep-count", "index": ALL}, "value"),
            State("fabric-blocks-table", "data"),  # keep current table data
        ],
    )
    def update_fabric_table(
        refresh_clicks, add_clicks, type_val, prep_names, prep_counts, current_data
    ):
        ctx = callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        status_msg = ""

        if not triggered:
            return fetch_fabric_blocks(), ""
        if triggered == "refresh-fabric-blocks":
            return fetch_fabric_blocks(), ""

        if triggered == "add-fabric-blocks":

            if not type_val:
                return no_update, "Please select a fabric type."

            preparations = []
            for name, count in zip(prep_names, prep_counts):
                if name:
                    try:
                        cnt = int(count) if count else 1
                    except:
                        cnt = 1

                    preparations.append({"type_id": name, "amount": cnt})

            payload = {"type_id": type_val, "preparations": preparations}
            print("Payload:", payload)
            try:
                resp = requests.post(
                    f"{config.BACKEND_API_URL}/fabric-block", json=payload
                )

                # Only update table if SUCCESS
                if resp.status_code in (200, 201):
                    status_msg = f"Successfully added fabric block with {len(preparations)} preparation(s)."

                    # Now fetch fresh data
                    return fetch_fabric_blocks(), status_msg

                else:
                    return no_update, f"Error adding fabric block: {resp.status_code}"

            except Exception as e:
                return no_update, f"Error connecting to backend: {str(e)}"

        return no_update, ""

    @app.callback(
        Output("res-dashboard-table", "data", allow_duplicate=True),
        Input("flow-chart", "tapEdgeData"),
        prevent_initial_call=True,
    )
    def onTapEdge(tapEdgeData):
        col_title = "EventTrigger"
        ce_data = data.get_data()
        filtered_data = ce_data[
            ce_data[col_title].str.contains(tapEdgeData["label"], case=False, na=False)
        ]
        return filtered_data.to_dict("records")

    @app.callback(
        Output("res-dashboard-table", "data"),
        Input("flow-chart", "tapNodeData"),
        prevent_initial_call=True,
    )
    def onTapNode(tapNodeData):
        col_title = "TO"
        ce_data = data.get_data()
        filtered_data = ce_data[
            ce_data[col_title].str.contains(tapNodeData["label"], case=False, na=False)
        ]
        return filtered_data.to_dict("records")

    @app.callback(
        Output("res-dashboard-table", "data", allow_duplicate=True),
        [Input("update-button", "n_clicks")],
        prevent_initial_call=True,
    )
    def update_table(n_clicks):
        return data.get_data().to_dict("records")

    @app.callback(
        Output("co2-form-content", "children"),
        Input("co2-form-load", "n_clicks"),
    )
    def load_co2_form(pathname):
        top_co2 = get_co2("croptop")
        skirt_co2 = get_co2("skirt")
        return html.Div(
            [
                html.H3("Crop Top CO2 Assessment"),
                html.P(f"Total CO2 Emissions for Crop Top: {top_co2} kg CO2eq"),
                html.H3("Skirt CO2 Assessment"),
                html.P(f"Total CO2 Emissions for Skirt: {skirt_co2} kg CO2eq"),
            ]
        )


def fetch_fabric_blocks():
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/fabric-blocks")

        if resp.status_code != 200:
            return []

        backend_data = resp.json()
        print("Fetched fabric blocks:", backend_data)

        for block in backend_data:
            preps = block.get("preparations", [])

            if isinstance(preps, list):
                block["preparations"] = ", ".join(
                    f"{p.get('type','')}({p.get('amount',0)})" for p in preps
                )
            else:
                block["preparations"] = str(preps)

        return backend_data

    except Exception:
        return []


def get_co2(garment_type: str) -> float:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/co2/{garment_type}")

        if resp.status_code != 200:
            return 0.0

        backend_data = resp.json()
        return backend_data.get("total_co2eq", 0.0)

    except Exception:
        return 0.0
