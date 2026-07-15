"""Development/Validation-only v2 Pilot: measure review frequency and cost.

The Pilot never touches Test-ID/Test-OOD. Offline (deterministic) runs are the
default and require no approval. Live provider runs require an explicitly
approved budget, mirroring the formal-runner gate, so no accidental spend can
occur. The Pilot reports review frequency, token/latency, parameter behavior,
and variance but no confirmatory held-out p-values.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from shiftmem.control.episode import V2EpisodeConfig, run_v2_episode
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.metrics import summarize_episode, summarize_strategy_reviews
from shiftmem.memory.store import make_memory
from shiftmem.providers.local import DeterministicStrategyProvider

_OFFLINE_PROVIDERS = {"deterministic"}


def validate_pilot_config(config: dict[str, Any]) -> None:
    if config.get("protocol") != "v2":
        raise ValueError("pilot protocol must be v2")
    split = str(config.get("split", ""))
    if split not in {"Development", "Validation"}:
        raise ValueError("pilot split must be Development or Validation only")
    provider = str(config.get("provider", "deterministic"))
    if provider not in _OFFLINE_PROVIDERS and config.get("budget_approved") is not True:
        raise ValueError("live pilot provider requires explicit budget approval")


def build_pilot_plan(config: dict[str, Any]) -> list[dict[str, Any]]:
    validate_pilot_config(config)
    rows: list[dict[str, Any]] = []
    for method in config["memory_methods"]:
        for model in config["models"]:
            for seed in config["seeds"]:
                rows.append(
                    {
                        "method": str(method),
                        "model": str(model["label"]),
                        "seed": int(seed),
                    }
                )
    return rows


def _make_provider(config: dict[str, Any], model_label: str | None = None):
    provider = str(config.get("provider", "deterministic"))
    if provider in _OFFLINE_PROVIDERS:
        return DeterministicStrategyProvider()
    # Live path: only reachable when validate_pilot_config confirmed approval.
    from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig
    from shiftmem.providers.inventory_prompt import (
        STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_strategy_review_user_message,
    )

    model_name = None
    for model in config.get("models", []):
        if model_label is None or str(model["label"]) == model_label:
            model_name = model.get("model_name")
            break
    return CompatibleAPIProvider(
        ProviderConfig.from_env(provider, model_override=model_name),
        system_prompt=STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_user_message=build_strategy_review_user_message,
    )


class _BudgetStop(BaseException):
    """Control-flow signal for a reached budget cap.

    Inherits BaseException, not Exception, so the strategy agent's broad
    ``except Exception`` fallback handler cannot swallow it and let execution
    continue past the cap.
    """


class _BudgetedProvider:
    """Wrap a provider and hard-stop before a call cap is exceeded."""

    def __init__(self, inner, counter: dict[str, int], max_calls: int):
        self._inner = inner
        self._counter = counter
        self._max_calls = max_calls

    def generate(self, request):
        if self._counter["calls"] >= self._max_calls:
            raise _BudgetStop(f"call cap reached: {self._max_calls}")
        self._counter["calls"] += 1
        return self._inner.generate(request)


def run_pilot(
    config: dict[str, Any],
    scenario_paths: list[Path],
    provider_override: Any | None = None,
) -> dict[str, Any]:
    validate_pilot_config(config)
    plan = build_pilot_plan(config)
    budgets = config.get("budgets", {})
    max_calls = int(budgets.get("max_calls", 0)) or 10**9
    cny_per_call = float(budgets.get("cny_per_call", 0.0))
    counter = {"calls": 0}

    cells: list[dict[str, Any]] = []
    for scenario_path in scenario_paths:
        scenario = load_scenario(scenario_path)
        for row in plan:
            base = provider_override or _make_provider(config, row["model"])
            provider = _BudgetedProvider(base, counter, max_calls)
            try:
                result = run_v2_episode(
                    scenario=scenario,
                    provider=provider,
                    memory=make_memory(row["method"]),
                    config=V2EpisodeConfig(
                        seed=row["seed"],
                        max_days=int(config["max_days"]),
                        review_interval=int(config["review_interval"]),
                        cooldown=int(config["cooldown"]),
                    ),
                )
            except _BudgetStop as stop:
                raise RuntimeError(str(stop)) from None
            reviews = summarize_strategy_reviews(
                result["scheduler_log"], result["review_logs"]
            )
            episode = summarize_episode(result["environment_records"])
            cells.append(
                {
                    "scenario": scenario.name,
                    **row,
                    "total_cost": episode["total_cost"],
                    "fill_rate": episode["fill_rate"],
                    **reviews,
                }
            )
    return {
        "protocol": "v2",
        "split": config["split"],
        "provider": config["provider"],
        "test_outcomes_accessed": False,
        "cells": cells,
        "provider_calls": counter["calls"],
        "estimated_cost_cny": round(counter["calls"] * cny_per_call, 4),
        "total_reviews": sum(c["total_reviews"] for c in cells),
        "total_fallbacks": sum(c["fallback_count"] for c in cells),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--scenario", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    report = run_pilot(config, args.scenario)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "cells"}, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
