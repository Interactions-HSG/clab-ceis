from __future__ import annotations

from dash import Dash, Input, Output, State, ctx, html, no_update
from dash.dependencies import ALL

import ceis_data
from ceis_dashboard.callbacks.api import (
    disassemble_returned_garment,
    fetch_orders,
    fetch_returned_garment_alternatives,
    fetch_returned_garments,
    ship_order,
)
from pages.order_table import (
    render_orders_table,
    render_return_alternative_details,
    render_returned_garments_table,
)


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

    @app.callback(
        Output("returned-garments-table-container", "children"),
        Output("returned-garment-action-status", "children"),
        Output("fabric-inventory-version", "data"),
        Input(
            {"type": "disassemble-returned-garment", "index": ALL},
            "n_clicks",
        ),
        State("fabric-inventory-version", "data"),
        prevent_initial_call=True,
    )
    def disassemble_garment(_clicks, inventory_version):
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            return no_update, no_update, no_update

        garment_id = triggered_id.get("index")
        result = disassemble_returned_garment(garment_id)
        if result.get("error"):
            return (
                no_update,
                f"Unable to disassemble garment #{garment_id}: {result['error']}",
                no_update,
            )

        block_count = result.get("fabric_block_count", 0)
        return (
            render_returned_garments_table(fetch_returned_garments()),
            f"Garment #{garment_id} disassembled. {block_count} fabric block(s) "
            "moved to second-hand inventory.",
            int(inventory_version or 0) + 1,
        )

    @app.callback(
        Output("selected-returned-garment", "data"),
        Output("returned-alternatives-panel", "hidden"),
        Output("returned-alternatives-title", "children"),
        Input({"type": "view-return-alternatives", "index": ALL}, "n_clicks"),
        prevent_initial_call=True,
    )
    def select_returned_garment(_clicks):
        triggered_id = ctx.triggered_id
        if not isinstance(triggered_id, dict):
            return no_update, no_update, no_update

        garment_id = triggered_id.get("index")
        return garment_id, False, f"Return alternatives for garment #{garment_id}"

    @app.callback(
        Output("returned-alternatives-chart", "children"),
        Input("selected-returned-garment", "data"),
        Input("returned-alternatives-distance", "value"),
        Input("returned-alternatives-higher-electricity-factor", "value"),
        Input("fabric-inventory-version", "data"),
    )
    def update_return_alternatives(
        garment_id,
        distance_km,
        electricity_mode,
        _inventory_version,
    ):
        if garment_id is None:
            return html.Div()
        if distance_km is None:
            return html.P("Enter a transport distance to calculate alternatives.")
        try:
            distance = float(distance_km)
        except (TypeError, ValueError):
            return html.P("Transport distance must be a valid number.")
        if distance < 0:
            return html.P("Transport distance must be zero or greater.")

        payload = fetch_returned_garment_alternatives(
            garment_id,
            distance,
            use_higher_electricity_factor=(
                "higher_factor" in (electricity_mode or [])
            ),
        )
        if payload.get("error"):
            return html.P(f"Unable to calculate alternatives: {payload['error']}")
        return render_return_alternative_details(payload)
