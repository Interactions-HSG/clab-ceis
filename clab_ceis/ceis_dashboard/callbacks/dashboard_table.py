from __future__ import annotations
from dash import Dash, Input, Output, ctx

import ceis_data
from ceis_dashboard.callbacks.api import fetch_resource_events


def register_dashboard_table_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("lifecycle-events-table", "data"),
        Input("flow-chart", "tapEdgeData"),
        Input("flow-chart", "tapNodeData"),
        Input("lifecycle-events-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def filter_lifecycle_events(edge_data, node_data, _reset_clicks):
        if ctx.triggered_id == "flow-chart" and ctx.triggered_prop_ids.get(
            "flow-chart.tapEdgeData"
        ):
            return fetch_resource_events(lifecycle_edge=edge_data.get("label"))
        if ctx.triggered_id == "flow-chart" and node_data:
            return fetch_resource_events(lifecycle_node=node_data.get("label"))
        return fetch_resource_events()

    @app.callback(
        Output("supply-events-table", "data"),
        Input("supply-chain-chart", "tapNodeData"),
        Input("supply-chain-chart", "tapEdgeData"),
        Input("supply-events-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def filter_supply_events(node_data, edge_data, _reset_clicks):
        if ctx.triggered_id == "supply-chain-chart" and ctx.triggered_prop_ids.get(
            "supply-chain-chart.tapNodeData"
        ):
            if node_data.get("material_id") is not None:
                return fetch_resource_events(material_id=node_data["material_id"])
            return fetch_resource_events(
                manufacturer_id=node_data.get("manufacturer_id")
            )
        if ctx.triggered_id == "supply-chain-chart" and edge_data:
            if edge_data.get("material_manufacturer_distance_id") is not None:
                return fetch_resource_events(
                    material_manufacturer_distance_id=edge_data[
                        "material_manufacturer_distance_id"
                    ]
                )
            return fetch_resource_events(
                manufacturer_distance_id=edge_data.get("manufacturer_distance_id")
            )
        return fetch_resource_events(supply_chain_only=True)
