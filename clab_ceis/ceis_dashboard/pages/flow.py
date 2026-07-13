from enum import Enum

from dash import dash_table, html
import dash_cytoscape as cyto

from pages.ui import app_topbar, page_hero


GRAPH_EDGE_COLOR = "#8f978f"
GRAPH_HIGHLIGHT_COLOR = "#d97706"
VALUE_CHAIN_CUSTOMER_ID = "value-chain-customer"
VALUE_CHAIN_STEP_IDS = {
    "material": "value-chain-materials",
    "fabric": "value-chain-fabric",
    "garment": "value-chain-garment",
    "finishing": "value-chain-service",
}


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
                "control-point-distance": "105",
                "line-color": GRAPH_EDGE_COLOR,
                "target-arrow-color": GRAPH_EDGE_COLOR,
            },
        },
        {
            "selector": f"#{CeLoops.Repair.value}",
            "style": {
                "control-point-distance": "-70",
                "text-margin-x": "-12%",
                "text-margin-y": "-5%",
            },
        },
        {
            "selector": f"#{CeLoops.Recycle.value}",
            "style": {
                "control-point-distance": "165",
                "text-margin-x": "12%",
            },
        },
        {
            "selector": f"#{CeLoops.Composting.value}",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distance": "-215",
                "text-margin-x": "-18%",
            },
        },
        {
            "selector": f"#{CeLoops.Remanufacture.value}",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distance": "90",
                "text-margin-x": "12%",
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
                "shape": "ellipse",
                "background-color": "#2f6f5e",
                "border-color": "#dfeee8",
                "border-width": 3,
                "color": "#ffffff",
                "text-wrap": "wrap",
                "text-max-width": 118,
                "text-valign": "center",
                "text-halign": "center",
                "font-weight": 700,
                "font-size": "10px",
                "width": 96,
                "height": 96,
            },
        },
        {
            "selector": ".producer-node",
            "style": {
                "shape": "round-rectangle",
                "background-color": "#f7f4ec",
                "border-color": "#c8c1b3",
                "color": "#1d2420",
                "width": 128,
                "height": 54,
                "text-max-width": 116,
            },
        },
        {
            "selector": ".material-node",
            "style": {
                "background-color": "#6f8c4f",
                "border-color": "#dce8c8",
            },
        },
        {
            "selector": ".customer-node",
            "style": {
                "background-color": "#2f6f5e",
                "border-color": "#99f6e4",
                "font-size": "11px",
                "width": 108,
                "height": 108,
            },
        },
        {
            "selector": ".edge-label-node",
            "style": {
                "label": "data(label)",
                "background-opacity": 0,
                "border-width": 0,
                "color": "#155e75",
                "font-size": "10px",
                "font-weight": 700,
                "height": 1,
                "text-background-color": "#faf8f2",
                "text-background-opacity": 0.95,
                "text-background-padding": 4,
                "width": 1,
            },
        },
        {
            "selector": ".repair-node",
            "style": {
                "background-color": "#2878a8",
                "border-color": "#d8eef8",
            },
        },
        {
            "selector": "edge",
            "style": {
                "label": "data(label)",
                "target-arrow-shape": "triangle",
                "curve-style": "straight",
                "line-color": GRAPH_EDGE_COLOR,
                "target-arrow-color": GRAPH_EDGE_COLOR,
                "font-size": "10px",
                "text-background-color": "#faf8f2",
                "text-background-opacity": 0.95,
                "text-background-padding": 4,
                "width": 2.5,
            },
        },
        {
            "selector": ".biological-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distance": -120,
                "line-color": "#6f8c4f",
                "target-arrow-color": "#6f8c4f",
            },
        },
        {
            "selector": ".feedstock-leg",
            "style": {
                "curve-style": "straight",
                "line-color": "#6f8c4f",
                "target-arrow-color": "#6f8c4f",
                "color": "#4b6b36",
            },
        },
        {
            "selector": ".technical-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distance": 130,
                "line-color": "#2878a8",
                "target-arrow-color": "#2878a8",
                "color": "#155e75",
            },
        },
        {
            "selector": ".customer-leg",
            "style": {
                "curve-style": "bezier",
                "line-color": "#2878a8",
                "target-arrow-color": "#2878a8",
                "z-index": 5,
            },
        },
        {
            "selector": ".deliver-leg",
            "style": {
                "label": "",
                "control-point-distance": -70,
                "control-point-weight": 0.38,
                "text-margin-x": -12,
                "text-margin-y": -42,
            },
        },
        {
            "selector": ".customer-return-service",
            "style": {
                "control-point-distance": 75,
                "control-point-weight": 0.48,
            },
        },
        {
            "selector": ".customer-return-garment",
            "style": {
                "control-point-distance": 125,
                "control-point-weight": 0.52,
                "text-margin-x": 8,
            },
        },
        {
            "selector": ".customer-return-fabric",
            "style": {
                "control-point-distance": 175,
                "control-point-weight": 0.56,
                "text-margin-x": 16,
            },
        },
        {
            "selector": ".customer-return-material",
            "style": {
                "control-point-distance": 225,
                "control-point-weight": 0.6,
                "text-margin-x": 24,
            },
        },
        {
            "selector": ".customer-self-repair",
            "style": {
                "curve-style": "bezier",
                "loop-direction": "180deg",
                "loop-sweep": "125deg",
                "control-point-step-size": 115,
                "line-color": "#0b6ea8",
                "target-arrow-color": "#0b6ea8",
                "arrow-scale": 1.3,
                "color": "#0f4f6f",
                "font-weight": "700",
                "text-background-color": "#eef8fc",
                "text-background-opacity": 1,
                "text-background-padding": 5,
                "text-margin-x": -112,
                "text-margin-y": -36,
                "width": 2.5,
                "z-index": 20,
                "z-index-compare": "manual",
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
    return {
        VALUE_CHAIN_STEP_IDS["material"]: {"x": 190, "y": 70},
        VALUE_CHAIN_STEP_IDS["fabric"]: {"x": 190, "y": 220},
        VALUE_CHAIN_STEP_IDS["garment"]: {"x": 190, "y": 360},
        VALUE_CHAIN_STEP_IDS["finishing"]: {"x": 190, "y": 500},
        VALUE_CHAIN_CUSTOMER_ID: {"x": 370, "y": 620},
    }


def _value_chain_role_nodes(supply_chain: dict, role_group: str) -> list[dict]:
    if role_group == "material":
        return supply_chain.get("material_nodes", [])
    return [
        node
        for node in supply_chain.get("nodes", [])
        if node.get("role_group") == role_group
    ]


def _value_chain_count_label(singular: str, plural: str, count: int) -> str:
    unit = singular if count == 1 else plural
    return f"{count} {unit}" if count else "No linked data"


def _garment_step_detail(garment_count: int, repair_count: int) -> str:
    supplier_text = _value_chain_count_label("supplier", "suppliers", garment_count)
    if not repair_count:
        return supplier_text
    partner = "repair partner" if repair_count == 1 else "repair partners"
    return f"{supplier_text}\n{repair_count} {partner}"


def _value_chain_step_node(
    role_group: str,
    label: str,
    detail: str,
    positions: dict[str, dict[str, int]],
    *,
    classes: str = "producer-node",
    manufacturer_ids: list[int] | None = None,
    material_ids: list[int] | None = None,
) -> dict:
    node_id = VALUE_CHAIN_STEP_IDS[role_group]
    return {
        "data": {
            "id": node_id,
            "label": f"{label}\n{detail}",
            "role": label,
            "role_group": role_group,
            "manufacturer_ids": manufacturer_ids or [],
            "material_ids": material_ids or [],
        },
        "classes": classes,
        "position": positions[node_id],
    }


def get_supply_chain_elements(supply_chain: dict) -> list[dict]:
    positions = _supply_chain_node_positions(supply_chain)
    material_nodes = _value_chain_role_nodes(supply_chain, "material")
    fabric_nodes = _value_chain_role_nodes(supply_chain, "fabric")
    garment_nodes = _value_chain_role_nodes(supply_chain, "garment")
    finishing_nodes = _value_chain_role_nodes(supply_chain, "finishing")
    repair_nodes = _value_chain_role_nodes(supply_chain, "repair")
    manufacturer_role_by_id = {
        node["id"]: node.get("role_group")
        for node in supply_chain.get("nodes", [])
        if node.get("id") is not None
    }
    has_value_chain_data = any(
        [material_nodes, fabric_nodes, garment_nodes, finishing_nodes, repair_nodes]
    )
    if not has_value_chain_data:
        return []

    elements = [
        _value_chain_step_node(
            "material",
            "Raw materials",
            _value_chain_count_label("input", "inputs", len(material_nodes)),
            positions,
            classes="material-node",
            material_ids=[node["id"] for node in material_nodes],
        ),
        _value_chain_step_node(
            "fabric",
            "Fabric manufacturer",
            _value_chain_count_label("supplier", "suppliers", len(fabric_nodes)),
            positions,
            manufacturer_ids=[node["id"] for node in fabric_nodes],
        ),
        _value_chain_step_node(
            "garment",
            "Garment manufacturer",
            _garment_step_detail(len(garment_nodes), len(repair_nodes)),
            positions,
            manufacturer_ids=[
                node["id"] for node in [*garment_nodes, *repair_nodes]
            ],
        ),
        _value_chain_step_node(
            "finishing",
            "Service provider",
            _value_chain_count_label("finisher", "finishers", len(finishing_nodes)),
            positions,
            manufacturer_ids=[node["id"] for node in finishing_nodes],
        ),
    ]
    elements.append(
        {
            "data": {
                "id": VALUE_CHAIN_CUSTOMER_ID,
                "label": "Customer",
                "role": "Customer",
                "role_group": "customer",
            },
            "classes": "customer-node",
            "position": positions[VALUE_CHAIN_CUSTOMER_ID],
        }
    )
    elements.append(
        {
            "data": {
                "id": "deliver-label",
                "label": "deliver",
            },
            "classes": "edge-label-node",
            "position": {"x": 285, "y": 590},
        }
    )
    elements.extend(
        {
            "data": {
                "id": edge_id,
                "source": source,
                "target": target,
                "label": label,
                "manufacturer_distance_ids": manufacturer_distance_ids,
                "material_manufacturer_distance_ids": material_distance_ids,
            },
            "classes": classes,
        }
        for edge_id, source, target, label, classes, manufacturer_distance_ids, material_distance_ids in [
            (
                "value-chain-material-to-fabric",
                VALUE_CHAIN_STEP_IDS["material"],
                VALUE_CHAIN_STEP_IDS["fabric"],
                "feedstock",
                "feedstock-leg",
                [],
                [edge["id"] for edge in supply_chain.get("material_edges", [])],
            ),
            (
                "value-chain-fabric-to-garment",
                VALUE_CHAIN_STEP_IDS["fabric"],
                VALUE_CHAIN_STEP_IDS["garment"],
                "raw fabrics",
                "value-chain-leg",
                [
                    edge["id"]
                    for edge in supply_chain.get("edges", [])
                    if manufacturer_role_by_id.get(edge.get("source_manufacturer_id"))
                    == "fabric"
                    and manufacturer_role_by_id.get(
                        edge.get("destination_manufacturer_id")
                    )
                    == "garment"
                ],
                [],
            ),
            (
                "value-chain-garment-to-service",
                VALUE_CHAIN_STEP_IDS["garment"],
                VALUE_CHAIN_STEP_IDS["finishing"],
                "raw garments",
                "value-chain-leg",
                [
                    edge["id"]
                    for edge in supply_chain.get("edges", [])
                    if manufacturer_role_by_id.get(edge.get("source_manufacturer_id"))
                    == "garment"
                    and manufacturer_role_by_id.get(
                        edge.get("destination_manufacturer_id")
                    )
                    == "finishing"
                ],
                [],
            ),
            (
                "value-chain-service-to-customer",
                VALUE_CHAIN_STEP_IDS["finishing"],
                VALUE_CHAIN_CUSTOMER_ID,
                "deliver",
                "customer-leg deliver-leg",
                [],
                [],
            ),
            (
                "value-chain-customer-to-service",
                VALUE_CHAIN_CUSTOMER_ID,
                VALUE_CHAIN_STEP_IDS["finishing"],
                "repair",
                "technical-loop customer-return-service",
                [],
                [],
            ),
            (
                "value-chain-customer-to-garment",
                VALUE_CHAIN_CUSTOMER_ID,
                VALUE_CHAIN_STEP_IDS["garment"],
                "repair / remanufacture",
                "technical-loop customer-return-garment",
                [],
                [],
            ),
            (
                "value-chain-customer-self-repair",
                VALUE_CHAIN_CUSTOMER_ID,
                VALUE_CHAIN_CUSTOMER_ID,
                "self-repair",
                "customer-self-repair",
                [],
                [],
            ),
            (
                "value-chain-customer-to-fabric",
                VALUE_CHAIN_CUSTOMER_ID,
                VALUE_CHAIN_STEP_IDS["fabric"],
                "reuse",
                "technical-loop customer-return-fabric",
                [],
                [],
            ),
            (
                "value-chain-customer-to-material",
                VALUE_CHAIN_CUSTOMER_ID,
                VALUE_CHAIN_STEP_IDS["material"],
                "recycle",
                "technical-loop customer-return-material",
                [],
                [],
            ),
        ]
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
                                            "height": "760px",
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
                                    html.H2("Value Chain"),
                                    html.P(
                                        "Select a material, producer, customer, transport leg, or circular loop to inspect its events."
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
                                        style={"height": "800px", "width": "100%"},
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
                                "This table updates from either graph. Click any lifecycle or value-chain node/edge above, or reset to see everything."
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
    lifecycle_x = 260
    return {
        "elements": [
            {
                "data": {
                    "id": f"{CeStages.Extraction.value}",
                    "label": f"{CeStages.Extraction.name}",
                },
                "position": {"x": lifecycle_x, "y": 70},
            },
            {
                "data": {
                    "id": f"{CeStages.Production.value}",
                    "label": f"{CeStages.Production.name}",
                },
                "position": {"x": lifecycle_x, "y": 270},
            },
            {
                "data": {
                    "id": f"{CeStages.Use.value}",
                    "label": f"{CeStages.Use.name}",
                },
                "position": {"x": lifecycle_x, "y": 470},
            },
            {
                "data": {
                    "id": f"{CeStages.Waste.value}",
                    "label": f"{CeStages.Waste.name}",
                },
                "position": {"x": lifecycle_x, "y": 670},
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


_chart_height = 760
