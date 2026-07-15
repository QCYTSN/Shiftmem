"""Validate and dry-run the freeze-bound formal experiment matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import yaml

from shiftmem.control.controller import StrategyParameters
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.formal_v2 import (
    aggregate_results,
    append_completed_cell,
    execute_offline_cell,
    load_completed_cells,
    run_oracle_episode,
)
from shiftmem.evaluation.splits import load_split_manifest
from shiftmem.memory.store import make_memory

try:
    from scripts.verify_freeze import verify_freeze
except ModuleNotFoundError:
    from verify_freeze import verify_freeze


FORMAL_METHODS = {"none", "full_history", "summary", "vector", "time_decay", "shiftmem"}

V2_PRIMARY_METHODS = {"vector", "shiftmem"}
V2_SECONDARY_METHODS = {"none", "full_history", "summary", "time_decay"}


def _reject_test_scenarios(scenario_ids: list[str]) -> None:
    prohibited = [
        name for name in scenario_ids if name.lower().startswith(("test-id", "test-ood"))
    ]
    if prohibited:
        raise ValueError(
            f"Test-ID/Test-OOD scenarios are prohibited in dry-run: {prohibited}"
        )


def _hash_cell(identity: dict[str, Any]) -> str:
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()[:20]


def validate_v2_config(config: dict[str, Any]) -> None:
    """Validate the v2 hierarchical primary/secondary matrix shape."""

    if config.get("protocol") != "v2":
        raise ValueError("config protocol must be v2")
    primary = {str(row["config_id"]) for row in config.get("primary_methods", [])}
    if primary != V2_PRIMARY_METHODS:
        raise ValueError("v2 primary tier must be exactly VectorMemory and ShiftMem")
    secondary = {str(row["config_id"]) for row in config.get("secondary_methods", [])}
    if secondary != V2_SECONDARY_METHODS:
        raise ValueError("v2 secondary tier must be the four remaining baselines")
    if len(config.get("models", [])) != 2:
        raise ValueError("v2 matrix requires exactly two core models")
    if int(config.get("primary_seeds", 0)) < 1:
        raise ValueError("v2 primary tier requires positive seed count")
    profile = config.get("shiftmem_profile")
    if not profile:
        raise ValueError("v2 matrix requires an explicit ShiftMem runtime profile")
    make_memory("shiftmem", profile)
    controller = config.get("controller_profile", {})
    defaults = controller.get("defaults")
    bounds = controller.get("bounds")
    max_review_deltas = controller.get("max_review_deltas")
    expected_bounds = {
        key: list(value) for key, value in StrategyParameters.bounds().items()
    }
    if (
        defaults != StrategyParameters().model_dump()
        or bounds != expected_bounds
        or max_review_deltas != StrategyParameters.max_review_deltas()
    ):
        raise ValueError("v2 controller profile must match the frozen implementation")
    if int(config.get("review_interval", 0)) < 1 or int(config.get("cooldown", -1)) < 0:
        raise ValueError("v2 scheduler profile is incomplete")


def build_v2_cell_plan(
    config: dict[str, Any],
    scenario_ids: list[str],
    seeds: list[int],
    tier: str,
) -> list[dict[str, Any]]:
    validate_v2_config(config)
    _reject_test_scenarios(scenario_ids)
    if tier == "primary":
        methods = config["primary_methods"]
        models = [str(model["label"]) for model in config["models"]]
    elif tier == "secondary":
        methods = config["secondary_methods"]
        models = [str(config["secondary_model"])]
    else:
        raise ValueError(f"unknown tier: {tier}")

    rows: list[dict[str, Any]] = []
    for scenario_id in sorted(scenario_ids):
        for seed in sorted(seeds):
            for model in models:
                for method in methods:
                    identity = {
                        "tier": tier,
                        "scenario_id": scenario_id,
                        "seed": int(seed),
                        "model": model,
                        "method": str(method["config_id"]),
                    }
                    rows.append({**identity, "cell_id": _hash_cell(identity)})
    return rows


def validate_formal_config(config: dict[str, Any]) -> None:
    methods = {str(row["config_id"]) for row in config.get("methods", [])}
    if methods != FORMAL_METHODS or len(config.get("methods", [])) != 6:
        raise ValueError("formal matrix must contain exactly the six methods")
    if len(config.get("models", [])) != 2:
        raise ValueError("formal matrix requires exactly two core models")
    if int(config.get("seeds_per_cell", 0)) < 5:
        raise ValueError("formal matrix requires at least five seeds per cell")


def validate_live_dry_run_config(config: dict[str, Any]) -> None:
    validate_formal_config(config)
    if config.get("budget_approved") is not True:
        raise ValueError("live API budget is not approved")
    if float(config["budgets"].get("max_cost_cny", 0)) > 30:
        raise ValueError("live dry-run exceeds the approved 30 CNY cap")


def build_cell_plan(
    config: dict[str, Any], scenario_ids: list[str], seeds: list[int]
) -> list[dict[str, Any]]:
    validate_formal_config(config)
    prohibited = [name for name in scenario_ids if name.lower().startswith(("test-id", "test-ood"))]
    if prohibited:
        raise ValueError(f"Test-ID/Test-OOD scenarios are prohibited in dry-run: {prohibited}")
    rows: list[dict[str, Any]] = []
    for scenario_id in sorted(scenario_ids):
        for seed in sorted(seeds):
            for model in config["models"]:
                for method in config["methods"]:
                    identity = {
                        "scenario_id": scenario_id,
                        "seed": int(seed),
                        "model": str(model["label"]),
                        "method": str(method["config_id"]),
                    }
                    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
                    rows.append({**identity, "cell_id": hashlib.sha256(encoded.encode()).hexdigest()[:20]})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--freeze-dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cells-output", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--execute-offline", action="store_true")
    args = parser.parse_args()
    if args.dry_run and args.execute_offline:
        raise ValueError("choose either --dry-run or --execute-offline")
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if config.get("protocol") == "v2":
        return _main_v2(args, config)
    validate_formal_config(config)
    if args.freeze_dir is None:
        raise ValueError("v1 dry-run requires --freeze-dir")
    freeze_errors = verify_freeze(args.freeze_dir)
    if freeze_errors:
        raise ValueError(f"freeze verification failed: {freeze_errors}")
    manifest = load_split_manifest(args.manifest)
    if manifest.split not in {"Development", "Validation"}:
        raise ValueError(f"{manifest.split} manifests are prohibited before replacement freeze")
    seeds = manifest.seeds[: int(config["seeds_per_cell"])]
    plan = build_cell_plan(config, [row.id for row in manifest.scenarios], seeds)
    estimated_calls = len(plan) * int(config["post_shift_days"])
    if estimated_calls > int(config["budgets"]["max_calls"]):
        raise ValueError("planned decisions exceed max_calls")
    if not args.dry_run:
        if not config.get("budget_approved"):
            raise ValueError("live API budget is not approved")
        raise ValueError("live execution remains disabled until replacement freeze")
    result = {
        "dry_run": True,
        "provider_calls": 0,
        "test_outcomes_accessed": False,
        "freeze_id": args.freeze_dir.name,
        "manifest_split": manifest.split,
        "cells": len(plan),
        "estimated_decisions": estimated_calls,
        "cell_plan_hash": hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


def _main_v2(args: argparse.Namespace, config: dict[str, Any]) -> int:
    validate_v2_config(config)
    manifest = load_split_manifest(args.manifest)
    if manifest.split not in {"Development", "Validation"}:
        raise ValueError(
            f"{manifest.split} manifests are prohibited before replacement freeze"
        )
    freeze_id = "pre-freeze-offline-rehearsal"
    if args.freeze_dir is not None:
        freeze_errors = verify_freeze(args.freeze_dir)
        if freeze_errors:
            raise ValueError(f"freeze verification failed: {freeze_errors}")
        freeze_id = args.freeze_dir.name

    scenario_ids = [row.id for row in manifest.scenarios]
    primary_seeds = manifest.seeds[: int(config["primary_seeds"])]
    secondary_seeds = manifest.seeds[: int(config["secondary_seeds"])]
    plan = build_v2_cell_plan(config, scenario_ids, primary_seeds, "primary")
    plan += build_v2_cell_plan(config, scenario_ids, secondary_seeds, "secondary")
    scenarios = {entry.id: load_scenario(entry.path) for entry in manifest.scenarios}
    estimated_reviews = sum(
        math.ceil(scenarios[row["scenario_id"]].episode_length / int(config["review_interval"]))
        for row in plan
    )
    plan_hash = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    base = {
        "protocol": "v2",
        "freeze_id": freeze_id,
        "manifest_split": manifest.split,
        "test_outcomes_accessed": False,
        "cells": len(plan),
        "estimated_periodic_reviews": estimated_reviews,
        "cell_plan_hash": plan_hash,
    }
    if args.dry_run:
        result = {**base, "dry_run": True, "provider_calls": 0}
        _write_json(args.output, result)
        print(json.dumps(result, sort_keys=True))
        return 0
    if not args.execute_offline:
        if config.get("budget_approved") is not True:
            raise ValueError("live API budget is not approved")
        raise ValueError("live execution remains disabled until replacement freeze")

    raw_path = args.cells_output or args.output.with_name(
        f"{args.output.stem}_cells.jsonl"
    )
    completed = load_completed_cells(raw_path)
    expected_ids = {row["cell_id"] for row in plan}
    unexpected = sorted(set(completed) - expected_ids)
    if unexpected:
        raise ValueError(f"resume file contains cells outside this plan: {unexpected}")
    oracle_cache: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in plan:
        if row["cell_id"] in completed:
            continue
        key = (str(row["scenario_id"]), int(row["seed"]))
        if key not in oracle_cache:
            oracle_cache[key] = run_oracle_episode(scenarios[key[0]], key[1])
        oracle = oracle_cache[key]
        cell = execute_offline_cell(row, scenarios[key[0]], config, oracle)
        append_completed_cell(raw_path, cell)
        completed[cell.cell_id] = cell
    ordered = [completed[row["cell_id"]] for row in plan]
    result = {
        **base,
        **aggregate_results(plan, ordered),
        "dry_run": False,
        "offline_integration_only": True,
        "raw_cells": str(raw_path),
    }
    _write_json(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
