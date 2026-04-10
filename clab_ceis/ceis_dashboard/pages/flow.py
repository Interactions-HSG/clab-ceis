from enum import Enum

from dash import dash_table, html
import dash_cytoscape as cyto

from ceis_data import CeisData


def _metric_card(title: str, value: str, subtitle: str, accent: str):
    return html.Div(
        [
            html.Div(title, style={"fontSize": "0.9rem", "fontWeight": "600"}),
            html.Div(
                value,
                style={"fontSize": "2rem", "fontWeight": "700", "marginTop": "8px"},
            ),
            html.Div(
                subtitle,
                style={"fontSize": "0.9rem", "marginTop": "8px", "color": "#334155"},
            ),
        ],
        style={
            "backgroundColor": "#f8fafc",
            "borderLeft": f"6px solid {accent}",
            "borderRadius": "10px",
            "padding": "16px",
            "boxShadow": "0 1px 3px rgba(15, 23, 42, 0.08)",
            "minWidth": "220px",
            "flex": "1 1 220px",
        },
    )


def _build_strategy_progress_section(progress_data: dict):
    aggregates = progress_data.get("aggregates", {})
    sold_garments = progress_data.get("sold_garments", [])
    thresholds = progress_data.get("thresholds", {})

    circularity_pct = float(aggregates.get("circularity_pct", 0))
    threshold_pct = float(thresholds.get("circularity_pct", 30))
    delta_pct = float(aggregates.get("circularity_threshold_delta", 0))
    status_color = "#16a34a" if circularity_pct >= threshold_pct else "#dc2626"
    status_text = (
        f"{delta_pct:.2f} percentage points above threshold"
        if delta_pct >= 0
        else f"{abs(delta_pct):.2f} percentage points below threshold"
    )

    return html.Div(
        [
            html.H1("Strategist Progress"),
            html.P(
                (
                    "Review the current progress towards company goals based on sold "
                    "garments and their linked second-life fabric blocks."
                )
            ),
            html.Div(
                [
                    html.Div(
                        f"Circularity threshold target: {threshold_pct:.0f}%",
                        style={
                            "fontWeight": "600",
                            "color": "#0f172a",
                            "marginBottom": "16px",
                        },
                    )
                ]
            ),
            html.Div(
                [
                    _metric_card(
                        "Circularity Progress",
                        f"{circularity_pct:.2f}%",
                        status_text,
                        status_color,
                    ),
                    _metric_card(
                        "Fabric Saved",
                        f"{float(aggregates.get('fabric_saved_pct', 0)):.2f}%",
                        "Share of recipe fabric area covered by second-life fabric blocks",
                        "#0284c7",
                    ),
                    _metric_card(
                        "Environmental Costs",
                        f"{float(aggregates.get('environmental_cost_co2eq', 0)):.2f} kg CO2eq",
                        "Summed CO2eq across all sold garments",
                        "#7c3aed",
                    ),
                    _metric_card(
                        "Sold Garments",
                        str(int(aggregates.get("sold_garments", 0))),
                        (
                            f"{int(aggregates.get('second_life_fabric_blocks_sold', 0))} "
                            "second-life blocks linked to sold garments"
                        ),
                        "#d97706",
                    ),
                ],
                style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
            ),
            html.H2("Sold Garment Breakdown", style={"marginTop": "24px"}),
            dash_table.DataTable(
                id="strategy-progress-table",
                columns=[
                    {"name": "Garment", "id": "garment_name"},
                    {"name": "Recipe Fabric Blocks", "id": "recipe_fabric_blocks"},
                    {
                        "name": "Second-life Fabric Blocks",
                        "id": "second_life_fabric_blocks",
                    },
                    {"name": "Circularity (%)", "id": "circularity_pct"},
                    {"name": "Fabric Saved (%)", "id": "fabric_saved_pct"},
                    {"name": "CO2eq", "id": "co2eq"},
                ],
                data=sold_garments,
                style_table={"overflowX": "auto"},
                style_cell={"textAlign": "center", "padding": "10px"},
                style_header={"fontWeight": "bold"},
            ),
        ]
    )


