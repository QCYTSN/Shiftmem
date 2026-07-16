from shiftmem.envs.demand_models import DemandParameters
from shiftmem.envs.shifts import CostParameters, Scenario, Shift
from shiftmem.envs.supply_models import SupplyParameters
from shiftmem.evaluation.formal_v2 import (
    aggregate_results,
    execute_cell,
    execute_offline_cell,
    run_oracle_episode,
    validate_plan_completeness,
)
from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, RunIdentity
from shiftmem.providers.journaled import JournaledProvider
from shiftmem.providers.local import DeterministicStrategyProvider


def config() -> dict:
    return {
        "review_interval": 5,
        "cooldown": 3,
        "shiftmem_profile": {
            "memory": {
                "detector_min_samples": 10,
                "detector_delta": 0.1,
                "detector_threshold": 48.0,
                "validation_service_window": 3,
                "dormancy_patience": 3,
            },
            "retrieval": {
                "semantic": 0.75,
                "confidence": 0.5,
                "recency": 1.0,
                "utility": 0.25,
                "probation_penalty": 0.25,
                "changed_variable_penalty": 0.5,
                "recency_half_life": 30.0,
            },
        },
    }


def scenario(stable: bool = False) -> Scenario:
    return Scenario(
        name="formal-offline",
        episode_length=40,
        initial_inventory=30,
        demand_model="poisson",
        demand=DemandParameters(base_level=5),
        supply=SupplyParameters(lead_time=1, fill_rate=0.8),
        costs=CostParameters(purchase=1, holding=0.1, stockout=5),
        shifts=()
        if stable
        else (Shift(type="sudden_demand", start_day=5, changes={"base_level_multiplier": 1.5}),),
    )


def test_offline_rehearsal_exercises_all_six_methods_and_oracle_pairing() -> None:
    subject = scenario()
    oracle = run_oracle_episode(subject, seed=7)
    methods = ["none", "full_history", "summary", "vector", "time_decay", "shiftmem"]
    plan = [
        {
            "cell_id": f"cell-{method}",
            "tier": "primary" if method in {"vector", "shiftmem"} else "secondary",
            "scenario_id": "validation-unit",
            "seed": 7,
            "model": "offline",
            "method": method,
        }
        for method in methods
    ]
    results = [execute_offline_cell(row, subject, config(), oracle) for row in plan]

    summary = aggregate_results(plan, results)
    assert summary["cells"] == 6
    assert summary["provider_calls"] == 0
    assert summary["test_outcomes_accessed"] is False
    assert set(summary["methods"]) == set(methods)
    assert all(row.post_shift_cumulative_regret_30 is not None for row in results)


def test_stable_cell_marks_adaptation_endpoint_not_applicable() -> None:
    subject = scenario(stable=True)
    row = {
        "cell_id": "stable-vector",
        "tier": "primary",
        "scenario_id": "validation-stable",
        "seed": 8,
        "model": "offline",
        "method": "vector",
    }
    result = execute_offline_cell(
        row, subject, config(), run_oracle_episode(subject, seed=8)
    )
    assert result.endpoint_applicable is False
    assert result.shift_day is None
    assert result.post_shift_cumulative_regret_30 is None
    assert result.recovery is None


def test_completeness_rejects_missing_paired_cell() -> None:
    subject = scenario(stable=True)
    row = {
        "cell_id": "vector",
        "tier": "primary",
        "scenario_id": "validation-stable",
        "seed": 8,
        "model": "offline",
        "method": "vector",
    }
    plan = [row, {**row, "cell_id": "shiftmem", "method": "shiftmem"}]
    result = execute_offline_cell(
        row, subject, config(), run_oracle_episode(subject, seed=8)
    )
    try:
        validate_plan_completeness(plan, [result])
    except ValueError as error:
        assert "missing" in str(error)
    else:
        raise AssertionError("missing paired cell was accepted")


def test_formal_cell_attempts_are_freeze_bound_and_replayed(tmp_path) -> None:
    class CountingProvider(DeterministicStrategyProvider):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def generate(self, request):
            self.calls += 1
            return super().generate(request)

        def token_budget_upper_bounds(self, request) -> tuple[int, int]:
            return 10_000, 512

    identity = RunIdentity(
        run_id="formal-replay",
        freeze_id="v2-freeze",
        git_commit="a" * 40,
        config_hash="b" * 64,
    )
    limits = BudgetLimits(
        max_calls=100,
        max_input_tokens=1_000_000,
        max_output_tokens=100_000,
        max_cost_cny=100,
    )
    journal_path = tmp_path / "journal.jsonl"
    subject = scenario(stable=True)
    oracle = run_oracle_episode(subject, seed=8)
    row = {
        "cell_id": "journal-vector",
        "tier": "primary",
        "scenario_id": "validation-stable",
        "seed": 8,
        "model": "deepseek",
        "method": "vector",
    }
    delegate = CountingProvider()
    first_journal = JsonlRunJournal(journal_path, identity, limits)
    first = JournaledProvider(
        delegate,
        first_journal,
        4.0,
        6.0,
        require_preflight_reservation=True,
    )
    run_identity = identity.model_dump(mode="json")
    first_result = execute_cell(
        row,
        subject,
        config(),
        oracle,
        provider=first,
        run_identity=run_identity,
    )
    first_calls = delegate.calls
    assert first_calls > 0
    assert first_journal.totals()["reserved_attempts"] == 0
    assert first_result.run_identity == run_identity

    resumed_journal = JsonlRunJournal(journal_path, identity, limits)
    resumed = JournaledProvider(
        delegate,
        resumed_journal,
        4.0,
        6.0,
        require_preflight_reservation=True,
    )
    execute_cell(
        row,
        subject,
        config(),
        oracle,
        provider=resumed,
        run_identity=run_identity,
    )
    assert delegate.calls == first_calls
    assert resumed_journal.totals()["calls"] == first_calls
