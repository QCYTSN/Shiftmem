"""Tests for the deterministic parameterized inventory controller."""

import pytest

from shiftmem.control.controller import DeterministicController, StrategyParameters


def _observation(recent=None, inventory=50, pipeline=0, lead_time=2):
    history = recent if recent is not None else [
        {"day": d, "demand": 20, "sales": 20, "lost_sales": 0,
         "ending_inventory": 50, "order_quantity": 20, "arrivals": 20,
         "total_cost": 0.0}
        for d in range(14)
    ]
    return {
        "day": 14,
        "inventory": inventory,
        "pipeline_inventory": pipeline,
        "pipeline_orders": [],
        "quoted_lead_time": lead_time,
        "last_demand": 20,
        "last_sales": 20,
        "costs": {"purchase": 1.0, "holding": 0.1, "stockout": 2.0, "fixed_order": 0.0},
        "recent_history": history,
    }


def test_strategy_parameters_defaults_within_bounds():
    strategy = StrategyParameters()
    assert strategy.forecast_window >= 1
    assert strategy.safety_stock_multiplier >= 0
    assert strategy.lead_time_buffer >= 0


def test_strategy_parameters_clamp_out_of_range():
    clamped = StrategyParameters.clamp(
        forecast_window=999, safety_stock_multiplier=-5.0, lead_time_buffer=999
    )
    bounds = StrategyParameters.bounds()
    assert clamped.forecast_window == bounds["forecast_window"][1]
    assert clamped.safety_stock_multiplier == bounds["safety_stock_multiplier"][0]
    assert clamped.lead_time_buffer == bounds["lead_time_buffer"][1]


def test_order_is_non_negative_integer_action():
    controller = DeterministicController()
    action = controller.order(_observation(), StrategyParameters())
    assert set(action) == {"order_quantity", "supplier_id"}
    assert action["supplier_id"] == "standard"
    assert isinstance(action["order_quantity"], int)
    assert action["order_quantity"] >= 0


def test_order_is_deterministic_for_identical_inputs():
    controller = DeterministicController()
    strategy = StrategyParameters()
    obs = _observation()
    first = controller.order(obs, strategy)
    second = controller.order(obs, strategy)
    assert first == second


def test_higher_safety_multiplier_increases_order_under_variable_demand():
    controller = DeterministicController()
    # Variable demand gives non-zero sigma so the safety term is exercised.
    varied = [
        {"day": d, "demand": 10 + (d % 5) * 8, "sales": 20, "lost_sales": 0,
         "ending_inventory": 50, "order_quantity": 20, "arrivals": 20,
         "total_cost": 0.0}
        for d in range(14)
    ]
    obs = _observation(recent=varied)
    low = controller.order(obs, StrategyParameters(safety_stock_multiplier=1.0))
    high = controller.order(obs, StrategyParameters(safety_stock_multiplier=2.0))
    assert high["order_quantity"] > low["order_quantity"]


def test_forecast_uses_public_history_only_not_hidden_truth():
    controller = DeterministicController()
    obs = _observation()
    obs["demand_mean"] = 10_000  # hidden-truth style key must be ignored
    baseline = controller.order(_observation(), StrategyParameters())
    with_hidden = controller.order(obs, StrategyParameters())
    assert with_hidden["order_quantity"] == baseline["order_quantity"]


def test_order_rejects_oracle_context_keys():
    controller = DeterministicController()
    obs = _observation()
    obs["fill_rate"] = 0.9
    obs["regime_id"] = 3
    with pytest.raises(ValueError):
        controller.order(obs, StrategyParameters(), strict=True)


def test_order_covers_position_gap():
    controller = DeterministicController()
    strategy = StrategyParameters()
    empty = controller.order(_observation(inventory=0, pipeline=0), strategy)
    full = controller.order(_observation(inventory=500, pipeline=0), strategy)
    assert empty["order_quantity"] > full["order_quantity"]
    assert full["order_quantity"] == 0
