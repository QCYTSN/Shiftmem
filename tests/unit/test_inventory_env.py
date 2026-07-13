import pytest

from shiftmem.envs.demand_models import DemandParameters
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import CostParameters, Scenario
from shiftmem.envs.supply_models import SupplyParameters


class ConstantDemand:
    def __init__(self, value: int) -> None:
        self.value = value

    def sample(self, rng, parameters) -> int:
        return self.value


def make_scenario(length: int = 4) -> Scenario:
    return Scenario(
        name="unit",
        episode_length=length,
        initial_inventory=10,
        demand_model="poisson",
        demand=DemandParameters(base_level=3),
        supply=SupplyParameters(lead_time=2),
        costs=CostParameters(purchase=1, holding=0.5, stockout=4, fixed_order=2),
    )


def test_reset_exposes_only_agent_visible_state() -> None:
    observation, info = InventoryEnv(make_scenario(), ConstantDemand(3)).reset(seed=42)
    assert observation == {
        "day": 0,
        "inventory": 10,
        "pipeline_inventory": 0,
        "last_demand": 0,
        "last_sales": 0,
    }
    assert info == {"scenario": "unit"}
    assert "demand_mean" not in observation


def test_step_conserves_inventory_and_costs() -> None:
    env = InventoryEnv(make_scenario(), ConstantDemand(3))
    env.reset(seed=1)
    _, reward, _, _, info = env.step({"order_quantity": 5, "supplier_id": "standard"})
    assert info["starting_inventory"] + info["arrivals"] - info["sales"] == info["ending_inventory"]
    assert info["ending_inventory"] == 7
    assert info["purchase_cost"] == 5
    assert info["holding_cost"] == 3.5
    assert info["stockout_cost"] == 0
    assert info["ordering_cost"] == 2
    assert info["total_cost"] == 10.5
    assert reward == -10.5


def test_order_arrives_only_after_lead_time() -> None:
    env = InventoryEnv(make_scenario(), ConstantDemand(0))
    env.reset(seed=1)
    _, _, _, _, day0 = env.step({"order_quantity": 5, "supplier_id": "standard"})
    _, _, _, _, day1 = env.step({"order_quantity": 0, "supplier_id": "standard"})
    _, _, _, _, day2 = env.step({"order_quantity": 0, "supplier_id": "standard"})
    assert [day0["arrivals"], day1["arrivals"], day2["arrivals"]] == [0, 0, 5]


def test_lost_sales_never_makes_inventory_negative() -> None:
    env = InventoryEnv(make_scenario(), ConstantDemand(30))
    env.reset(seed=1)
    _, _, _, _, info = env.step({"order_quantity": 0, "supplier_id": "standard"})
    assert info["sales"] == 10
    assert info["lost_sales"] == 20
    assert info["ending_inventory"] == 0


@pytest.mark.parametrize(
    "action",
    [
        {"order_quantity": -1, "supplier_id": "standard"},
        {"order_quantity": 1.5, "supplier_id": "standard"},
        {"order_quantity": 1, "supplier_id": "other"},
        {"order_quantity": 1},
    ],
)
def test_invalid_actions_are_rejected(action: dict) -> None:
    env = InventoryEnv(make_scenario(), ConstantDemand(1))
    env.reset(seed=1)
    with pytest.raises((TypeError, ValueError)):
        env.step(action)


def test_episode_terminates_at_configured_horizon() -> None:
    env = InventoryEnv(make_scenario(length=2), ConstantDemand(1))
    env.reset(seed=1)
    assert env.step({"order_quantity": 0, "supplier_id": "standard"})[2] is False
    final = env.step({"order_quantity": 0, "supplier_id": "standard"})
    assert final[2] is True
    assert final[3] is False
    with pytest.raises(RuntimeError):
        env.step({"order_quantity": 0, "supplier_id": "standard"})


def test_seed_reproduces_complete_records() -> None:
    first = InventoryEnv(make_scenario())
    second = InventoryEnv(make_scenario())
    first.reset(seed=99)
    second.reset(seed=99)
    for _ in range(4):
        action = {"order_quantity": 3, "supplier_id": "standard"}
        first.step(action)
        second.step(action)
    assert first.records == second.records


def test_oracle_context_is_separate_from_observation() -> None:
    env = InventoryEnv(make_scenario(), ConstantDemand(1))
    observation, _ = env.reset(seed=1)
    assert env.oracle_context() == {
        "demand_model": "poisson",
        "demand_mean": 3,
        "dispersion": 10.0,
        "lead_time": 2,
        "fill_rate": 1.0,
    }
    assert set(env.oracle_context()).isdisjoint(observation)


def test_uncertain_fill_is_not_revealed_before_arrival() -> None:
    scenario = Scenario(
        name="uncertain-fill",
        episode_length=3,
        initial_inventory=0,
        demand_model="poisson",
        demand=DemandParameters(base_level=1),
        supply=SupplyParameters(lead_time=2, fill_rate=0.5),
        costs=CostParameters(purchase=0, holding=0, stockout=0),
    )
    env = InventoryEnv(scenario, ConstantDemand(0))
    env.reset(seed=4)
    observation, _, _, _, first = env.step(
        {"order_quantity": 10, "supplier_id": "standard"}
    )
    assert observation["pipeline_inventory"] == 10
    assert first["pipeline_inventory"] == 10
    env.step({"order_quantity": 0, "supplier_id": "standard"})
    _, _, _, _, arrival_day = env.step(
        {"order_quantity": 0, "supplier_id": "standard"}
    )
    assert 0 <= arrival_day["arrivals"] <= 10
