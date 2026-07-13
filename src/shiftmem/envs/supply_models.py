"""Supply and lead-time models used by inventory scenarios."""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SupplyParameters:
    """Parameters for a single supplier on a given day."""

    lead_time: int
    fill_rate: float = 1.0

    def __post_init__(self) -> None:
        if not isinstance(self.lead_time, int) or self.lead_time < 1:
            raise ValueError("lead_time must be an integer of at least one day")
        if not 0 <= self.fill_rate <= 1:
            raise ValueError("fill_rate must be between zero and one")


class SingleSupplier:
    """A single standard supplier with stochastic order fill."""

    def __init__(self, supplier_id: str = "standard") -> None:
        if supplier_id != "standard":
            raise ValueError("Phase 1 supports only the standard supplier")
        self.supplier_id = supplier_id

    def arrival_quantity(
        self,
        order_quantity: int,
        rng: np.random.Generator,
        parameters: SupplyParameters,
    ) -> int:
        if not isinstance(order_quantity, (int, np.integer)):
            raise TypeError("order_quantity must be an integer")
        if order_quantity < 0:
            raise ValueError("order_quantity must be non-negative")
        if parameters.fill_rate == 1:
            return int(order_quantity)
        return int(rng.binomial(order_quantity, parameters.fill_rate))
