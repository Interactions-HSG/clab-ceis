from enum import Enum

from dash import dash_table, html
import dash_cytoscape as cyto

from pages.ui import app_topbar, page_hero


GRAPH_EDGE_COLOR = "#8f978f"
GRAPH_HIGHLIGHT_COLOR = "#d97706"


EVENT_COLUMNS = [
    {"name": "Event ID", "id": "event_id"},
    {"name": "Event", "id": "event_trigger"},
    {"name": "Date", "id": "date"},
    {"name": "Time", "id": "time"},
    {"name": "Resource Type", "id": "resource_type"},
    {"name": "CO2eq", "id": "co2eq"},
    {"name": "CO2 Status", "id": "co2eq_calculation_status"},
    {"name": "At", "id": "at"},
    {"name": "From", "id": "from"},
    {"name": "To", "id": "to"},
    {"name": "Status", "id": "status"},
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


LIFECYCLE_EDGE_IDS = {
    "Supply": "lifecycle-edge-supply",
    "Deliver": "lifecycle-edge-deliver",
    "Release": "lifecycle-edge-release",
}


def _id_selector(element_ids: set[str]) -> str:
    return ", ".join(f'[id = "{element_id}"]' for element_id in sorted(element_ids))


def _lifecycle_node_ids(labels: set[str]) -> set[str]:
    return {
        str(CeStages[label].value)
        for label in labels
        if label in CeStages.__members__
    }


def _lifecycle_edge_ids(labels: set[str]) -> set[str]:
    edge_ids = {
        LIFECYCLE_EDGE_IDS[label]
        for label in labels
        if label in LIFECYCLE_EDGE_IDS
    }
    edge_ids.update(
        str(CeLoops[label].value)
        for label in labels
        if label in CeLoops.__members__
    )
    return edge_ids


def get_flow_chart_stylesheet(
    highlighted_node_labels: set[str] | None = None,
    highlighted_edge_labels: set[str] | None = None,
) -> list[dict]:
    highlighted_node_ids = _lifecycle_node_ids(highlighted_node_labels or set())
    highlighted_edge_ids = _lifecycle_edge_ids(highlighted_edge_labels or set())
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "shape": "round-rectangle",
                "width": "78px",
                "height": "42px",
                "background-color": "#2f6f5e",
                "color": "#1d2420",
                "font-weight": "700",
                "font-size": "11px",
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
                "line-color": GRAPH_EDGE_COLOR,
                "target-arrow-color": GRAPH_EDGE_COLOR,
                "color": "#68716b",
                "font-size": "10px",
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
                "control-point-distance": "90",
                "line-color": GRAPH_EDGE_COLOR,
                "target-arrow-color": GRAPH_EDGE_COLOR,
            },
        },
        {
            "selector": f"#{CeLoops.Composting.value}",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distance": "-110",
                "text-margin-y": "15%",
            },
        },
        {
            "selector": f"#{CeLoops.Remanufacture.value}",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distance": "-85",
                "text-margin-y": "15%",
            },
        },
    ]
    if highlighted_node_ids:
        stylesheet.append(
            {
                "selector": _id_selector(highlighted_node_ids),
                "style": {
                    "border-color": GRAPH_HIGHLIGHT_COLOR,
                    "border-width": 3,
                    "z-index": 999,
                },
            }
        )
    if highlighted_edge_ids:
        stylesheet.append(
            {
                "selector": _id_selector(highlighted_edge_ids),
                "style": {
                    "line-color": GRAPH_HIGHLIGHT_COLOR,
                    "target-arrow-color": GRAPH_HIGHLIGHT_COLOR,
                    "width": 3,
                    "z-index": 999,
                },
            }
        )
    return stylesheet


