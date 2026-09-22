"""Resolve declarative fabric-block recipe process quantities."""

from enum import Enum


class ProcessQuantityBasis(str, Enum):
    FIXED = "fixed"
    FABRIC_WEIGHT_KG = "fabric_weight_kg"
    FABRIC_AREA_SQM = "fabric_area_sqm"


def resolve_process_amount(
    rate: float,
    quantity_basis: ProcessQuantityBasis | str,
    *,
    fabric_weight_kg: float,
    fabric_area_sqm: float,
) -> float:
    """Convert a recipe rate into the activity amount used for emissions."""
    basis = ProcessQuantityBasis(quantity_basis)
    basis_quantity = {
        ProcessQuantityBasis.FIXED: 1.0,
        ProcessQuantityBasis.FABRIC_WEIGHT_KG: float(fabric_weight_kg),
        ProcessQuantityBasis.FABRIC_AREA_SQM: float(fabric_area_sqm),
    }[basis]
    return float(rate) * basis_quantity
