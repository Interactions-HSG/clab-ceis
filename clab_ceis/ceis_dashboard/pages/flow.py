from enum import Enum

from dash import dash_table, html
import dash_cytoscape as cyto

from pages.ui import app_topbar, page_hero


EVENT_COLUMNS = [
    {"name": "Event ID", "id": "event_id"},
    {"name": "Event Trigger", "id": "event_trigger"},
    {"name": "Timestamp", "id": "timestamp"},
    {"name": "Request Type", "id": "request_type"},
    {"name": "Resource Type", "id": "resource_type"},
    {"name": "CO2eq", "id": "co2eq"},
    {"name": "From", "id": "from"},
    {"name": "To", "id": "to"},
    {"name": "Status", "id": "status"},
    {"name": "Order ID", "id": "order_id"},
    {"name": "Distance (km)", "id": "distance_km"},
]


def _event_table(table_id: str, events: list[dict]):
    return dash_table.DataTable(
        id=table_id,
        columns=EVENT_COLUMNS,
        data=events,
        page_size=12,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "center", "padding": "10px"},
        style_header={"fontWeight": "bold"},
    )


def get_supply_chain_elements(supply_chain: dict) -> list[dict]:
    material_distances = {
        edge["material_id"]: edge["distance_km"]
        for edge in supply_chain.get("material_edges", [])
    }
    elements = [
        {
            "data": {
                "id": f"manufacturer-{node['id']}",
                "manufacturer_id": node["id"],
                "label": node["company"],
                "role": node["role"],
                "role_group": node["role_group"],
                "location": node["location"],
            }
        }
        for node in supply_chain.get("nodes", [])
    ]
    elements.extend(
        {
            "data": {
                "id": f"distance-{edge['id']}",
                "manufacturer_distance_id": edge["id"],
                "source": f"manufacturer-{edge['source_manufacturer_id']}",
                "target": f"manufacturer-{edge['destination_manufacturer_id']}",
                "label": f"{edge['distance_km']:.1f} km",
            }
        }
        for edge in supply_chain.get("edges", [])
    )
    elements.extend(
        {
            "data": {
                "id": f"material-{node['id']}",
                "material_id": node["id"],
                "label": (
                    f"{node['name'].title()}\n"
                    f"{material_distances.get(node['id'], 0):,.0f} km upstream"
                ),
                "role": "Raw material",
                "role_group": "material",
            }
        }
        for node in supply_chain.get("material_nodes", [])
    )
    elements.extend(
        {
            "data": {
                "id": f"material-distance-{edge['id']}",
                "material_manufacturer_distance_id": edge["id"],
                "source": f"material-{edge['material_id']}",
                "target": f"manufacturer-{edge['destination_manufacturer_id']}",
                "label": "",
                "distance_km": edge["distance_km"],
            },
            "classes": "material-leg",
        }
        for edge in supply_chain.get("material_edges", [])
    )
    return elements


def _metric_card(title: str, value: str, subtitle: str, accent: str):
    return html.Div(
        [
            html.Div(title, className="metric-title"),
            html.Div(value, className="metric-value"),
            html.Div(subtitle, className="designer-balance-metric-subtitle"),
        ],
        className="metric-card",
        style={"borderTop": f"5px solid {accent}"},
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
            html.H2("Strategist Progress"),
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
                        className="panel-muted",
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
                className="shop-summary",
            ),
            html.H3("Sold Garment Breakdown"),
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
        ],
        className="panel table-panel",
    )


