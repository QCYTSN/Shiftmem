import numpy as np
import pytest

from shiftmem.agents.classical import (
    ExponentialSmoothingPolicy,
    FixedOrderPolicy,
    MovingAverageReorderPolicy,
    OraclePolicy,
    RandomOrderPolicy,
)
from shiftmem.envs.demand_models import DemandParameters
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import CostParameters, Scenario
from shiftmem.envs.supply_models import SupplyParameters


OBSERVATION = {
    "day": 0,
    "inventory": 4,
    "pipeline_inventory": 3,
    "last_demand": 10,
    "last_sales": 8,
}


@pytest.mark.parametrize(
    "policy",
    [
        FixedOrderPolicy(5),
        RandomOrderPolicy(0, 10, seed=1),
        MovingAverageReorderPolicy(window=3, lead_time=2, safety_stock=2),
        ExponentialSmoothingPolicy(alpha=0.5, lead_time=2, safety_stock=2),
    ],
)
def test_ordinary_policies_return_legal_action(policy) -> None:
    action = policy.act(OBSERVATION)
    assert action["supplier_id"] == "standard"
    assert isinstance(action["order_quantity"], int)
    assert action["order_quantity"] >= 0


def test_random_policy_is_reproducible() -> None:
    first = RandomOrderPolicy(0, 10, seed=9)
    second = RandomOrderPolicy(0, 10, seed=9)
    assert [first.act(OBSERVATION) for _ in range(5)] == [second.act(OBSERVATION) for _ in range(5)]


def test_moving_average_uses_history_and_pipeline() -> None:
    policy = MovingAverageReorderPolicy(window=2, lead_time=1, safety_stock=0)
    first = policy.act(OBSERVATION)
    second = policy.act({**OBSERVATION, "last_demand": 20})
    assert first["order_quantity"] == 13
    assert second["order_quantity"] == 23


def test_exponential_smoothing_updates_forecast() -> None:
    policy = ExponentialSmoothingPolicy(alpha=0.5, lead_time=1, safety_stock=0)
    assert policy.act(OBSERVATION)["order_quantity"] == 13
    assert policy.act({**OBSERVATION, "last_demand": 20})["order_quantity"] == 23


def test_malformed_observation_is_rejected() -> None:
    with pytest.raises(ValueError):
        FixedOrderPolicy(2).act({"inventory": 1})


def run_cost(policy, seed: int, oracle: bool = False) -> float:
    scenario = Scenario(
        name="oracle-check",
        episode_length=60,
        initial_inventory=20,
        demand_model="poisson",
        demand=DemandParameters(base_level=10),
        supply=SupplyParameters(lead_time=2),
        costs=CostParameters(purchase=0.1, holding=0.2, stockout=10),
    )
    env = InventoryEnv(scenario)
    observation, _ = env.reset(seed=seed)
    done = False
    while not done:
        action = policy.act(observation, env.oracle_context()) if oracle else policy.act(observation)
        observation, _, done, _, _ = env.step(action)
    return sum(record["total_cost"] for record in env.records)


def test_oracle_mean_cost_is_below_random_policy() -> None:
    oracle_costs = [run_cost(OraclePolicy(), seed, oracle=True) for seed in range(10)]
    random_costs = [run_cost(RandomOrderPolicy(0, 20, seed=seed), seed) for seed in range(10)]
    assert np.mean(oracle_costs) < np.mean(random_costs)
