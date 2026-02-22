from __future__ import annotations

import requests
from dash import Dash, Input, Output, State, callback_context, html, dcc, no_update
from dash.dependencies import ALL

import config
from ceis_backend.models import FabricBlockInfo, PreparationInfo
import ceis_data
from .api import fetch_fabric_blocks


def register_fabric_block_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("fabric-type", "options"),
        Input("url", "pathname"),
    )
    def load_fabric_block_types(pathname):
        try:
            resp = requests.get(f"{config.BACKEND_API_URL}/fabric-block-types")

            if resp.status_code == 200:
                data = resp.json()

                return [{"label": fb["name"], "value": fb["id"]} for fb in data]

        except Exception:
            pass

        return []

    @app.callback(
        Output("fabric-location", "options"),
        Input("url", "pathname"),
    )
    def load_locations(pathname):
        try:
            resp = requests.get(f"{config.BACKEND_API_URL}/locations")

            if resp.status_code == 200:
                data = resp.json()

                return [{"label": loc["name"], "value": loc["id"]} for loc in data]

        except Exception:
            pass

        return []

    @app.callback(
        Output("delete-fabric-block-id", "options"),
        Input("url", "pathname"),
        Input("refresh-fabric-blocks", "n_clicks"),
        Input("add-fabric-blocks", "n_clicks"),
        Input("delete-fabric-block-button", "n_clicks"),
    )
    def load_fabric_block_inventory_options(
        pathname, refresh_clicks, add_clicks, delete_clicks
    ):
        blocks = fetch_fabric_blocks()
        return [
            {
                "label": f"{block.get('id')} - {block.get('type')}",
                "value": block.get("id"),
            }
            for block in blocks
        ]

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

            options = []
            try:
                resp = requests.get(f"{config.BACKEND_API_URL}/process-types")

                if resp.status_code == 200:
                    data = resp.json()

                    options = [
                        {"label": prep["name"], "value": prep["id"]}
                        for prep in data
                    ]

            except Exception:
                pass

            new_id = len(children)
            children.append(
                html.Div(
                    [
                        html.Div(
                            [
                                dcc.Dropdown(
                                    id={"type": "prep-name", "index": new_id},
                                    options=options,
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
        Output("fabric-remove-status", "children"),
        [
            Input("refresh-fabric-blocks", "n_clicks"),
            Input("add-fabric-blocks", "n_clicks"),
            Input("delete-fabric-block-button", "n_clicks"),
        ],
        [
            State("fabric-type", "value"),
            State("fabric-location", "value"),
            State({"type": "prep-name", "index": ALL}, "value"),
            State({"type": "prep-count", "index": ALL}, "value"),
            State("delete-fabric-block-id", "value"),
            State("fabric-blocks-table", "data"),
        ],
    )
    def update_fabric_table(
        refresh_clicks,
        add_clicks,
        delete_clicks,
        type_val,
        location_val,
        prep_names,
        prep_counts,
        delete_id,
        current_data,
    ):
        ctx = callback_context
        triggered = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

        if not triggered:
            return fetch_fabric_blocks(), "", ""
        if triggered == "refresh-fabric-blocks":
            return fetch_fabric_blocks(), "", ""

        if triggered == "add-fabric-blocks":

            if not type_val:
                return no_update, "Please select a fabric type.", ""

            preparations: list[PreparationInfo] = []
            for name, count in zip(prep_names, prep_counts):
                if name:
                    try:
                        cnt = int(count) if count else 1
                    except:
                        cnt = 1

                    preparations.append(PreparationInfo(type_id=name, time=cnt))

            payload = FabricBlockInfo(
                type_id=type_val,
                processes=preparations,
                location_id=location_val
            )
            print("Payload:", payload)
            try:
                resp = requests.post(
                    f"{config.BACKEND_API_URL}/fabric-blocks", json=payload.dict()
                )

                # Only update table if SUCCESS
                if resp.status_code in (200, 201):
                    status_msg = (
                        "Successfully added fabric block with "
                        f"{len(preparations)} preparation(s)."
                    )

                    # Now fetch fresh data
                    return fetch_fabric_blocks(), status_msg, ""

                else:
                    return (
                        no_update,
                        f"Error adding fabric block: {resp.status_code}",
                        "",
                    )

            except Exception as e:
                return no_update, f"Error connecting to backend: {str(e)}", ""

        if triggered == "delete-fabric-block-button":
            if not delete_id:
                return no_update, "", "Please select a fabric block to remove."

            try:
                resp = requests.delete(
                    f"{config.BACKEND_API_URL}/fabric-blocks/{delete_id}"
                )
                if resp.status_code in (200, 204):
                    return fetch_fabric_blocks(), "", "Fabric block removed."
                if resp.status_code == 404:
                    return no_update, "", "Fabric block not found."
                return (
                    no_update,
                    "",
                    f"Error removing fabric block: {resp.status_code}",
                )
            except Exception as e:
                return no_update, "", f"Error connecting to backend: {str(e)}"

        return no_update, "", ""
