from __future__ import annotations

def calculate_material_cost_chf(
    area_sqm: float, cost_per_sqm_chf: float
) -> float:
    """Calculate fabric cost from the block area and normalized area price."""
    return float(area_sqm) * float(cost_per_sqm_chf)
