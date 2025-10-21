#!/usr/bin/env python
from dash import Dash, Input, Output, State, callback_context, html, dcc
import requests
import pandas as pd
import math
from clab_ceis.ceis_dashboard import ceis_data
from clab_ceis import config
from dash.dependencies import ALL


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
                                        {"label": "Sewing", "value": "sewing"},
                                        {"label": "Dyeing", "value": "dyeing"},
                                        {"label": "Steaming", "value": "steaming"},
                                        {"label": "Cutting", "value": "cutting"},
                                        {"label": "Washing", "value": "washing"},
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
        ],
    )
    def update_fabric_table(refresh_clicks, add_clicks, type_val, prep_names, prep_counts):
        ctx = callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        status_msg = ""

        # If add button triggered
        if triggered == "add-fabric-blocks":
            if not type_val:
                return [], "Please select a fabric type."
            
            # Build preparations list from dynamic inputs
            preparations = []
            for name, count in zip(prep_names, prep_counts):
                if name:  # Only add if name is selected
                    try:
                        cnt = int(count) if count else 1
                    except:
                        cnt = 1
                    preparations.append({
                        "type": name,
                        "amount": cnt
                    })

            # Send to backend API
            try:
                payload = {
                    "type": type_val,
                    "preparations": preparations
                }
                resp = requests.post(
                    f"{config.BACKEND_API_URL}/fabric-block",
                    json=payload
                )
                if resp.status_code in [200, 201]:
                    status_msg = f"Successfully added fabric block with {len(preparations)} preparation(s)."
                else:
                    status_msg = f"Error adding fabric block: {resp.status_code}"
            except Exception as e:
                status_msg = f"Error connecting to backend: {str(e)}"

        # Fetch backend data (on refresh or after add)
        try:
            resp = requests.get(f"{config.BACKEND_API_URL}/fabric-blocks")
            if resp.status_code == 200:
                backend_data = resp.json()
                # Format preparations for display
                for block in backend_data:
                    preps = block.get('preparations', [])
                    if isinstance(preps, list):
                        block['preparations'] = ", ".join(
                            f"{p.get('type', '')}({p.get('amount', 1)})" for p in preps
                        )
                    else:
                        block['preparations'] = str(preps)
                return backend_data, status_msg
            else:
                return [], status_msg or f"Error fetching data: {resp.status_code}"
        except Exception as e:
            return [], status_msg or f"Error connecting to backend: {str(e)}"

    # Your existing callbacks...
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


