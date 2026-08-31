from ceis_backend.costing import calculate_material_cost_chf


def test_direct_area_price_calculates_material_cost():
    assert calculate_material_cost_chf(0.5, 20.0) == 10.0
