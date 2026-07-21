import numpy as np
import pytest

from shiftmem.envs.supply_models import SingleSupplier, SupplyParameters


def test_supply_parameters_validate_ranges() -> None:
    with pytest.raises(ValueError):
        SupplyParameters(lead_time=0)
    with pytest.raises(ValueError):
        SupplyParameters(lead_time=1, fill_rate=1.1)


def test_full_fill_arrives_in_full() -> None:
    supplier = SingleSupplier()
    result = supplier.arrival_quantity(
        12, np.random.default_rng(1), SupplyParameters(lead_time=2, fill_rate=1)
    )
    assert result == 12


def test_partial_fill_is_seeded() -> None:
    supplier = SingleSupplier()
    parameters = SupplyParameters(lead_time=2, fill_rate=0.5)
    assert supplier.arrival_quantity(20, np.random.default_rng(4), parameters) == supplier.arrival_quantity(
        20, np.random.default_rng(4), parameters
    )


@pytest.mark.parametrize("quantity", [-1, 1.5])
def test_order_quantity_must_be_non_negative_integer(quantity) -> None:
    with pytest.raises((TypeError, ValueError)):
        SingleSupplier().arrival_quantity(
            quantity, np.random.default_rng(1), SupplyParameters(lead_time=1)
        )


def test_only_standard_supplier_is_supported() -> None:
    with pytest.raises(ValueError):
        SingleSupplier(supplier_id="other")