def get_supply_chain_stylesheet(
    highlighted_node_ids: set[str] | None = None,
    highlighted_edge_ids: set[str] | None = None,
) -> list[dict]:
    highlighted_node_ids = highlighted_node_ids or set()
    highlighted_edge_ids = highlighted_edge_ids or set()
    stylesheet = [
        {
            "selector": "node",
            "style": {
                "label": "data(label)",
                "shape": "round-rectangle",
                "background-color": "#0b5f56",
                "color": "#f0fdfa",
                "text-wrap": "wrap",
                "text-max-width": 140,
                "text-valign": "center",
                "font-weight": 700,
                "font-size": "9px",
                "width": 108,
                "height": 48,
            },
        },
        {
            "selector": "edge",
            "style": {
                "label": "data(label)",
                "target-arrow-shape": "triangle",
                "curve-style": "bezier",
                "line-color": GRAPH_EDGE_COLOR,
                "target-arrow-color": GRAPH_EDGE_COLOR,
                "font-size": "10px",
                "text-background-color": "#cffafe",
                "text-background-opacity": 1,
            },
        },
    ]
    if highlighted_node_ids:
        stylesheet.append(
            {
                "selector": _id_selector(highlighted_node_ids),
                "style": {
                    "border-color": GRAPH_HIGHLIGHT_COLOR,
                    "border-width": 3,
                    "z-index": 999,
                },
            }
        )
    if highlighted_edge_ids:
        stylesheet.append(
            {
                "selector": _id_selector(highlighted_edge_ids),
                "style": {
                    "line-color": GRAPH_HIGHLIGHT_COLOR,
                    "target-arrow-color": GRAPH_HIGHLIGHT_COLOR,
                    "width": 3,
                    "z-index": 999,
                },
            }
        )
    return stylesheet


def _supply_chain_node_positions(supply_chain: dict) -> dict[str, dict[str, int]]:
    nodes_by_role: dict[str, list[dict]] = {
        "material": supply_chain.get("material_nodes", []),
        "fabric": [],
        "garment": [],
        "finishing": [],
        "repair": [],
    }
    for node in supply_chain.get("nodes", []):
        nodes_by_role.setdefault(node.get("role_group"), []).append(node)

    role_y = {
        "material": 30,
        "fabric": 135,
        "garment": 285,
        "finishing": 395,
        "repair": 495,
    }

    def horizontal_positions(
        nodes: list[dict],
        *,
        start_x: int,
        max_x: int,
    ) -> list[int]:
        if not nodes:
            return []
        if len(nodes) == 1:
            return [round((start_x + max_x) / 2)]
        step = (max_x - start_x) / (len(nodes) - 1)
        return [round(start_x + index * step) for index in range(len(nodes))]

    positions: dict[str, dict[str, int]] = {}
    for role_group, bounds in (
        ("material", (45, 475)),
        ("fabric", (20, 500)),
        ("garment", (260, 260)),
        ("finishing", (35, 485)),
        ("repair", (155, 365)),
    ):
        role_nodes = nodes_by_role.get(role_group, [])
        x_positions = horizontal_positions(
            role_nodes,
            start_x=bounds[0],
            max_x=bounds[1],
        )
        for node, x_position in zip(role_nodes, x_positions):
            node_id = (
                f"material-{node['id']}"
                if role_group == "material"
                else f"manufacturer-{node['id']}"
            )
            positions[node_id] = {"x": x_position, "y": role_y[role_group]}

    return positions


def get_supply_chain_elements(supply_chain: dict) -> list[dict]:
    material_distances = {
        edge["material_id"]: edge["distance_km"]
        for edge in supply_chain.get("material_edges", [])
    }
    positions = _supply_chain_node_positions(supply_chain)
    elements = [
        {
            "data": {
                "id": f"manufacturer-{node['id']}",
                "manufacturer_id": node["id"],
                "label": node["company"],
                "role": node["role"],
                "role_group": node["role_group"],
                "location": node["location"],
            },
            "position": positions.get(f"manufacturer-{node['id']}"),
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
            },
            "position": positions.get(f"material-{node['id']}"),
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
                        GRAPH_HIGHLIGHT_COLOR,
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
        className="panel",
    )


