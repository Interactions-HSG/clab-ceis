from __future__ import annotations
from dash import Dash, Input, Output, State, ctx

import ceis_data
from ceis_dashboard.callbacks.api import fetch_resource_events
from pages.flow import get_flow_chart_stylesheet, get_supply_chain_stylesheet


def _index_elements(elements: list[dict] | None) -> dict[str, dict]:
    return {
        element.get("data", {}).get("id"): element
        for element in (elements or [])
        if element.get("data", {}).get("id")
    }


def _highlight_edge_with_endpoints(
    edge_id: str | None,
    element_by_id: dict[str, dict],
    highlighted_node_ids: set[str],
    highlighted_edge_ids: set[str],
) -> None:
    if not edge_id:
        return
    highlighted_edge_ids.add(edge_id)
    edge = element_by_id.get(edge_id, {})
    edge_data = edge.get("data", {})
    if edge_data.get("source"):
        highlighted_node_ids.add(edge_data["source"])
    if edge_data.get("target"):
        highlighted_node_ids.add(edge_data["target"])


def _highlight_from_events(
    events: list[dict],
    supply_elements: list[dict] | None,
) -> tuple[set[str], set[str], set[str], set[str]]:
    flow_node_labels = set()
    flow_edge_labels = set()
    supply_node_ids = set()
    supply_edge_ids = set()
    supply_element_by_id = _index_elements(supply_elements)

    for event in events:
        if event.get("lifecycle_node"):
            flow_node_labels.add(event["lifecycle_node"])
        if event.get("lifecycle_edge"):
            flow_edge_labels.add(event["lifecycle_edge"])
        if event.get("manufacturer_id") is not None:
            supply_node_ids.add(f"manufacturer-{event['manufacturer_id']}")
        if event.get("material_id") is not None:
            supply_node_ids.add(f"material-{event['material_id']}")
        if event.get("manufacturer_distance_id") is not None:
            _highlight_edge_with_endpoints(
                f"distance-{event['manufacturer_distance_id']}",
                supply_element_by_id,
                supply_node_ids,
                supply_edge_ids,
            )
        if event.get("material_manufacturer_distance_id") is not None:
            _highlight_edge_with_endpoints(
                f"material-distance-{event['material_manufacturer_distance_id']}",
                supply_element_by_id,
                supply_node_ids,
                supply_edge_ids,
            )

    return flow_node_labels, flow_edge_labels, supply_node_ids, supply_edge_ids


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
        State("supply-chain-chart", "elements"),
        prevent_initial_call=True,
    )
    def filter_resource_events(
        lifecycle_edge_data,
        lifecycle_node_data,
        supply_node_data,
        supply_edge_data,
        _reset_clicks,
        supply_elements,
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
            flow_edge_labels.add(lifecycle_edge_data.get("label"))
        elif ctx.triggered_id == "flow-chart" and lifecycle_node_data:
            events = fetch_resource_events(
                lifecycle_node=lifecycle_node_data.get("label")
            )
            flow_node_labels.add(lifecycle_node_data.get("label"))
        elif ctx.triggered_id == "supply-chain-chart" and ctx.triggered_prop_ids.get(
            "supply-chain-chart.tapNodeData"
        ):
            if supply_node_data.get("material_id") is not None:
                events = fetch_resource_events(
                    material_id=supply_node_data["material_id"]
                )
            else:
                events = fetch_resource_events(
                    manufacturer_id=supply_node_data.get("manufacturer_id")
                )
            if supply_node_data.get("id"):
                supply_node_ids.add(supply_node_data["id"])
        elif ctx.triggered_id == "supply-chain-chart" and supply_edge_data:
            if supply_edge_data.get("material_manufacturer_distance_id") is not None:
                events = fetch_resource_events(
                    material_manufacturer_distance_id=supply_edge_data[
                        "material_manufacturer_distance_id"
                    ]
                )
            else:
                events = fetch_resource_events(
                    manufacturer_distance_id=supply_edge_data.get(
                        "manufacturer_distance_id"
                    )
                )
            _highlight_edge_with_endpoints(
                supply_edge_data.get("id"),
                _index_elements(supply_elements),
                supply_node_ids,
                supply_edge_ids,
            )
        else:
            return (
                events,
                get_flow_chart_stylesheet(),
                get_supply_chain_stylesheet(),
            )

        (
            event_flow_nodes,
            event_flow_edges,
            event_supply_nodes,
            event_supply_edges,
        ) = _highlight_from_events(events, supply_elements)
        flow_node_labels.update(event_flow_nodes)
        flow_edge_labels.update(event_flow_edges)
        supply_node_ids.update(event_supply_nodes)
        supply_edge_ids.update(event_supply_edges)

        return (
            events,
            get_flow_chart_stylesheet(flow_node_labels, flow_edge_labels),
            get_supply_chain_stylesheet(supply_node_ids, supply_edge_ids),
        )
