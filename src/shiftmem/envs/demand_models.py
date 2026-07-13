"""Demand-process models used by inventory scenarios."""

from dataclasses import dataclass
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class DemandParameters:
    """Validated parameters controlling a daily demand distribution."""

    base_level: float
    seasonal_factor: float = 1.0
    promotion_factor: float = 1.0
    external_factor: float = 1.0
    dispersion: float = 10.0

    def __post_init__(self) -> None:
        for name in (
            "base_level",
            "seasonal_factor",
            "promotion_factor",
            "external_factor",
            "dispersion",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

    @property
    def mean(self) -> float:
        return (
            self.base_level
            * self.seasonal_factor
            * self.promotion_factor
            * self.external_factor
        )


class DemandModel(Protocol):
    """Protocol implemented by stochastic daily demand models."""

    def sample(
        self, rng: np.random.Generator, parameters: DemandParameters
    ) -> int: ...


class PoissonDemand:
    """Poisson demand with variance equal to its mean."""

    def sample(self, rng: np.random.Generator, parameters: DemandParameters) -> int:
        return int(rng.poisson(parameters.mean))


class NegativeBinomialDemand:
    """Overdispersed negative-binomial demand."""

    def sample(self, rng: np.random.Generator, parameters: DemandParameters) -> int:
        probability = parameters.dispersion / (parameters.dispersion + parameters.mean)
        return int(rng.negative_binomial(parameters.dispersion, probability))
