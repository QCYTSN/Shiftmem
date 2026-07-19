"""Development/Validation-only protocol-v2 Pilot runner.

Offline deterministic execution is the default. Live execution additionally
requires an approved budget, a clean repository, a verified harness manifest,
run-specific outputs, and an fsynced provider-attempt journal. No Test split is
accepted by this runner.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
import math
import os
from pathlib import Path
import platform
import subprocess
from typing import Any

import yaml

from shiftmem.control.episode import V2EpisodeConfig, run_v2_episode
from shiftmem.control.controller import StrategyParameters
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.metrics import summarize_episode, summarize_strategy_reviews
from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, RunIdentity
from shiftmem.memory.store import make_memory
from shiftmem.providers.journaled import JournaledProvider
from shiftmem.providers.local import DeterministicStrategyProvider


_OFFLINE_PROVIDERS = {"deterministic"}


class _BudgetStop(BaseException):
    """Fail-closed signal that the agent's ``except Exception`` cannot swallow."""


class _BudgetedProvider:
    """Stop before an external call would exceed the approved effective cap."""

    def __init__(
        self,
        inner: Any,
        counter: dict[str, int],
        max_calls: int,
    ) -> None:
        self._inner = inner
        self._counter = counter
        self._max_calls = max_calls

    def generate(self, request: Any) -> Any:
        if self._counter["calls"] >= self._max_calls:
            raise _BudgetStop(f"call cap reached: {self._max_calls}")
        self._counter["calls"] += 1
        return self._inner.generate(request)


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        default=_json_default,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _cell_id(scenario: str, model: str, method: str, seed: int) -> str:
    logical = f"{scenario}|{model}|{method}|{seed}"
    return hashlib.sha256(logical.encode("utf-8")).hexdigest()[:20]


def _git_metadata() -> dict[str, Any]:
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    return {"git_revision": revision, "git_dirty": dirty}


