from __future__ import annotations

from dash import html


def render_orders_table(orders: list[dict]):
    if not orders:
        return html.Div("No orders yet.", className="panel-muted")

    header = html.Thead(
        html.Tr(
            [
                html.Th("Order"),
                html.Th("Garment"),
                html.Th("Material"),
                html.Th("Fulfillment"),
                html.Th("Status"),
                html.Th("Created"),
                html.Th("Action"),
            ]
        )
    )
    rows = []
    for order in orders:
        completed = order.get("status") == "Completed"
        rows.append(
            html.Tr(
                [
                    html.Td(f"#{order['id']}"),
                    html.Td(order.get("garment") or "—"),
                    html.Td(order.get("material") or "—"),
                    html.Td(str(order.get("fulfillment_type") or "—").title()),
                    html.Td(order.get("status") or "—"),
                    html.Td(order.get("created_at") or "—"),
                    html.Td(
                        html.Button(
                            "Shipped" if completed else "Ship",
                            id={"type": "ship-order", "index": order["id"]},
                            n_clicks=0,
                            disabled=completed,
                            className="order-ship-button",
                        )
                    ),
                ]
            )
        )
    return html.Div(
        html.Table([header, html.Tbody(rows)], className="orders-table"),
        className="orders-table-scroll",
    )
