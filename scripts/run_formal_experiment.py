"""Validate and dry-run the freeze-bound formal experiment matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import subprocess
from typing import Any

import yaml

from shiftmem.control.controller import StrategyParameters
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.formal_v2 import (
    aggregate_results,
    append_completed_cell,
    execute_cell,
    execute_offline_cell,
    load_completed_cells,
    run_oracle_episode,
)
from shiftmem.evaluation.splits import load_split_manifest
from shiftmem.memory.store import make_memory
from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, RunIdentity
from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig
from shiftmem.providers.inventory_prompt import (
    STRATEGY_REVIEW_SYSTEM_PROMPT,
    build_strategy_review_user_message,
)
from shiftmem.providers.journaled import JournaledProvider

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
    if int(config.get("secondary_seeds", -1)) < 0:
        raise ValueError("v2 secondary seed count must be non-negative")
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


def validate_v2_live_gate_config(config: dict[str, Any]) -> None:
    """Require every frozen field needed for fail-closed formal spending."""

    validate_v2_config(config)
    if config.get("budget_approved") is not True:
        raise ValueError("formal live API budget is not approved")
    budgets = config.get("budgets", {})
    required_budgets = {
        "max_calls",
        "max_input_tokens",
        "max_output_tokens",
        "max_cost_cny",
        "max_successful_cost_cny",
    }
    if not required_budgets.issubset(budgets) or any(
        float(budgets[field]) <= 0 for field in required_budgets
    ):
        raise ValueError("formal live budget limits must be complete and positive")
    required_model = {
        "label",
        "provider",
        "model_name",
        "input_cny_per_million",
        "output_cny_per_million",
        "max_output_tokens_per_call",
        "max_billed_output_tokens_per_call",
    }
    for model in config["models"]:
        if not required_model.issubset(model):
            raise ValueError("formal live model pricing and output cap are incomplete")
        if (
            float(model["input_cny_per_million"]) < 0
            or float(model["output_cny_per_million"]) < 0
            or int(model["max_output_tokens_per_call"]) < 1
            or int(model["max_billed_output_tokens_per_call"])
            < int(model["max_output_tokens_per_call"])
        ):
            raise ValueError("formal live model rates or output cap are invalid")


def verify_config_bound_to_freeze(
    config_path: Path,
    config_bytes: bytes,
    freeze_dir: Path,
    *,
    workspace_root: Path | None = None,
) -> None:
    root = (workspace_root or Path.cwd()).resolve()
    try:
        relative = config_path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError("formal config must be inside the workspace") from error
    frozen_config = freeze_dir / relative
    if not frozen_config.is_file():
        raise ValueError(f"formal config is not present in freeze: {relative}")
    if frozen_config.read_bytes() != config_bytes:
        raise ValueError("formal config bytes do not match the verified freeze")


def verify_file_bound_to_freeze(
    path: Path,
    freeze_dir: Path,
    *,
    workspace_root: Path | None = None,
) -> None:
    """Require a live-run input to match its byte-identical frozen copy."""

    root = (workspace_root or Path.cwd()).resolve()
    try:
        relative = path.resolve().relative_to(root)
    except ValueError as error:
        raise ValueError("formal input must be inside the workspace") from error
    frozen_path = freeze_dir / relative
    if not frozen_path.is_file():
        raise ValueError(f"formal input is not present in freeze: {relative}")
    if frozen_path.read_bytes() != path.read_bytes():
        raise ValueError(f"formal input bytes do not match the verified freeze: {relative}")


def select_prior_sources(
    config: dict[str, Any], manifest_split: str
) -> list[dict[str, Any]]:
    """Return exactly the frozen continuation sources for one split."""

    continuation = config.get("continuation_from") or {}
    sources = continuation.get("prior_sources") or []
    selected = [
        source
        for source in sources
        if source.get("manifest_split") == manifest_split
    ]
    hashes = [str(source.get("sha256", "")) for source in selected]
    if any(len(digest) != 64 for digest in hashes):
        raise ValueError("frozen prior cell source hash is invalid")
    if len(set(hashes)) != len(hashes):
        raise ValueError("frozen prior cell sources contain duplicate hashes")
    return selected


def validate_v2_split_access(
    split: str, *, execute_live: bool, freeze_verified: bool
) -> None:
    """Allow held-out splits only for a live run bound to a verified freeze."""

    if split in {"Test-ID", "Test-OOD"} and not (
        execute_live and freeze_verified
    ):
        raise ValueError(
            f"{split} requires live execution with a verified replacement freeze"
        )


def build_v2_cell_plan(
    config: dict[str, Any],
    scenario_ids: list[str],
    seeds: list[int],
    tier: str,
    *,
    allow_held_out: bool = False,
) -> list[dict[str, Any]]:
    validate_v2_config(config)
    if not allow_held_out:
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
    parser.add_argument("--execute-live", action="store_true")
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--prior-cells", type=Path, action="append")
    args = parser.parse_args()
    if sum((args.dry_run, args.execute_offline, args.execute_live)) > 1:
        raise ValueError("choose one execution mode")
    config_bytes = args.config.read_bytes()
    config = yaml.safe_load(config_bytes)
    if config.get("protocol") == "v2":
        return _main_v2(args, config, config_bytes)
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


def _main_v2(
    args: argparse.Namespace, config: dict[str, Any], config_bytes: bytes
) -> int:
    validate_v2_config(config)
    manifest = load_split_manifest(args.manifest)
    freeze_id = "pre-freeze-offline-rehearsal"
    freeze_verified = False
    if args.freeze_dir is not None:
        freeze_errors = verify_freeze(args.freeze_dir)
        if freeze_errors:
            raise ValueError(f"freeze verification failed: {freeze_errors}")
        freeze_id = args.freeze_dir.name
        freeze_verified = True
    validate_v2_split_access(
        manifest.split,
        execute_live=bool(args.execute_live),
        freeze_verified=freeze_verified,
    )

    if args.execute_live:
        validate_v2_live_gate_config(config)
        if args.freeze_dir is None or args.journal is None or not args.run_id:
            raise ValueError(
                "formal live execution requires freeze-dir, journal, and run-id"
            )
        verify_config_bound_to_freeze(args.config, config_bytes, args.freeze_dir)
        verify_file_bound_to_freeze(args.manifest, args.freeze_dir)
        for entry in manifest.scenarios:
            verify_file_bound_to_freeze(entry.path, args.freeze_dir)

    scenario_ids = [row.id for row in manifest.scenarios]
    primary_seeds = manifest.seeds[: int(config["primary_seeds"])]
    secondary_seeds = manifest.seeds[: int(config["secondary_seeds"])]
    allow_held_out = manifest.split in {"Test-ID", "Test-OOD"}
    plan = build_v2_cell_plan(
        config,
        scenario_ids,
        primary_seeds,
        "primary",
        allow_held_out=allow_held_out,
    )
    plan += build_v2_cell_plan(
        config,
        scenario_ids,
        secondary_seeds,
        "secondary",
        allow_held_out=allow_held_out,
    )
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
    if not args.execute_offline and not args.execute_live:
        if config.get("budget_approved") is not True:
            raise ValueError("live API budget is not approved")
        raise ValueError("live execution remains disabled until replacement freeze")

    journal: JsonlRunJournal | None = None
    if args.execute_live:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        if status.strip():
            raise ValueError("repository must be clean before formal live execution")
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        identity = RunIdentity(
            run_id=str(args.run_id),
            freeze_id=freeze_id,
            git_commit=commit,
            config_hash=hashlib.sha256(config_bytes).hexdigest(),
        )
        journal = JsonlRunJournal(
            args.journal, identity, BudgetLimits(**config["budgets"])
        )

    raw_path = args.cells_output or args.output.with_name(
        f"{args.output.stem}_cells.jsonl"
    )
    completed = load_completed_cells(raw_path)
    prior: dict[str, Any] = {}
    continuation = config.get("continuation_from") or {}
    all_declared_sources = continuation.get("prior_sources") or []
    declared_sources = select_prior_sources(config, manifest.split)
    if args.prior_cells or declared_sources:
        if not args.execute_live:
            raise ValueError("prior cells are allowed only for formal live continuation")
        if not all_declared_sources:
            raise ValueError("formal config does not declare a prior continuation")
        declared_by_hash = {source["sha256"]: source for source in declared_sources}
        for prior_path in args.prior_cells or []:
            digest = hashlib.sha256(prior_path.read_bytes()).hexdigest()
            source = declared_by_hash.get(digest)
            if source is None:
                raise ValueError("prior cells hash does not match frozen continuation")
            if manifest.split != source.get("manifest_split"):
                raise ValueError("prior cells do not belong to this manifest split")
            loaded = load_completed_cells(prior_path)
            if len(loaded) != int(source.get("completed_cells", -1)):
                raise ValueError("prior completed cell count does not match continuation")
            if any(
                cell.run_identity != source.get("run_identity")
                for cell in loaded.values()
            ):
                raise ValueError("prior cells do not match declared run identity")
            overlap = set(prior) & set(loaded)
            if overlap:
                raise ValueError(f"prior sources contain duplicate cells: {sorted(overlap)}")
            prior.update(loaded)
        if len(args.prior_cells or []) != len(declared_sources):
            raise ValueError(
                "all frozen prior cell sources for this manifest are required"
            )
    if args.execute_live and not args.resume:
        existing_paths = [path for path in (raw_path, args.output, args.journal) if path and path.exists()]
        if existing_paths:
            raise FileExistsError(f"formal live outputs already exist: {existing_paths}")
    expected_ids = {row["cell_id"] for row in plan}
    unexpected = sorted((set(completed) | set(prior)) - expected_ids)
    if unexpected:
        raise ValueError(f"resume file contains cells outside this plan: {unexpected}")
    if journal is not None:
        expected_identity = journal.identity.model_dump(mode="json")
        mismatched_identity = sorted(
            cell_id
            for cell_id, cell in completed.items()
            if cell.run_identity != expected_identity
        )
        if mismatched_identity:
            raise ValueError(
                "completed cells do not match formal run identity: "
                f"{mismatched_identity}"
            )
    overlap = sorted(set(completed) & set(prior))
    if overlap:
        raise ValueError(f"continuation outputs duplicate prior cells: {overlap}")
    all_completed = {**prior, **completed}
    oracle_cache: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for row in plan:
        if row["cell_id"] in all_completed:
            continue
        key = (str(row["scenario_id"]), int(row["seed"]))
        if key not in oracle_cache:
            oracle_cache[key] = run_oracle_episode(scenarios[key[0]], key[1])
        oracle = oracle_cache[key]
        if journal is None:
            cell = execute_offline_cell(row, scenarios[key[0]], config, oracle)
        else:
            provider = _make_formal_live_provider(config, row["model"], journal)
            cell = execute_cell(
                row,
                scenarios[key[0]],
                config,
                oracle,
                provider=provider,
                run_identity=journal.identity.model_dump(mode="json"),
                test_outcomes_accessed=manifest.split in {"Test-ID", "Test-OOD"},
            )
        append_completed_cell(raw_path, cell)
        completed[cell.cell_id] = cell
        all_completed[cell.cell_id] = cell
    ordered = [all_completed[row["cell_id"]] for row in plan]
    result = {
        **base,
        **aggregate_results(
            plan,
            ordered,
            journal_totals=journal.totals() if journal is not None else None,
            test_outcomes_accessed=manifest.split in {"Test-ID", "Test-OOD"},
        ),
        "dry_run": False,
        "offline_integration_only": journal is None,
        "raw_cells": str(raw_path),
        "prior_cells": [str(path) for path in args.prior_cells] if args.prior_cells else [],
    }
    _write_json(args.output, result)
    print(json.dumps(result, sort_keys=True))
    return 0


def _make_formal_live_provider(
    config: dict[str, Any], model_label: str, journal: JsonlRunJournal
) -> JournaledProvider:
    model = next(
        (row for row in config["models"] if str(row["label"]) == model_label),
        None,
    )
    if model is None:
        raise ValueError(f"unknown formal model: {model_label}")
    provider_config = ProviderConfig.from_env(
        str(model["provider"]), model_override=str(model["model_name"])
    ).model_copy(
        update={"max_tokens": int(model["max_output_tokens_per_call"])}
    )
    delegate = CompatibleAPIProvider(
        provider_config,
        system_prompt=STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_user_message=build_strategy_review_user_message,
    )
    return JournaledProvider(
        delegate,
        journal,
        float(model["input_cny_per_million"]),
        float(model["output_cny_per_million"]),
        require_preflight_reservation=True,
        output_token_reservation_per_call=int(
            model["max_billed_output_tokens_per_call"]
        ),
    )


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    raise SystemExit(main())
