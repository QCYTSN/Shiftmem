"""Tests for the v2 protocol gate and Validation-only Pilot dry-run."""

from pathlib import Path

import pytest
import yaml

from scripts.validate_protocol import validate_protocol_v2
from scripts.run_v2_pilot import build_pilot_plan, validate_pilot_config


def _pilot_config():
    return {
        "protocol": "v2",
        "split": "Validation",
        "provider": "deterministic",
        "memory_methods": ["vector", "shiftmem"],
        "models": [{"label": "deepseek"}],
        "seeds": [1000, 1001],
        "max_days": 40,
        "review_interval": 5,
        "cooldown": 3,
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


def test_pilot_stops_before_exceeding_call_cap():
    from scripts.run_v2_pilot import run_pilot
    from shiftmem.providers.local import DeterministicStrategyProvider

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
