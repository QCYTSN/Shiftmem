import numpy as np
import pytest

from shiftmem.envs.demand_models import (
    DemandParameters,
    NegativeBinomialDemand,
    PoissonDemand,
)


def test_demand_mean_multiplies_all_factors() -> None:
    parameters = DemandParameters(
        base_level=20,
        seasonal_factor=1.5,
        promotion_factor=2,
        external_factor=0.5,
    )
    assert parameters.mean == 30


@pytest.mark.parametrize(
    "kwargs",
    [
        {"base_level": 0},
        {"seasonal_factor": 0},
        {"promotion_factor": -1},
        {"external_factor": 0},
        {"dispersion": 0},
    ],
)
def test_demand_parameters_reject_non_positive_values(kwargs: dict) -> None:
    values = {"base_level": 10, **kwargs}
    with pytest.raises(ValueError):
        DemandParameters(**values)


@pytest.mark.parametrize("model", [PoissonDemand(), NegativeBinomialDemand()])
def test_sampling_is_reproducible_and_non_negative(model) -> None:
    parameters = DemandParameters(base_level=20, dispersion=4)
    first = [model.sample(np.random.default_rng(42), parameters) for _ in range(1)]
    second = [model.sample(np.random.default_rng(42), parameters) for _ in range(1)]
    assert first == second
    assert isinstance(first[0], int)
    assert first[0] >= 0


def test_negative_binomial_is_overdispersed() -> None:
    model = NegativeBinomialDemand()
    parameters = DemandParameters(base_level=20, dispersion=4)
    rng = np.random.default_rng(7)
    samples = np.array([model.sample(rng, parameters) for _ in range(20_000)])
    assert samples.var() > samples.mean()
