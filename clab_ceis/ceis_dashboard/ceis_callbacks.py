#!/usr/bin/env python
from clab_ceis.ceis_backend.models import Co2Response, FabricBlock, FabricBlockInfo, PreparationInfo
from dash import Dash, Input, Output, State, callback_context, html, dcc
import requests
import pandas as pd
import math
from clab_ceis.ceis_dashboard import ceis_data
from clab_ceis import config
from dash.dependencies import ALL
from dash import no_update


def get_callbacks(app: Dash, data: ceis_data.CeisData) -> None:

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

    # @app.callback(
    #     Output("prep-name", "options"),
    #     Input("url", "pathname"),
    # )
    # def load_preparation_types(pathname):
    #     try:
    #         resp = requests.get(f"{config.BACKEND_API_URL}/process-types")
    #         print("Preparation types response:", resp)

    #         if resp.status_code == 200:
    #             data = resp.json()

    #             return [
    #                 {"label": prep["name"], "value": prep["id"]}
    #                 for prep in data
    #             ]

    #     except Exception:
    #         pass

    #     return []

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
                        {"label": prep["name"], "value": prep["id"]} for prep in data
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
                                    # {"label": "Sewing", "value": "1"},
                                    # {"label": "Dyeing", "value": "3"},
                                    # {"label": "Steaming", "value": "2"},
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

            preparations: list[PreparationInfo] = []
            for name, count in zip(prep_names, prep_counts):
                if name:
                    try:
                        cnt = int(count) if count else 1
                    except:
                        cnt = 1

                    # preparations.append({"type_id": name, "amount": cnt})
                    preparations.append(PreparationInfo(type_id=name, time=cnt))

            payload = FabricBlockInfo(type_id=type_val, processes=preparations)
            print("Payload:", payload)
            try:
                resp = requests.post(
                    f"{config.BACKEND_API_URL}/fabric-block", json=payload.dict()
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
                top_co2.fabric_blocks.total_emission + top_co2.processes.total_emission,
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


def fetch_fabric_blocks():
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/fabric-blocks")

        if resp.status_code != 200:
            return []

        backend_data = resp.json()

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


def get_co2(garment_type: str) -> Co2Response | None:
    try:
        resp = requests.get(f"{config.BACKEND_API_URL}/co2/{garment_type}")
        if resp.status_code != 200:
            return None

        data = resp.json()
        print(f"CO2 data for {garment_type}:", data)
        return Co2Response(**data)

    except Exception as e:
        print(e)
        return None
