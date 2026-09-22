import pytest

from ceis_backend.process_quantities import resolve_process_amount


@pytest.mark.parametrize(
    ("basis", "rate", "expected"),
    [
        ("fixed", 2.5, 2.5),
        ("fabric_weight_kg", 1.0, 0.10752),
        ("fabric_area_sqm", 0.75, 0.384),
    ],
)
def test_resolve_process_amount_uses_declared_quantity_basis(basis, rate, expected):
    assert resolve_process_amount(
        rate,
        basis,
        fabric_weight_kg=0.10752,
        fabric_area_sqm=0.512,
    ) == pytest.approx(expected)


def test_resolve_process_amount_rejects_unknown_quantity_basis():
    with pytest.raises(ValueError):
        resolve_process_amount(
            1.0,
            "process-name-specific-magic",
            fabric_weight_kg=0.10752,
            fabric_area_sqm=0.512,
        )
