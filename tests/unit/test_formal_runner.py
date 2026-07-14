from pathlib import Path

import pytest

from scripts.run_formal_experiment import (
    build_cell_plan,
    validate_formal_config,
    validate_live_dry_run_config,
)


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
