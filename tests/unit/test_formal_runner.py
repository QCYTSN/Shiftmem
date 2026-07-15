from pathlib import Path

import pytest

from scripts.run_formal_experiment import (
    build_cell_plan,
    build_v2_cell_plan,
    validate_formal_config,
    validate_live_dry_run_config,
    validate_v2_config,
)


def v2_config() -> dict:
    return {
        "protocol": "v2",
        "models": [{"label": "deepseek"}, {"label": "minimax"}],
        "primary_methods": [{"config_id": "vector"}, {"config_id": "shiftmem"}],
        "secondary_methods": [
            {"config_id": name} for name in ["none", "full_history", "summary", "time_decay"]
        ],
        "secondary_model": "deepseek",
        "primary_seeds": 10,
        "secondary_seeds": 5,
        "post_shift_days": 30,
        "review_interval": 5,
        "cooldown": 3,
        "controller_profile": {
            "defaults": {
                "forecast_window": 14,
                "safety_stock_multiplier": 1.2,
                "lead_time_buffer": 1,
            },
            "bounds": {
                "forecast_window": [1, 60],
                "safety_stock_multiplier": [0.0, 5.0],
                "lead_time_buffer": [0, 14],
            },
        },
        "shiftmem_profile": {
            "memory": {
                "detector_min_samples": 10,
                "detector_delta": 0.1,
                "detector_threshold": 48.0,
                "validation_service_window": 3,
                "dormancy_patience": 3,
            },
            "retrieval": {"semantic": 0.75, "recency": 1.0},
        },
        "budget_approved": False,
        "budgets": {"max_calls": 100000, "max_input_tokens": 1, "max_output_tokens": 1, "max_cost_cny": 1},
    }


def test_v2_config_requires_two_primary_methods_and_two_models() -> None:
    invalid = v2_config()
    invalid["primary_methods"] = [{"config_id": "vector"}]
    with pytest.raises(ValueError, match="primary"):
        validate_v2_config(invalid)


def test_v2_config_rejects_implicit_runtime_defaults() -> None:
    invalid = v2_config()
    del invalid["shiftmem_profile"]
    with pytest.raises(ValueError, match="explicit ShiftMem"):
        validate_v2_config(invalid)


def test_v2_primary_tier_is_320_cells() -> None:
    scenarios = [f"validation-{i}" for i in range(8)]
    plan = build_v2_cell_plan(v2_config(), scenarios, list(range(10)), tier="primary")
    # 8 scenarios x 10 seeds x 2 models x 2 methods.
    assert len(plan) == 8 * 10 * 2 * 2
    assert len({row["cell_id"] for row in plan}) == len(plan)


def test_v2_secondary_tier_is_160_cells_deepseek_only() -> None:
    scenarios = [f"validation-{i}" for i in range(8)]
    plan = build_v2_cell_plan(v2_config(), scenarios, list(range(5)), tier="secondary")
    # 8 scenarios x 5 seeds x 1 model x 4 methods.
    assert len(plan) == 8 * 5 * 1 * 4
    assert all(row["model"] == "deepseek" for row in plan)


def test_v2_cell_plan_rejects_test_manifest() -> None:
    with pytest.raises(ValueError, match="Test-ID|Test-OOD"):
        build_v2_cell_plan(v2_config(), ["test-ood-periodic"], [1], tier="primary")


def config() -> dict:
    return {
        "models": [{"label": "a"}, {"label": "b"}],
        "methods": [
            {"config_id": name}
            for name in ["none", "full_history", "summary", "vector", "time_decay", "shiftmem"]
        ],
        "seeds_per_cell": 5,
        "post_shift_days": 30,
        "budget_approved": False,
        "budgets": {"max_calls": 1000, "max_input_tokens": 1, "max_output_tokens": 1, "max_cost_cny": 1},
    }


def test_formal_config_requires_exact_six_method_matrix() -> None:
    invalid = config()
    invalid["methods"] = invalid["methods"][:-1]
    with pytest.raises(ValueError, match="six methods"):
        validate_formal_config(invalid)


def test_cell_plan_is_deterministic_and_paired() -> None:
    scenarios = ["validation-a", "validation-b"]
    first = build_cell_plan(config(), scenarios, [10, 11])
    second = build_cell_plan(config(), scenarios, [10, 11])

    assert first == second
    assert len(first) == 2 * 2 * 2 * 6
    assert len({row["cell_id"] for row in first}) == len(first)


def test_dry_run_rejects_test_manifest_even_without_outcome_access() -> None:
    with pytest.raises(ValueError, match="Test-ID|Test-OOD"):
        build_cell_plan(config(), ["test-id-stable"], [1])


def test_live_dry_run_requires_explicit_cny_cap_and_approval() -> None:
    approved = config()
    approved["budget_approved"] = True
    approved["budgets"]["max_cost_cny"] = 30
    validate_live_dry_run_config(approved)

    approved["budgets"]["max_cost_cny"] = 31
    with pytest.raises(ValueError, match="30 CNY"):
        validate_live_dry_run_config(approved)
