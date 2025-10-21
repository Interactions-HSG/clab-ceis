#!/usr/bin/env python
from dash import Dash, Input, Output
import requests

from clab_ceis.ceis_dashboard import ceis_data
from clab_ceis import config



def get_callbacks(app: Dash, data: ceis_data.CeisData) -> None:

    @app.callback(
        Output("res-dashboard-table", "data", allow_duplicate=True),
        Input("flow-chart", "tapEdgeData"),
        prevent_initial_call=True,
    )
    def onTapEdge(tapEdgeData):
        # global ce_data
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

    # Callback to fetch fabric blocks from the backend /fabric-blocks endpoint
    @app.callback(
        Output("fabric-blocks-table", "data"),
        [Input("refresh-fabric-blocks", "n_clicks")],
    )
    def update_fabric_blocks(n_clicks):
        print('Fetching fabric blocks from backend...')
        try:
            resp = requests.get(f"{config.BACKEND_API_URL}/fabric-blocks")
            if resp.status_code == 200:
                data = resp.json()
                # flatten preparations
                for block in data:
                    block['preparations'] = ", ".join(
                        f"{p['type']}({p['amount']})" for p in block.get('preparations', [])
                    )
                return data
        except Exception as e:
            print('Error fetching fabric blocks:', e)
            pass
        return []