def get_dashboard_layout(
    progress_data: dict | None = None,
    supply_chain: dict | None = None,
    resource_events: list[dict] | None = None,
):
    flow_chart_data = get_flow_chart_data()
    progress_data = progress_data or {}
    supply_chain = supply_chain or {"nodes": [], "edges": []}
    resource_events = resource_events or []
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
                    _build_strategy_progress_section(progress_data),
                    html.Div(
                        [
                            html.Section(
                                [
                                    html.H2("Product Lifecycle"),
                                    html.P(
                                        "Select a lifecycle stage or loop to inspect its events."
                                    ),
                                    cyto.Cytoscape(
                                        id="flow-chart",
                                        layout={
                                            "name": "preset",
                                            "fit": True,
                                            "padding": 20,
                                        },
                                        style={
                                            "height": "520px",
                                            "width": "100%",
                                        },
                                        autolock=True,
                                        elements=flow_chart_data["elements"],
                                        panningEnabled=False,
                                        minZoom=0.25,
                                        maxZoom=2,
                                        stylesheet=get_flow_chart_stylesheet(),
                                    ),
                                ],
                                className="panel",
                                style={"minWidth": 0},
                            ),
                            html.Section(
                                [
                                    html.H2("Supply Chain"),
                                    html.P(
                                        "Select a manufacturer, material, or transport leg to inspect its events."
                                    ),
                                    cyto.Cytoscape(
                                        id="supply-chain-chart",
                                        layout={
                                            "name": "preset",
                                            "fit": True,
                                            "padding": 25,
                                        },
                                        elements=get_supply_chain_elements(
                                            supply_chain
                                        ),
                                        style={"height": "520px", "width": "100%"},
                                        minZoom=0.35,
                                        maxZoom=2,
                                        stylesheet=get_supply_chain_stylesheet(),
                                    ),
                                ],
                                className="panel",
                                style={"minWidth": 0},
                            ),
                        ],
                        className="dashboard-graph-grid",
                    ),
                    html.Section(
                        [
                            html.H2("Resource Events"),
                            html.P(
                                "This table updates from either graph. Click any lifecycle or supply-chain node/edge above, or reset to see everything."
                            ),
                            html.Button(
                                "Show all events",
                                id="resource-events-reset",
                                n_clicks=0,
                            ),
                            _event_table("resource-events-table", resource_events),
                        ],
                        className="panel table-panel",
                    ),
                ],
                className="dashboard-stack",
            ),
        ],
        className="wrapper",
    )


def get_flow_chart_data() -> dict:
    lifecycle_y = 0.5 * _chart_height
    return {
        "elements": [
            {
                "data": {
                    "id": f"{CeStages.Extraction.value}",
                    "label": f"{CeStages.Extraction.name}",
                },
                "position": {"x": 45, "y": lifecycle_y},
            },
            {
                "data": {
                    "id": f"{CeStages.Production.value}",
                    "label": f"{CeStages.Production.name}",
                },
                "position": {"x": 190, "y": lifecycle_y},
            },
            {
                "data": {
                    "id": f"{CeStages.Use.value}",
                    "label": f"{CeStages.Use.name}",
                },
                "position": {"x": 335, "y": lifecycle_y},
            },
            {
                "data": {
                    "id": f"{CeStages.Waste.value}",
                    "label": f"{CeStages.Waste.name}",
                },
                "position": {"x": 480, "y": lifecycle_y},
            },
            {
                "data": {
                    "id": LIFECYCLE_EDGE_IDS["Supply"],
                    "source": f"{CeStages.Extraction.value}",
                    "target": f"{CeStages.Production.value}",
                    "label": "Supply",
                }
            },
            {
                "data": {
                    "id": LIFECYCLE_EDGE_IDS["Deliver"],
                    "source": f"{CeStages.Production.value}",
                    "target": f"{CeStages.Use.value}",
                    "label": "Deliver",
                }
            },
            {
                "data": {
                    "id": LIFECYCLE_EDGE_IDS["Release"],
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


_chart_height = 520
