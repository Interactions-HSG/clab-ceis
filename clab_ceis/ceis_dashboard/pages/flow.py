from enum import Enum

from dash import dash_table, html
import dash_cytoscape as cyto

from pages.ui import app_topbar, page_hero


GRAPH_EDGE_COLOR = "#8f978f"
GRAPH_HIGHLIGHT_COLOR = "#d97706"
VALUE_CHAIN_CUSTOMER_ID = "value-chain-customer"
VALUE_CHAIN_BRAND_ID = "value-chain-brand"
VALUE_CHAIN_LOCAL_SERVICE_ID = "value-chain-local-service"
VALUE_CHAIN_STEP_IDS = {
    "material": "value-chain-materials",
    "fabric": "value-chain-fabric",
    "garment": "value-chain-garment",
    "service": "value-chain-service",
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
                "font-size": "14px",
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
                "background-color": "#96b34f",
                "border-color": "#dfe9bf",
                "border-width": 2,
                "color": "#ffffff",
                "text-wrap": "wrap",
                "text-max-width": 92,
                "text-valign": "center",
                "text-halign": "center",
                "font-weight": 700,
                "font-size": "10px",
                "width": 92,
                "height": 92,
            },
        },
        {
            "selector": ".major-actor-node",
            "style": {
                "width": 98,
                "height": 98,
                "text-max-width": 94,
            },
        },
        {
            "selector": ".brand-node",
            "style": {
                "width": 102,
                "height": 102,
                "font-size": "15px",
            },
        },
        {
            "selector": ".customer-node",
            "style": {
                "width": 100,
                "height": 100,
                "font-size": "15px",
            },
        },
        {
            "selector": ".local-service-node",
            "style": {
                "width": 112,
                "height": 112,
                "text-max-width": 104,
            },
        },
        {
            "selector": "edge",
            "style": {
                "label": "data(label)",
                "target-arrow-shape": "triangle",
                "curve-style": "straight",
                "line-color": "#e38a2f",
                "target-arrow-color": "#e38a2f",
                "arrow-scale": 0.9,
                "color": "#9a4f17",
                "font-size": "14px",
                "font-weight": 700,
                "text-rotation": "none",
                "text-background-opacity": 0,
                "width": 2,
            },
        },
        {
            "selector": ".garment-brand-flow",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "82 82",
                "control-point-weights": "0.18 0.82",
                "source-endpoint": "225deg",
                "target-endpoint": "315deg",
            },
        },
        {
            "selector": ".repair-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "72 72",
                "control-point-weights": "0.2 0.8",
                "source-endpoint": "35deg",
                "target-endpoint": "145deg",
                "text-margin-x": -14,
                "text-margin-y": -14,
            },
        },
        {
            "selector": ".reuse-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "168 168",
                "control-point-weights": "0.16 0.84",
                "source-endpoint": "75deg",
                "target-endpoint": "105deg",
                "text-margin-x": 18,
                "text-margin-y": 16,
            },
        },
        {
            "selector": ".remanufacture-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "228 228",
                "control-point-weights": "0.12 0.88",
                "source-endpoint": "95deg",
                "target-endpoint": "125deg",
                "text-margin-x": 18,
                "text-margin-y": -12,
            },
        },
        {
            "selector": ".recycle-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "320 320",
                "control-point-weights": "0.08 0.92",
                "source-endpoint": "120deg",
                "target-endpoint": "90deg",
                "text-margin-x": 20,
                "text-margin-y": -12,
            },
        },
        {
            "selector": ".local-service-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "-52 -52",
                "control-point-weights": "0.22 0.78",
                "source-endpoint": "250deg",
                "target-endpoint": "110deg",
                "source-arrow-shape": "triangle",
                "source-arrow-color": "#e38a2f",
                "text-margin-y": 12,
            },
        },
        {
            "selector": ".maintain-loop",
            "style": {
                "curve-style": "unbundled-bezier",
                "control-point-distances": "86 86",
                "control-point-weights": "0.2 0.8",
                "source-endpoint": "45deg",
                "target-endpoint": "135deg",
                "text-margin-x": 20,
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


def _supply_chain_node_positions() -> dict[str, dict[str, int]]:
    return {
        VALUE_CHAIN_STEP_IDS["material"]: {"x": 240, "y": 55},
        VALUE_CHAIN_STEP_IDS["fabric"]: {"x": 240, "y": 175},
        VALUE_CHAIN_STEP_IDS["garment"]: {"x": 240, "y": 295},
        VALUE_CHAIN_STEP_IDS["service"]: {"x": 240, "y": 425},
        VALUE_CHAIN_BRAND_ID: {"x": 240, "y": 555},
        VALUE_CHAIN_LOCAL_SERVICE_ID: {"x": 75, "y": 725},
        VALUE_CHAIN_CUSTOMER_ID: {"x": 240, "y": 725},
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


def _garment_step_detail(garment_count: int) -> str:
    return _value_chain_count_label("supplier", "suppliers", garment_count)


def _value_chain_step_node(
    role_group: str,
    label: str,
    detail: str,
    positions: dict[str, dict[str, int]],
    *,
    classes: str = "major-actor-node",
    manufacturer_ids: list[int] | None = None,
    material_ids: list[int] | None = None,
) -> dict:
    node_id = VALUE_CHAIN_STEP_IDS[role_group]
    return {
        "data": {
            "id": node_id,
            "label": f"{label}\n({detail})" if detail else label,
            "role": label,
            "role_group": role_group,
            "manufacturer_ids": manufacturer_ids or [],
            "material_ids": material_ids or [],
        },
        "classes": classes,
        "position": positions[node_id],
    }


def _value_chain_static_node(
    node_id: str,
    label: str,
    position: dict[str, int],
    classes: str,
    *,
    manufacturer_ids: list[int] | None = None,
) -> dict:
    return {
        "data": {
            "id": node_id,
            "label": label,
            "manufacturer_ids": manufacturer_ids or [],
            "material_ids": [],
        },
        "classes": classes,
        "position": position,
    }


def _value_chain_edge(
    edge_id: str,
    source: str,
    target: str,
    classes: str = "",
    *,
    label: str = "",
    manufacturer_distance_ids: list[int] | None = None,
    material_distance_ids: list[int] | None = None,
) -> dict:
    return {
        "data": {
            "id": edge_id,
            "source": source,
            "target": target,
            "label": label,
            "manufacturer_distance_ids": manufacturer_distance_ids or [],
            "material_manufacturer_distance_ids": material_distance_ids or [],
        },
        "classes": classes,
    }


def get_supply_chain_elements(supply_chain: dict) -> list[dict]:
    positions = _supply_chain_node_positions()
    material_nodes = _value_chain_role_nodes(supply_chain, "material")
    fabric_nodes = _value_chain_role_nodes(supply_chain, "fabric")
    garment_nodes = _value_chain_role_nodes(supply_chain, "garment")
    repair_nodes = _value_chain_role_nodes(supply_chain, "repair")
    manufacturer_role_by_id = {
        node["id"]: node.get("role_group")
        for node in supply_chain.get("nodes", [])
        if node.get("id") is not None
    }
    has_value_chain_data = any(
        [material_nodes, fabric_nodes, garment_nodes, repair_nodes]
    )
    if not has_value_chain_data:
        return []

    elements = [
        _value_chain_step_node(
            "material",
            "Raw materials",
            _value_chain_count_label("input", "inputs", len(material_nodes)),
            positions,
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
            _garment_step_detail(len(garment_nodes)),
            positions,
            manufacturer_ids=[node["id"] for node in garment_nodes],
        ),
        _value_chain_step_node(
            "service",
            "Service provider",
            _value_chain_count_label("partner", "partners", len(repair_nodes)),
            positions,
            manufacturer_ids=[node["id"] for node in repair_nodes],
        ),
        _value_chain_static_node(
            VALUE_CHAIN_BRAND_ID,
            "Brand",
            positions[VALUE_CHAIN_BRAND_ID],
            "brand-node",
        ),
        _value_chain_static_node(
            VALUE_CHAIN_LOCAL_SERVICE_ID,
            "Local service provider\n(repair shop)",
            positions[VALUE_CHAIN_LOCAL_SERVICE_ID],
            "local-service-node",
        ),
        _value_chain_static_node(
            VALUE_CHAIN_CUSTOMER_ID,
            "Customer",
            positions[VALUE_CHAIN_CUSTOMER_ID],
            "customer-node",
        ),
    ]
    fabric_to_garment_distance_ids = [
        edge["id"]
        for edge in supply_chain.get("edges", [])
        if manufacturer_role_by_id.get(edge.get("source_manufacturer_id")) == "fabric"
        and manufacturer_role_by_id.get(edge.get("destination_manufacturer_id"))
        == "garment"
    ]
    elements.extend(
        [
            _value_chain_edge(
                "value-chain-material-to-fabric",
                VALUE_CHAIN_STEP_IDS["material"],
                VALUE_CHAIN_STEP_IDS["fabric"],
                material_distance_ids=[
                    edge["id"] for edge in supply_chain.get("material_edges", [])
                ],
            ),
            _value_chain_edge(
                "value-chain-fabric-to-garment",
                VALUE_CHAIN_STEP_IDS["fabric"],
                VALUE_CHAIN_STEP_IDS["garment"],
                manufacturer_distance_ids=fabric_to_garment_distance_ids,
            ),
            _value_chain_edge(
                "value-chain-garment-to-brand",
                VALUE_CHAIN_STEP_IDS["garment"],
                VALUE_CHAIN_BRAND_ID,
                "garment-brand-flow",
            ),
            _value_chain_edge(
                "value-chain-service-to-brand",
                VALUE_CHAIN_STEP_IDS["service"],
                VALUE_CHAIN_BRAND_ID,
            ),
            _value_chain_edge(
                "value-chain-brand-to-customer",
                VALUE_CHAIN_BRAND_ID,
                VALUE_CHAIN_CUSTOMER_ID,
            ),
            _value_chain_edge(
                "value-chain-brand-to-material",
                VALUE_CHAIN_BRAND_ID,
                VALUE_CHAIN_STEP_IDS["material"],
                "recycle-loop",
                label="Fibre recycle",
            ),
            _value_chain_edge(
                "value-chain-brand-to-garment",
                VALUE_CHAIN_BRAND_ID,
                VALUE_CHAIN_STEP_IDS["garment"],
                "remanufacture-loop",
                label="Remanufacture",
            ),
            _value_chain_edge(
                "value-chain-brand-to-service-repair",
                VALUE_CHAIN_BRAND_ID,
                VALUE_CHAIN_STEP_IDS["service"],
                "repair-loop",
                label="Repair",
            ),
            _value_chain_edge(
                "value-chain-brand-to-service-reuse",
                VALUE_CHAIN_BRAND_ID,
                VALUE_CHAIN_STEP_IDS["service"],
                "reuse-loop",
                label="Reuse / redistribute",
            ),
            _value_chain_edge(
                "value-chain-customer-to-local-service",
                VALUE_CHAIN_CUSTOMER_ID,
                VALUE_CHAIN_LOCAL_SERVICE_ID,
                "local-service-loop",
                label="Repair",
            ),
            _value_chain_edge(
                "value-chain-customer-to-brand",
                VALUE_CHAIN_CUSTOMER_ID,
                VALUE_CHAIN_BRAND_ID,
                "maintain-loop",
                label="Maintain / prolong",
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
                                        "Select an actor, transport leg, or circular process to inspect its events."
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
