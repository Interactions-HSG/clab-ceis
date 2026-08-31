from __future__ import annotations
from dash import Dash, Input, Output, ctx

import ceis_data
from ceis_dashboard.callbacks.api import fetch_resource_events
from pages.flow import (
    VALUE_CHAIN_BRAND_ID,
    VALUE_CHAIN_CUSTOMER_ID,
    VALUE_CHAIN_LOCAL_SERVICE_ID,
    VALUE_CHAIN_STEP_IDS,
    get_flow_chart_stylesheet,
    get_supply_chain_stylesheet,
)


VALUE_CHAIN_EDGE_IDS = {
    "feedstock": "value-chain-material-to-fabric",
    "raw_fabrics": "value-chain-fabric-to-garment",
    "raw_garments": "value-chain-garment-to-brand",
    "service_supply": "value-chain-service-to-brand",
    "deliver": "value-chain-brand-to-customer",
    "recycle": "value-chain-brand-to-material",
    "remanufacture": "value-chain-brand-to-garment",
    "repair": "value-chain-brand-to-service-repair",
    "reuse": "value-chain-brand-to-service-reuse",
    "local_repair": "value-chain-customer-to-local-service",
    "maintain": "value-chain-customer-to-brand",
}

LIFECYCLE_NODE_TO_VALUE_CHAIN_NODES = {
    "Extraction": {VALUE_CHAIN_STEP_IDS["material"]},
    "Production": {
        VALUE_CHAIN_STEP_IDS["fabric"],
        VALUE_CHAIN_STEP_IDS["garment"],
        VALUE_CHAIN_STEP_IDS["service"],
        VALUE_CHAIN_BRAND_ID,
        VALUE_CHAIN_LOCAL_SERVICE_ID,
    },
    "Use": {VALUE_CHAIN_CUSTOMER_ID},
    "Waste": set(),
}

LIFECYCLE_EDGE_TO_VALUE_CHAIN_EDGES = {
    "Supply": {
        VALUE_CHAIN_EDGE_IDS["feedstock"],
        VALUE_CHAIN_EDGE_IDS["raw_fabrics"],
        VALUE_CHAIN_EDGE_IDS["raw_garments"],
        VALUE_CHAIN_EDGE_IDS["service_supply"],
    },
    "Deliver": {VALUE_CHAIN_EDGE_IDS["deliver"]},
    "Release": set(),
    "Repair": {
        VALUE_CHAIN_EDGE_IDS["repair"],
        VALUE_CHAIN_EDGE_IDS["local_repair"],
        VALUE_CHAIN_EDGE_IDS["maintain"],
    },
    "Remanufacture": {
        VALUE_CHAIN_EDGE_IDS["remanufacture"],
        VALUE_CHAIN_EDGE_IDS["reuse"],
    },
    "Recycle": {VALUE_CHAIN_EDGE_IDS["recycle"]},
    "Composting": set(),
}

VALUE_CHAIN_NODE_TO_LIFECYCLE_NODE = {
    value_chain_node: lifecycle_node
    for lifecycle_node, value_chain_nodes in LIFECYCLE_NODE_TO_VALUE_CHAIN_NODES.items()
    for value_chain_node in value_chain_nodes
}

VALUE_CHAIN_EDGE_TO_LIFECYCLE_EDGE = {
    value_chain_edge: lifecycle_edge
    for lifecycle_edge, value_chain_edges in LIFECYCLE_EDGE_TO_VALUE_CHAIN_EDGES.items()
    for value_chain_edge in value_chain_edges
}


def _ids(data: dict, key: str) -> set[int]:
    return {int(value) for value in data.get(key, []) if value is not None}


def _event_matches_value_chain_node(event: dict, node_data: dict) -> bool:
    manufacturer_id = event.get("manufacturer_id")
    material_id = event.get("material_id")
    return (
        manufacturer_id is not None
        and int(manufacturer_id) in _ids(node_data, "manufacturer_ids")
    ) or (
        material_id is not None and int(material_id) in _ids(node_data, "material_ids")
    )


def _event_matches_value_chain_edge(event: dict, edge_data: dict) -> bool:
    manufacturer_distance_id = event.get("manufacturer_distance_id")
    material_distance_id = event.get("material_manufacturer_distance_id")
    return (
        manufacturer_distance_id is not None
        and int(manufacturer_distance_id)
        in _ids(edge_data, "manufacturer_distance_ids")
    ) or (
        material_distance_id is not None
        and int(material_distance_id)
        in _ids(edge_data, "material_manufacturer_distance_ids")
    )


def _filter_events_for_value_chain_element(
    events: list[dict],
    element_data: dict | None,
) -> list[dict]:
    if not element_data:
        return []

    if "source" in element_data and "target" in element_data:
        raw_matches = [
            event
            for event in events
            if _event_matches_value_chain_edge(event, element_data)
        ]
        if _ids(element_data, "manufacturer_distance_ids") or _ids(
            element_data,
            "material_manufacturer_distance_ids",
        ):
            return raw_matches
        lifecycle_edge = VALUE_CHAIN_EDGE_TO_LIFECYCLE_EDGE.get(element_data.get("id"))
        return [
            event
            for event in events
            if event.get("lifecycle_edge") == lifecycle_edge
        ]

    raw_matches = [
        event
        for event in events
        if _event_matches_value_chain_node(event, element_data)
    ]
    if _ids(element_data, "manufacturer_ids") or _ids(element_data, "material_ids"):
        return raw_matches
    lifecycle_node = VALUE_CHAIN_NODE_TO_LIFECYCLE_NODE.get(element_data.get("id"))
    return [
        event
        for event in events
        if event.get("lifecycle_node") == lifecycle_node
    ]