def get_dashboard_layout(
    progress_data: dict | None = None,
    supply_chain: dict | None = None,
    resource_events: list[dict] | None = None,
    supply_events: list[dict] | None = None,
):
    flow_chart_data = get_flow_chart_data()
    progress_data = progress_data or {}
    supply_chain = supply_chain or {"nodes": [], "edges": []}
    resource_events = resource_events or []
    supply_events = supply_events or []
    return html.Div(
        children=[
            app_topbar(),
            page_hero(
                "Strategy",
                "Lifecycle Strategy Board",
                "Track product lifecycle loops, resource events, and progress against circularity targets.",
                show_home=True,
            ),
            html.Div(
                [
                    html.Section(
                        [
                            html.H2("Product Lifecycle"),
                            cyto.Cytoscape(
                                id="flow-chart",
                                layout={"name": "preset"},
                                style={"height": f"{_chart_height}px", "width": "100%"},
                                autolock=True,
                                elements=flow_chart_data["elements"],
                                panningEnabled=False,
                                zoom=1,
                                stylesheet=[
                                    {
                                        "selector": "node",
                                        "style": {
                                            "label": "data(label)",
                                            "shape": "round-rectangle",
                                            "width": "92px",
                                            "height": "42px",
                                            "background-color": "#2f6f5e",
                                            "color": "#1d2420",
                                            "font-weight": "700",
                                            "text-valign": "bottom",
                                            "text-margin-y": "8px",
                                        },
                                    },
                                    {
                                        "selector": "edge",
                                        "style": {
                                            "label": "data(label)",
                                            "target-arrow-shape": "triangle",
                                            "arrow-scale": 1.3,
                                            "line-color": "#8f978f",
                                            "target-arrow-color": "#8f978f",
                                            "color": "#68716b",
                                            "font-size": "12px",
                                            "text-background-color": "#faf8f2",
                                            "text-background-opacity": 0.92,
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
                                            "curve-style": "unbundled-bezier",
                                            "control-point-distance": "200",
                                            "line-color": "#b56a2b",
                                            "target-arrow-color": "#b56a2b",
                                        },
                                    },
                                    {
                                        "selector": f"#{CeLoops.Composting.value}",
                                        "style": {
                                            "curve-style": "unbundled-bezier",
                                            "control-point-distance": "-300",
                                            "text-margin-y": "15%",
                                        },
                                    },
                                    {
                                        "selector": f"#{CeLoops.Remanufacture.value}",
                                        "style": {
                                            "curve-style": "unbundled-bezier",
                                            "control-point-distance": "-200",
                                            "text-margin-y": "15%",
                                        },
                                    },
                                ],
                            ),
                            html.Div(
                                [
                                    html.Button(
                                        "Show all lifecycle events",
                                        id="lifecycle-events-reset",
                                        n_clicks=0,
                                    ),
                                    _event_table(
                                        "lifecycle-events-table", resource_events
                                    ),
                                ],
                                className="table-panel",
                            ),
                        ],
                        className="panel",
                    ),
                    html.Section(
                        [
                            html.H2("Supply Chain Events"),
                            html.P(
                                "Select a manufacturer or transport leg to inspect its events."
                            ),
                            cyto.Cytoscape(
                                id="supply-chain-chart",
                                layout={
                                    "name": "breadthfirst",
                                    "directed": True,
                                    "padding": 40,
                                    "spacingFactor": 1.2,
                                },
                                elements=get_supply_chain_elements(supply_chain),
                                style={"height": "520px", "width": "100%"},
                                minZoom=0.35,
                                maxZoom=2,
                                stylesheet=[
                                    {
                                        "selector": "node",
                                        "style": {
                                            "label": "data(label)",
                                            "shape": "round-rectangle",
                                            "background-color": "#0b5f56",
                                            "color": "#f0fdfa",
                                            "text-wrap": "wrap",
                                            "text-max-width": 150,
                                            "text-valign": "center",
                                            "font-weight": 700,
                                            "width": 175,
                                            "height": 72,
                                        },
                                    },
                                    {
                                        "selector": "edge",
                                        "style": {
                                            "label": "data(label)",
                                            "target-arrow-shape": "triangle",
                                            "curve-style": "bezier",
                                            "line-color": "#0e7490",
                                            "target-arrow-color": "#0e7490",
                                            "text-background-color": "#cffafe",
                                            "text-background-opacity": 1,
                                        },
                                    },
                                ],
                            ),
                            html.Button(
                                "Show all supply-chain events",
                                id="supply-events-reset",
                                n_clicks=0,
                            ),
                            _event_table("supply-events-table", supply_events),
                        ],
                        className="panel table-panel",
                    ),
                    _build_strategy_progress_section(progress_data),
                ],
                className="dashboard-stack",
            ),
        ],
        className="wrapper",
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
