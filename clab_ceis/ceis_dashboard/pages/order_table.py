from __future__ import annotations

import plotly.graph_objects as go
from dash import dcc, html

from pages.chart_theme import apply_bar_chart_theme, component_marker


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


def render_returned_garments_table(garments: list[dict]):
    if not garments:
        return html.Div(
            "No pre-loved garments awaiting action.", className="panel-muted"
        )

    header = html.Thead(
        html.Tr(
            [
                html.Th("Garment ID"),
                html.Th("Garment"),
                html.Th("Original garment ID"),
                html.Th("Fabric blocks"),
                html.Th("Damage"),
                html.Th("Status"),
                html.Th("Action"),
            ]
        )
    )
    rows = [
        html.Tr(
            [
                html.Td(f"#{garment['id']}"),
                html.Td(garment.get("garment") or "—"),
                html.Td(f"#{garment['returned_from_garment_id']}"),
                html.Td(garment.get("fabric_block_count", 0)),
                html.Td(
                    str(garment.get("damage_code") or "no_damage")
                    .replace("_", " ")
                    .title()
                ),
                html.Td(
                    "Pre-loved"
                    if garment.get("status") in (None, "", "Returned")
                    else garment["status"]
                ),
                html.Td(
                    html.Div(
                        [
                            html.Button(
                                "View alternatives",
                                id={
                                    "type": "view-return-alternatives",
                                    "index": garment["id"],
                                },
                                n_clicks=0,
                                className="garment-alternatives-button",
                            ),
                            html.Button(
                                "Disassemble",
                                id={
                                    "type": "disassemble-returned-garment",
                                    "index": garment["id"],
                                },
                                n_clicks=0,
                                className="garment-disassemble-button",
                            ),
                        ],
                        className="returned-garment-actions",
                    )
                ),
            ]
        )
        for garment in garments
    ]
    return html.Div(
        html.Table([header, html.Tbody(rows)], className="orders-table"),
        className="orders-table-scroll",
    )


def _saved_components(components: list[dict]) -> list[dict]:
    return [
        {
            "name": f"Saved: {component['name']}",
            "co2eq": -float(component.get("co2eq", 0)),
        }
        for component in components
    ]


def _return_alternatives_chart(payload: dict) -> go.Figure:
    scenarios = payload.get("return", {})
    whole_garment = scenarios.get("whole_garment", {})
    fabric_blocks = scenarios.get("fabric_blocks", {})
    bars = [
        (
            "Reuse whole garment",
            [
                *whole_garment.get("components", []),
                *_saved_components(whole_garment.get("reference_components", [])),
            ],
        ),
        (
            "Recover fabric blocks",
            [
                *fabric_blocks.get("components", []),
                *_saved_components(fabric_blocks.get("reference_components", [])),
            ],
        ),
    ]

    component_names: list[str] = []
    values_by_bar: list[dict[str, float]] = []
    for _, components in bars:
        values = {
            str(component["name"]): float(component.get("co2eq", 0))
            for component in components
        }
        values_by_bar.append(values)
        for name in values:
            if name not in component_names:
                component_names.append(name)

    figure = go.Figure()
    labels = [label for label, _ in bars]
    for index, component_name in enumerate(component_names):
        values = [values.get(component_name, 0) for values in values_by_bar]
        figure.add_bar(
            name=component_name,
            x=labels,
            y=values,
            text=[f"{value:.3f}" if value else "" for value in values],
            textposition="inside",
            marker=component_marker(component_name, index),
            hovertemplate=component_name + ": %{y:.3f} kg CO2eq<extra></extra>",
        )

    figure.update_layout(
        barmode="relative",
        title={
            "text": "Return alternatives: impact (+) and CO2 saved (-)",
            "x": 0.02,
            "xanchor": "left",
        },
        xaxis_title=None,
        yaxis_title="kg CO2eq",
        legend_title_text="Calculation components",
        margin={"l": 55, "r": 20, "t": 60, "b": 55},
    )
    return apply_bar_chart_theme(figure)


def render_return_alternative_details(payload: dict) -> html.Div:
    garment = payload.get("garment", {})
    damage = payload.get("damage", {})
    calculation = payload.get("calculation", {})
    factor_label = (
        "Higher electricity factor"
        if calculation.get("electricity_mode") == "higher_factor"
        else "Current electricity factor"
    )
    return html.Div(
        [
            html.Div(
                [
                    html.Strong(
                        f"{garment.get('name', 'Garment')} #{garment.get('id', '')}"
                    ),
                    html.Span(f"Damage: {damage.get('label', '—')}"),
                    html.Span(
                        f"{garment.get('fabric_block_count', 0)} fabric blocks"
                    ),
                    html.Span(factor_label),
                ],
                className="scenario-summary panel-muted",
            ),
            html.Div(
                [
                    html.P(
                        "Positive sections are return emissions; negative sections "
                        "are the new-garment production CO2 saved. Transport is "
                        "shown only as a return emission."
                    ),
                    dcc.Graph(
                        id="dashboard-return-component-chart",
                        figure=_return_alternatives_chart(payload),
                        config={"displayModeBar": False},
                    ),
                ],
                className="co2-detail-panel",
            ),
        ],
        className="scenario-results",
    )