def _highlight_for_lifecycle_node(
    lifecycle_node: str | None,
) -> tuple[set[str], set[str], set[str], set[str]]:
    if not lifecycle_node:
        return set(), set(), set(), set()
    return (
        {lifecycle_node},
        set(),
        set(LIFECYCLE_NODE_TO_VALUE_CHAIN_NODES.get(lifecycle_node, set())),
        set(),
    )


def _highlight_for_lifecycle_edge(
    lifecycle_edge: str | None,
) -> tuple[set[str], set[str], set[str], set[str]]:
    if not lifecycle_edge:
        return set(), set(), set(), set()
    return (
        set(),
        {lifecycle_edge},
        set(),
        set(LIFECYCLE_EDGE_TO_VALUE_CHAIN_EDGES.get(lifecycle_edge, set())),
    )


def _highlight_for_value_chain_node(
    node_id: str | None,
) -> tuple[set[str], set[str], set[str], set[str]]:
    if not node_id:
        return set(), set(), set(), set()
    lifecycle_node = VALUE_CHAIN_NODE_TO_LIFECYCLE_NODE.get(node_id)
    flow_node_labels = {lifecycle_node} if lifecycle_node else set()
    return flow_node_labels, set(), {node_id}, set()


def _highlight_for_value_chain_edge(
    edge_id: str | None,
) -> tuple[set[str], set[str], set[str], set[str]]:
    if not edge_id:
        return set(), set(), set(), set()
    lifecycle_edge = VALUE_CHAIN_EDGE_TO_LIFECYCLE_EDGE.get(edge_id)
    flow_edge_labels = {lifecycle_edge} if lifecycle_edge else set()
    return set(), flow_edge_labels, set(), {edge_id}


def register_dashboard_table_callbacks(app: Dash, data: ceis_data.CeisData) -> None:
    @app.callback(
        Output("resource-events-table", "data"),
        Output("flow-chart", "stylesheet"),
        Output("supply-chain-chart", "stylesheet"),
        Input("flow-chart", "tapEdgeData"),
        Input("flow-chart", "tapNodeData"),
        Input("supply-chain-chart", "tapNodeData"),
        Input("supply-chain-chart", "tapEdgeData"),
        Input("resource-events-reset", "n_clicks"),
        prevent_initial_call=True,
    )
    def filter_resource_events(
        lifecycle_edge_data,
        lifecycle_node_data,
        supply_node_data,
        supply_edge_data,
        _reset_clicks,
    ):
        events = fetch_resource_events()
        flow_node_labels = set()
        flow_edge_labels = set()
        supply_node_ids = set()
        supply_edge_ids = set()

        if ctx.triggered_id == "flow-chart" and ctx.triggered_prop_ids.get(
            "flow-chart.tapEdgeData"
        ):
            events = fetch_resource_events(
                lifecycle_edge=lifecycle_edge_data.get("label")
            )
            (
                flow_node_labels,
                flow_edge_labels,
                supply_node_ids,
                supply_edge_ids,
            ) = _highlight_for_lifecycle_edge(lifecycle_edge_data.get("label"))
        elif ctx.triggered_id == "flow-chart" and lifecycle_node_data:
            events = fetch_resource_events(
                lifecycle_node=lifecycle_node_data.get("label")
            )
            (
                flow_node_labels,
                flow_edge_labels,
                supply_node_ids,
                supply_edge_ids,
            ) = _highlight_for_lifecycle_node(lifecycle_node_data.get("label"))
        elif ctx.triggered_id == "supply-chain-chart" and ctx.triggered_prop_ids.get(
            "supply-chain-chart.tapNodeData"
        ):
            events = _filter_events_for_value_chain_element(
                events,
                supply_node_data,
            )
            (
                flow_node_labels,
                flow_edge_labels,
                supply_node_ids,
                supply_edge_ids,
            ) = _highlight_for_value_chain_node(supply_node_data.get("id"))
        elif ctx.triggered_id == "supply-chain-chart" and supply_edge_data:
            events = _filter_events_for_value_chain_element(
                events,
                supply_edge_data,
            )
            (
                flow_node_labels,
                flow_edge_labels,
                supply_node_ids,
                supply_edge_ids,
            ) = _highlight_for_value_chain_edge(supply_edge_data.get("id"))
        else:
            return (
                events,
                get_flow_chart_stylesheet(),
                get_supply_chain_stylesheet(),
            )

        return (
            events,
            get_flow_chart_stylesheet(flow_node_labels, flow_edge_labels),
            get_supply_chain_stylesheet(supply_node_ids, supply_edge_ids),
        )
