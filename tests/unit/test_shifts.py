from pathlib import Path

import pytest

from shiftmem.envs.demand_models import DemandParameters
from shiftmem.envs.shifts import CostParameters, Scenario, Shift, load_scenario
from shiftmem.envs.supply_models import SupplyParameters


def scenario_with(shift: Shift) -> Scenario:
    return Scenario(
        name="test",
        episode_length=150,
        initial_inventory=20,
        demand_model="poisson",
        demand=DemandParameters(base_level=10),
        supply=SupplyParameters(lead_time=2),
        costs=CostParameters(purchase=1, holding=0.1, stockout=5),
        shifts=(shift,),
    )


def test_sudden_demand_applies_at_start_day() -> None:
    scenario = scenario_with(Shift("sudden_demand", start_day=5, changes={"base_level_multiplier": 2}))
    assert scenario.parameters_at(4).demand.mean == 10
    assert scenario.parameters_at(5).demand.mean == 20


def test_gradual_demand_interpolates_between_boundaries() -> None:
    scenario = scenario_with(Shift("gradual_demand", 10, 20, {"base_level_multiplier": 2}))
    assert scenario.parameters_at(10).demand.mean == 10
    assert scenario.parameters_at(15).demand.mean == 15
    assert scenario.parameters_at(20).demand.mean == 20


def test_periodic_demand_repeats() -> None:
    scenario = scenario_with(Shift("periodic_demand", 0, changes={"amplitude": 0.5, "period": 4}))
    assert scenario.parameters_at(0).demand.mean == pytest.approx(10)
    assert scenario.parameters_at(1).demand.mean == pytest.approx(15)
    assert scenario.parameters_at(5).demand.mean == pytest.approx(15)


def test_supply_shift_changes_lead_time() -> None:
    scenario = scenario_with(Shift("sudden_supply", 7, changes={"lead_time": 5, "fill_rate": 0.8}))
    assert scenario.parameters_at(6).supply.lead_time == 2
    assert scenario.parameters_at(7).supply == SupplyParameters(lead_time=5, fill_rate=0.8)


def test_combined_shift_changes_demand_and_supply() -> None:
    scenario = scenario_with(Shift("combined", 3, changes={"base_level_multiplier": 1.5, "lead_time": 4}))
    daily = scenario.parameters_at(3)
    assert daily.demand.mean == 15
    assert daily.supply.lead_time == 4


def test_false_alarm_restores_baseline() -> None:
    scenario = scenario_with(Shift("false_alarm", 3, 4, {"base_level_multiplier": 3}))
    assert scenario.parameters_at(3).demand.mean == 30
    assert scenario.parameters_at(5).demand.mean == 10


def test_invalid_scenario_and_shift_are_rejected() -> None:
    with pytest.raises(ValueError):
        scenario_with(Shift("unknown", 1))
    with pytest.raises(ValueError):
        Scenario(
            name="bad",
            episode_length=0,
            initial_inventory=0,
            demand_model="poisson",
            demand=DemandParameters(base_level=1),
            supply=SupplyParameters(lead_time=1),
            costs=CostParameters(purchase=1, holding=1, stockout=1),
        )


def test_load_stable_yaml() -> None:
    scenario = load_scenario(Path("configs/environments/stable.yaml"))
    assert scenario.episode_length == 150
    assert scenario.demand_model == "negative_binomial"