def _runtime_metadata(config: dict[str, Any], scenario_paths: list[Path]) -> dict[str, Any]:
    dependencies: dict[str, str] = {}
    for package in ("numpy", "pydantic", "gymnasium", "scipy", "PyYAML"):
        try:
            dependencies[package] = version(package)
        except PackageNotFoundError:
            dependencies[package] = "not-installed"
    from shiftmem.providers.inventory_prompt import STRATEGY_REVIEW_SYSTEM_PROMPT

    return {
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "device_class": "cpu-simulation-remote-api",
        "dependencies": dependencies,
        "models": config["models"],
        "memory_methods": config["memory_methods"],
        "shiftmem_profile": config.get("shiftmem_profile"),
        "controller_profile": config.get("controller_profile"),
        "seeds": config["seeds"],
        "max_days": config["max_days"],
        "review_interval": config["review_interval"],
        "cooldown": config["cooldown"],
        "strategy_defaults": StrategyParameters().model_dump(),
        "strategy_bounds": StrategyParameters.bounds(),
        "strategy_max_review_deltas": StrategyParameters.max_review_deltas(),
        "scenarios": [
            {"path": str(path), "sha256": _sha256_file(path)}
            for path in scenario_paths
        ],
        "system_prompt_sha256": hashlib.sha256(
            STRATEGY_REVIEW_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "user_message_builder": "build_strategy_review_user_message",
    }


def _validate_scenario_paths(paths: list[Path], split: str) -> None:
    for path in paths:
        lowered = path.name.lower()
        if "test" in lowered:
            raise ValueError("Pilot must not reference Test scenarios")
        if split == "Validation" and "validation" not in lowered:
            raise ValueError("Validation Pilot requires Validation scenario paths")


def validate_pilot_config(config: dict[str, Any]) -> None:
    if config.get("protocol") != "v2":
        raise ValueError("pilot protocol must be v2")
    split = str(config.get("split", ""))
    if split not in {"Development", "Validation"}:
        raise ValueError("pilot split must be Development or Validation only")
    if not config.get("models") or not config.get("memory_methods") or not config.get("seeds"):
        raise ValueError("pilot requires models, memory methods, and seeds")
    if "shiftmem" in config["memory_methods"] and not config.get("shiftmem_profile"):
        raise ValueError("Pilot with ShiftMem requires an explicit runtime profile")
    controller = config.get("controller_profile", {})
    expected_bounds = {
        key: list(value) for key, value in StrategyParameters.bounds().items()
    }
    if (
        controller.get("defaults") != StrategyParameters().model_dump()
        or controller.get("bounds") != expected_bounds
        or controller.get("max_review_deltas")
        != StrategyParameters.max_review_deltas()
    ):
        raise ValueError("Pilot controller profile must match the implementation")
    provider = str(config.get("provider", "deterministic"))
    if provider in _OFFLINE_PROVIDERS:
        return
    if config.get("budget_approved") is not True:
        raise ValueError("live pilot provider requires explicit budget approval")
    budgets = config.get("budgets", {})
    required_budget = {
        "max_calls",
        "max_input_tokens",
        "max_output_tokens",
        "max_cost_cny",
        "cny_per_call",
    }
    if not required_budget.issubset(budgets):
        raise ValueError("live pilot budget is incomplete")
    if any(float(budgets[name]) <= 0 for name in required_budget):
        raise ValueError("live pilot budget limits must be positive")
    for model in config["models"]:
        required_model = {
            "label",
            "profile",
            "model_id",
            "input_cny_per_million",
            "output_cny_per_million",
        }
        if not required_model.issubset(model):
            raise ValueError("live pilot model pricing/configuration is incomplete")
        if float(model["input_cny_per_million"]) < 0 or float(
            model["output_cny_per_million"]
        ) < 0:
            raise ValueError("live pilot model rates must be nonnegative")


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


def _model_config(config: dict[str, Any], label: str) -> dict[str, Any]:
    for model in config["models"]:
        if str(model["label"]) == label:
            return model
    raise ValueError(f"unknown pilot model: {label}")


def _make_provider(config: dict[str, Any], model_label: str) -> Any:
    provider = str(config.get("provider", "deterministic"))
    if provider in _OFFLINE_PROVIDERS:
        return DeterministicStrategyProvider()
    from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig
    from shiftmem.providers.inventory_prompt import (
        STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_strategy_review_user_message,
    )

    model = _model_config(config, model_label)
    return CompatibleAPIProvider(
        ProviderConfig.from_env(
            str(model["profile"]), model_override=str(model["model_id"])
        ),
        system_prompt=STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_user_message=build_strategy_review_user_message,
    )


def _effective_call_cap(config: dict[str, Any]) -> int:
    budgets = config.get("budgets", {})
    configured = int(budgets.get("max_calls", 0)) or 10**9
    cost = float(budgets.get("max_cost_cny", 0))
    per_call = float(budgets.get("cny_per_call", 0))
    if cost > 0 and per_call > 0:
        configured = min(configured, math.floor(cost / per_call))
    return configured


def _cell_summary(result: dict[str, Any], row: dict[str, Any], scenario: str) -> dict[str, Any]:
    reviews = summarize_strategy_reviews(result["scheduler_log"], result["review_logs"])
    episode = summarize_episode(result["environment_records"])
    attempts = [
        attempt
        for review in result["review_logs"]
        for attempt in review.get("attempts", [])
    ]
    return {
        "scenario": scenario,
        **row,
        "total_cost": episode["total_cost"],
        "fill_rate": episode["fill_rate"],
        **reviews,
        "attempt_count": len(attempts),
        "parse_failure_count": sum(
            attempt.get("parse_error") is not None for attempt in attempts
        ),
        "input_tokens": sum(int(attempt.get("input_tokens", 0)) for attempt in attempts),
        "output_tokens": sum(int(attempt.get("output_tokens", 0)) for attempt in attempts),
        "latency_ms": sum(float(attempt.get("latency_ms", 0)) for attempt in attempts),
    }


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(row, default=_json_default, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(report, default=_json_default, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def run_pilot(
    config: dict[str, Any],
    scenario_paths: list[Path],
    provider_override: Any | None = None,
    *,
    journal: JsonlRunJournal | None = None,
    raw_output: Path | None = None,
    aggregate_output: Path | None = None,
    run_metadata: dict[str, Any] | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    validate_pilot_config(config)
    plan = build_pilot_plan(config)
    budgets = config.get("budgets", {})
    counter = {"calls": int(journal.totals()["calls"]) if journal else 0}
    effective_cap = _effective_call_cap(config)

    existing: dict[str, dict[str, Any]] = {}
    if raw_output and raw_output.exists():
        if not resume:
            raise FileExistsError(f"raw output already exists: {raw_output}")
        for line in raw_output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                raw = json.loads(line)
                existing[str(raw["cell_id"])] = raw

    cells: list[dict[str, Any]] = [raw["summary"] for raw in existing.values()]
    expected_cells = len(scenario_paths) * len(plan)
    for scenario_path in scenario_paths:
        scenario = load_scenario(scenario_path)
        for row in plan:
            cell_id = _cell_id(scenario.name, row["model"], row["method"], row["seed"])
            if cell_id in existing:
                continue
            delegate = provider_override or _make_provider(config, row["model"])
            budgeted = _BudgetedProvider(delegate, counter, effective_cap)
            provider: Any = budgeted
            if journal is not None:
                model = _model_config(config, row["model"])
                provider = JournaledProvider(
                    budgeted,
                    journal,
                    float(model["input_cny_per_million"]),
                    float(model["output_cny_per_million"]),
                )
            try:
                result = run_v2_episode(
                    scenario=scenario,
                    provider=provider,
                    memory=make_memory(
                        row["method"],
                        config.get("shiftmem_profile")
                        if row["method"] == "shiftmem"
                        else None,
                    ),
                    config=V2EpisodeConfig(
                        seed=row["seed"],
                        max_days=int(config["max_days"]),
                        review_interval=int(config["review_interval"]),
                        cooldown=int(config["cooldown"]),
                        episode_id=cell_id,
                    ),
                )
            except _BudgetStop as stop:
                raise RuntimeError(str(stop)) from None
            summary = _cell_summary(result, row, scenario.name)
            raw = {
                "cell_id": cell_id,
                "run_id": (run_metadata or {}).get("run_id"),
                "summary": summary,
                "scheduler_log": result["scheduler_log"],
                "review_logs": result["review_logs"],
                "daily_decision_log": result["daily_decision_log"],
                "reuse_attribution": result["reuse_attribution"],
                "environment_records": result["environment_records"],
            }
            if raw_output is not None:
                _append_jsonl(raw_output, raw)
            existing[cell_id] = raw
            cells.append(summary)
            report = _build_report(
                config, cells, counter, effective_cap, expected_cells, run_metadata, journal
            )
            if aggregate_output is not None:
                _write_report(aggregate_output, report)
            print(
                json.dumps(
                    {
                        "completed_cell": cell_id,
                        "completed_cells": len(cells),
                        "expected_cells": expected_cells,
                        "provider_calls": counter["calls"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
    return _build_report(
        config, cells, counter, effective_cap, expected_cells, run_metadata, journal
    )


def _build_report(
    config: dict[str, Any],
    cells: list[dict[str, Any]],
    counter: dict[str, int],
    effective_cap: int,
    expected_cells: int,
    run_metadata: dict[str, Any] | None,
    journal: JsonlRunJournal | None,
) -> dict[str, Any]:
    totals = journal.totals() if journal else None
    budgets = config.get("budgets", {})
    return {
        "protocol": "v2",
        "split": config["split"],
        "provider": config["provider"],
        "test_outcomes_accessed": False,
        "complete": len(cells) == expected_cells,
        "expected_cells": expected_cells,
        "completed_cells": len(cells),
        "cells": cells,
        "provider_calls": counter["calls"],
        "effective_call_cap": effective_cap,
        "estimated_cost_cny": round(
            counter["calls"] * float(budgets.get("cny_per_call", 0)), 4
        ),
        "journal_totals": totals,
        "total_reviews": sum(c["total_reviews"] for c in cells),
        "total_attempts": sum(c["attempt_count"] for c in cells),
        "total_input_tokens": sum(c["input_tokens"] for c in cells),
        "total_output_tokens": sum(c["output_tokens"] for c in cells),
        "total_latency_ms": sum(c["latency_ms"] for c in cells),
        "total_fallbacks": sum(c["fallback_count"] for c in cells),
        "total_parse_failures": sum(c["parse_failure_count"] for c in cells),
        "run_metadata": run_metadata or {},
    }


def _verify_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    for relative, expected in manifest["files"].items():
        if _sha256_file(Path(relative)) != expected:
            raise ValueError(f"freeze hash mismatch: {relative}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--scenario", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--freeze-manifest", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    config_bytes = args.config.read_bytes()
    config = yaml.safe_load(config_bytes)
    validate_pilot_config(config)
    _validate_scenario_paths(args.scenario, str(config["split"]))
    live = str(config["provider"]) not in _OFFLINE_PROVIDERS
    if live:
        required = (args.raw_output, args.journal, args.freeze_manifest, args.run_id)
        if any(value is None for value in required):
            raise ValueError(
                "live pilot requires raw output, journal, freeze manifest, and run ID"
            )
        git = _git_metadata()
        if git["git_dirty"]:
            raise ValueError("repository must be clean before live pilot")
        manifest = _verify_manifest(args.freeze_manifest)
        identity = RunIdentity(
            run_id=str(args.run_id),
            freeze_id=str(manifest["freeze_id"]),
            git_commit=str(git["git_revision"]),
            config_hash=hashlib.sha256(config_bytes).hexdigest(),
        )
        limits = BudgetLimits(
            max_calls=_effective_call_cap(config),
            max_input_tokens=int(config["budgets"]["max_input_tokens"]),
            max_output_tokens=int(config["budgets"]["max_output_tokens"]),
            max_cost_cny=float(config["budgets"]["max_cost_cny"]),
        )
        if not args.resume:
            for path in (args.output, args.raw_output, args.journal):
                if path.exists():
                    raise FileExistsError(f"output already exists: {path}")
        journal = JsonlRunJournal(args.journal, identity, limits)
        metadata = {
            "run_id": args.run_id,
            "freeze_id": manifest["freeze_id"],
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            **git,
            **_runtime_metadata(config, args.scenario),
        }
    else:
        journal = None
        metadata = {
            "run_id": args.run_id or "offline-v2-pilot",
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            **_git_metadata(),
            **_runtime_metadata(config, args.scenario),
        }
    report = run_pilot(
        config,
        args.scenario,
        journal=journal,
        raw_output=args.raw_output,
        aggregate_output=args.output,
        run_metadata=metadata,
        resume=args.resume,
    )
    _write_report(args.output, report)
    print(json.dumps({k: v for k, v in report.items() if k != "cells"}, sort_keys=True))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
