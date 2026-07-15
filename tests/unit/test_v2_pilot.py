"""Tests for the v2 protocol gate and Validation-only Pilot dry-run."""

from pathlib import Path

import pytest
import yaml

from scripts.validate_protocol import validate_protocol_v2
from scripts.run_v2_pilot import (
    _effective_call_cap,
    build_pilot_plan,
    run_pilot,
    validate_pilot_config,
)
from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, RunIdentity
from shiftmem.providers.local import DeterministicStrategyProvider


def _pilot_config():
    return {
        "protocol": "v2",
        "split": "Validation",
        "provider": "deterministic",
        "memory_methods": ["vector", "shiftmem"],
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
        "models": [{"label": "deepseek"}],
        "seeds": [1000, 1001],
        "max_days": 40,
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
            "max_review_deltas": {
                "forecast_window": 7,
                "safety_stock_multiplier": 1.0,
                "lead_time_buffer": 1,
            },
        },
        "budget_approved": False,
    }


def test_protocol_v2_gate_requires_controller_and_scheduler_terms(tmp_path):
    weak = tmp_path / "p.md"
    weak.write_text("# Experiment Protocol\nNo v2 machinery described.", encoding="utf-8")
    errors = validate_protocol_v2(weak)
    assert any("deterministic controller" in e.lower() for e in errors)
    assert any("strategy" in e.lower() for e in errors)


def test_real_v2_protocol_passes_v2_gate():
    errors = validate_protocol_v2(Path("docs/experiment_protocol.md"))
    assert errors == []


def test_v2_protocol_records_qualification_stop_rule():
    text = Path("docs/experiment_protocol.md").read_text(encoding="utf-8")
    assert "inconclusive_harness_invalid" in text
    assert "one newly budget-approved qualification run" in text
    assert "monotonicity_passes == 4" in text


def test_pilot_config_must_be_validation_only():
    bad = _pilot_config()
    bad["split"] = "Test-ID"
    with pytest.raises(ValueError, match="Validation"):
        validate_pilot_config(bad)


def test_pilot_plan_is_deterministic_and_offline_by_default():
    plan = build_pilot_plan(_pilot_config())
    # 2 methods x 1 model x 2 seeds.
    assert len(plan) == 2 * 1 * 2
    assert build_pilot_plan(_pilot_config()) == plan


def test_pilot_live_execution_requires_budget_approval():
    live = _pilot_config()
    live["provider"] = "siliconflow"
    with pytest.raises(ValueError, match="budget"):
        validate_pilot_config(live)


def test_pilot_rejects_implicit_shiftmem_defaults():
    config = _pilot_config()
    del config["shiftmem_profile"]
    with pytest.raises(ValueError, match="explicit runtime profile"):
        validate_pilot_config(config)


def test_pilot_stops_before_exceeding_call_cap():
    cfg = _pilot_config()
    cfg["budgets"] = {"max_calls": 3, "max_cost_cny": 6, "cny_per_call": 0.01}
    # A counting factory so the test never touches the network.
    counter = {"calls": 0}

    class _Counting(DeterministicStrategyProvider):
        def generate(self, request):
            counter["calls"] += 1
            return super().generate(request)

    with pytest.raises(RuntimeError, match="call cap"):
        run_pilot(
            cfg,
            [Path("configs/environments/validation_demand_jump.yaml")],
            provider_override=_Counting(),
        )
    # It stopped at or before the cap rather than blowing past it.
    assert counter["calls"] <= 3


def _live_config():
    config = _pilot_config()
    config.update(
        {
            "provider": "siliconflow",
            "budget_approved": True,
            "memory_methods": ["vector"],
            "models": [
                {
                    "label": "deepseek",
                    "profile": "siliconflow",
                    "model_id": "deepseek-ai/DeepSeek-V3.2",
                    "input_cny_per_million": 4.0,
                    "output_cny_per_million": 6.0,
                }
            ],
            "seeds": [1000],
            "max_days": 12,
            "budgets": {
                "max_calls": 10,
                "max_input_tokens": 10000,
                "max_output_tokens": 10000,
                "max_cost_cny": 0.05,
                "cny_per_call": 0.01,
            },
        }
    )
    return config


def test_live_pilot_requires_complete_model_pricing_and_token_budgets():
    live = _live_config()
    del live["models"][0]["output_cny_per_million"]
    with pytest.raises(ValueError, match="pricing"):
        validate_pilot_config(live)

    live = _live_config()
    del live["budgets"]["max_output_tokens"]
    with pytest.raises(ValueError, match="budget"):
        validate_pilot_config(live)


def test_live_pilot_cost_ceiling_reduces_effective_call_cap():
    assert _effective_call_cap(_live_config()) == 5


def test_live_pilot_journals_attempts_and_resumes_without_new_calls(tmp_path):
    config = _live_config()
    identity = RunIdentity(
        run_id="pilot-test",
        freeze_id="pilot-freeze",
        git_commit="a" * 40,
        config_hash="b" * 64,
    )
    limits = BudgetLimits(
        max_calls=5,
        max_input_tokens=10000,
        max_output_tokens=10000,
        max_cost_cny=0.05,
    )
    journal = JsonlRunJournal(tmp_path / "journal.jsonl", identity, limits)
    raw = tmp_path / "raw.jsonl"
    aggregate = tmp_path / "summary.json"
    calls = {"count": 0}

    class _Counting(DeterministicStrategyProvider):
        def generate(self, request):
            calls["count"] += 1
            return super().generate(request)

    metadata = {"run_id": "pilot-test"}
    report = run_pilot(
        config,
        [Path("configs/environments/validation_demand_jump.yaml")],
        provider_override=_Counting(),
        journal=journal,
        raw_output=raw,
        aggregate_output=aggregate,
        run_metadata=metadata,
    )
    assert report["complete"] is True
    assert report["completed_cells"] == 1
    assert journal.totals()["calls"] == calls["count"] == report["provider_calls"]
    assert raw.read_text(encoding="utf-8").count("\n") == 1

    resumed = run_pilot(
        config,
        [Path("configs/environments/validation_demand_jump.yaml")],
        provider_override=_Counting(),
        journal=journal,
        raw_output=raw,
        aggregate_output=aggregate,
        run_metadata=metadata,
        resume=True,
    )
    assert resumed["complete"] is True
    assert calls["count"] == report["provider_calls"]
