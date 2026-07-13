from callbacks.dashboard_table import (
    _filter_events_for_value_chain_element,
    _highlight_for_lifecycle_edge,
    _highlight_for_lifecycle_node,
    _highlight_for_value_chain_edge,
    _highlight_for_value_chain_node,
)


def test_lifecycle_use_highlights_customer_only_in_value_chain():
    flow_nodes, flow_edges, supply_nodes, supply_edges = _highlight_for_lifecycle_node(
        "Use"
    )

    assert flow_nodes == {"Use"}
    assert flow_edges == set()
    assert supply_nodes == {"value-chain-customer"}
    assert supply_edges == set()


def test_lifecycle_deliver_highlights_deliver_edge_without_adjacent_nodes():
    flow_nodes, flow_edges, supply_nodes, supply_edges = _highlight_for_lifecycle_edge(
        "Deliver"
    )

    assert flow_nodes == set()
    assert flow_edges == {"Deliver"}
    assert supply_nodes == set()
    assert supply_edges == {"value-chain-service-to-customer"}


def test_value_chain_edge_highlights_matching_lifecycle_edge_only():
    flow_nodes, flow_edges, supply_nodes, supply_edges = _highlight_for_value_chain_edge(
        "value-chain-service-to-customer"
    )

    assert flow_nodes == set()
    assert flow_edges == {"Deliver"}
    assert supply_nodes == set()
    assert supply_edges == {"value-chain-service-to-customer"}


def test_value_chain_customer_highlights_lifecycle_use():
    flow_nodes, flow_edges, supply_nodes, supply_edges = _highlight_for_value_chain_node(
        "value-chain-customer"
    )

    assert flow_nodes == {"Use"}
    assert flow_edges == set()
    assert supply_nodes == {"value-chain-customer"}
    assert supply_edges == set()


def test_filter_events_for_value_chain_node_does_not_match_everything():
    events = [
        {"event_id": 1, "manufacturer_id": 7},
        {"event_id": 2, "manufacturer_id": 2},
        {"event_id": 3, "material_id": 5},
        {"event_id": 4, "lifecycle_node": "Use"},
    ]

    filtered = _filter_events_for_value_chain_element(
        events,
        {
            "id": "value-chain-garment",
            "manufacturer_ids": [7],
            "material_ids": [],
        },
    )

    assert [event["event_id"] for event in filtered] == [1]


def test_filter_events_for_customer_uses_lifecycle_use_events():
    events = [
        {"event_id": 1, "manufacturer_id": 7},
        {"event_id": 2, "lifecycle_node": "Use"},
        {"event_id": 3, "lifecycle_node": "Production"},
    ]

    filtered = _filter_events_for_value_chain_element(
        events,
        {
            "id": "value-chain-customer",
            "manufacturer_ids": [],
            "material_ids": [],
        },
    )

    assert [event["event_id"] for event in filtered] == [2]


def test_filter_events_for_value_chain_edge_uses_aggregate_distance_ids():
    events = [
        {"event_id": 1, "manufacturer_distance_id": 11},
        {"event_id": 2, "manufacturer_distance_id": 12},
        {"event_id": 3, "material_manufacturer_distance_id": 4},
    ]

    filtered = _filter_events_for_value_chain_element(
        events,
        {
            "id": "value-chain-fabric-to-garment",
            "source": "value-chain-fabric",
            "target": "value-chain-garment",
            "manufacturer_distance_ids": [11],
            "material_manufacturer_distance_ids": [],
        },
    )

    assert [event["event_id"] for event in filtered] == [1]


def test_filter_events_for_deliver_edge_uses_lifecycle_deliver_events():
    events = [
        {"event_id": 1, "lifecycle_edge": "Deliver"},
        {"event_id": 2, "lifecycle_edge": "Supply"},
        {"event_id": 3, "manufacturer_distance_id": 11},
    ]

    filtered = _filter_events_for_value_chain_element(
        events,
        {
            "id": "value-chain-service-to-customer",
            "source": "value-chain-service",
            "target": "value-chain-customer",
            "manufacturer_distance_ids": [],
            "material_manufacturer_distance_ids": [],
        },
    )

    assert [event["event_id"] for event in filtered] == [1]