def get_dashboard_layout(progress_data: dict | None = None):
    flow_chart_data = get_flow_chart_data()
    progress_data = progress_data or {}
    return html.Div(
        children=[
            html.Header([html.Div("Circular Lab Cockpit", className="logo")]),
            html.Div(
                [
                    html.H1("Product Lifecycle"),
                    cyto.Cytoscape(
                        id="flow-chart",
                        layout={"name": "preset"},
                        style={"height": f"{_chart_height}px"},
                        autolock=True,
                        elements=flow_chart_data["elements"],
                        panningEnabled=False,
                        zoom=1,
                        stylesheet=[
                            {
                                "selector": "node",
                                "style": {
                                    "label": "data(label)",
                                    "shape": "tag",
                                    "text-halign": "left",
                                    "text-valign": "bottom",
                                    "text-margin-x": "-10%",
                                    "line-color": "yellow",
                                    "background-color": "darkblue",
                                    "text-background-color": "grey",
                                    "text-background-opacity": 0.7,
                                },
                            },
                            {
                                "selector": "edge",
                                "style": {
                                    "label": "data(label)",
                                    "target-arrow-shape": "triangle",
                                    "arrow-scale": 1.5,
                                    "line-color": "darkblue",
                                    "text-margin-y": "-15%",
                                },
                            },
                            {
                                "selector": (
                                    f"#{CeLoops.Repair.value}, "
                                    f"#{CeLoops.Recycle.value}, "
                                    f"#{CeLoops.Remanufacture.value}, "
                                    f"#{CeLoops.Composting.value}"
                                ),
                                "style": {
                                    "label": "data(label)",
                                    "curve-style": "unbundled-bezier",
                                    "control-point-distance": "200",
                                    "line-color": "orange",
                                },
                            },
                            {
                                "selector": f"#{CeLoops.Composting.value}",
                                "style": {
                                    "label": "data(label)",
                                    "curve-style": "unbundled-bezier",
                                    "control-point-distance": "-300",
                                    "text-margin-y": "15%",
                                },
                            },
                            {
                                "selector": f"#{CeLoops.Remanufacture.value}",
                                "style": {
                                    "label": "data(label)",
                                    "curve-style": "unbundled-bezier",
                                    "control-point-distance": "-200",
                                    "text-margin-y": "15%",
                                },
                            },
                        ],
                    ),
                    html.P(id="cytoscape-output"),
                    html.H1("Resource Event Dashboard"),
                    html.Button("Update DataTable", id="update-button", n_clicks=0),
                    dash_table.DataTable(
                        id="res-dashboard-table",
                        columns=[
                            {"name": col, "id": col}
                            for col in CeisData().get_data().columns
                        ],
                        data=CeisData().get_data().to_dict("records"),
                        style_table={"maxWidth": f"{_chart_height}px"},
                        style_cell={"textAlign": "center"},
                        style_header={"fontWeight": "bold"},
                    ),
                    _build_strategy_progress_section(progress_data),
                ],
                className="wrapper",
            ),
        ]
    )


def get_flow_chart_data() -> dict:
    return {
        "elements": [
            {
                "data": {
                    "id": f"{CeStages.Extraction.value}",
                    "label": f"{CeStages.Extraction.name}",
                },
                "position": {"x": 100, "y": 0.5 * _chart_height},
            },
            {
                "data": {
                    "id": f"{CeStages.Production.value}",
                    "label": f"{CeStages.Production.name}",
                },
                "position": {"x": 300, "y": 0.5 * _chart_height},
            },
            {
                "data": {
                    "id": f"{CeStages.Use.value}",
                    "label": f"{CeStages.Use.name}",
                },
                "position": {"x": 500, "y": 0.5 * _chart_height},
            },
            {
                "data": {
                    "id": f"{CeStages.Waste.value}",
                    "label": f"{CeStages.Waste.name}",
                },
                "position": {"x": 700, "y": 0.5 * _chart_height},
            },
            {
                "data": {
                    "source": f"{CeStages.Extraction.value}",
                    "target": f"{CeStages.Production.value}",
                    "label": "Supply",
                }
            },
            {
                "data": {
                    "source": f"{CeStages.Production.value}",
                    "target": f"{CeStages.Use.value}",
                    "label": "Deliver",
                }
            },
            {
                "data": {
                    "source": f"{CeStages.Use.value}",
                    "target": f"{CeStages.Waste.value}",
                    "label": "Release",
                }
            },
            {
                "data": {
                    "id": f"{CeLoops.Repair.value}",
                    "label": f"{CeLoops.Repair.name}",
                    "source": f"{CeStages.Use.value}",
                    "target": f"{CeStages.Use.value}",
                }
            },
            {
                "data": {
                    "id": f"{CeLoops.Remanufacture.value}",
                    "label": f"{CeLoops.Remanufacture.name}",
                    "source": f"{CeStages.Use.value}",
                    "target": f"{CeStages.Production.value}",
                }
            },
            {
                "data": {
                    "id": f"{CeLoops.Recycle.value}",
                    "label": f"{CeLoops.Recycle.name}",
                    "source": f"{CeStages.Waste.value}",
                    "target": f"{CeStages.Production.value}",
                }
            },
            {
                "data": {
                    "id": f"{CeLoops.Composting.value}",
                    "label": f"{CeLoops.Composting.name}",
                    "source": f"{CeStages.Waste.value}",
                    "target": f"{CeStages.Extraction.value}",
                }
            },
        ]
    }


class CeStages(Enum):
    Extraction = 1
    Production = 2
    Use = 3
    Waste = 4


class CeLoops(Enum):
    Repair = 11
    Remanufacture = 12
    Recycle = 13
    Composting = 14


_chart_height = 400
