from __future__ import annotations

from dash import Dash, Input, Output, ctx, no_update
from dash.dependencies import ALL

import ceis_data
from ceis_dashboard.callbacks.api import fetch_orders, ship_order
from pages.order_table import render_orders_table


def register_order_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("orders-table-container", "children"),
        Output("order-action-status", "children"),
        Input({"type": "ship-order", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def complete_order(_ship_clicks):
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            return no_update, no_update

        order_id = triggered_id.get("index")
        result = ship_order(order_id)
        if result.get("error"):
            return no_update, f"Unable to ship order #{order_id}: {result['error']}"

        return (
            render_orders_table(fetch_orders()),
            f"Order #{order_id} shipped. Garment #{result['garment_inventory_id']} "
            "is recorded as sold.",
        )
