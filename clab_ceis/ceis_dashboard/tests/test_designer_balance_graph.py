from callbacks.designer_balance import _build_supply_chain_graph


def test_scenario_planner_uses_horizontal_supplier_flow_graph():
    graph = _build_supply_chain_graph(
        {
            "actors": [
                {
                    "role_group": "fabric",
                    "company": "Fabric A",
                    "location": "St. Gallen",
                    "delay_days": 1.5,
                },
                {
                    "role_group": "garment",
                    "company": "Garment A",
                    "location": "Burladingen",
                    "delay_days": 3.0,
                },
            ],
            "legs": [
                {
                    "source_role_group": "fabric",
                    "destination_role_group": "garment",
                    "distance_km": 120.0,
                    "delay_days": 0.92,
                }
            ],
        }
    )

    nodes = {
        element["data"]["id"]: element
        for element in graph.elements
        if "position" in element
    }
    edges = {
        element["data"]["id"]: element
        for element in graph.elements
        if "source" in element.get("data", {})
    }

    assert set(nodes) == {"fabric", "garment"}
    assert set(edges) == {"leg-0"}
    assert nodes["fabric"]["position"]["y"] == nodes["garment"]["position"]["y"]
    assert nodes["fabric"]["position"]["x"] < nodes["garment"]["position"]["x"]
    assert edges["leg-0"]["data"]["source"] == "fabric"
    assert edges["leg-0"]["data"]["target"] == "garment"
    assert all(
        not element["data"]["id"].startswith("customer")
        for element in graph.elements
    )
