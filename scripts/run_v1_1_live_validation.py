"""Run the approved CNY-capped, journaled v1.1 Validation dry-run."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

import yaml

from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, RunIdentity
from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig
from shiftmem.providers.journaled import JournaledProvider

try:
    from scripts.run_formal_experiment import validate_live_dry_run_config
    from scripts.run_validation_retrieval import run_one
    from scripts.verify_freeze import verify_freeze
except ModuleNotFoundError:
    from run_formal_experiment import validate_live_dry_run_config
    from run_validation_retrieval import run_one
    from verify_freeze import verify_freeze


def _cell_id(model: str, method: str, seed: int) -> str:
    value = f"validation-demand-jump|{model}|{method}|{seed}"
    return hashlib.sha256(value.encode()).hexdigest()[:20]


def _write_aggregate(path: Path, runs: list[dict[str, Any]], journal: JsonlRunJournal, expected: int) -> None:
    totals = journal.totals()
    result = {
        "complete": len(runs) == expected,
        "expected_cells": expected,
        "completed_cells": len(runs),
        "provider_calls": totals["calls"],
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "estimated_cost_cny": totals["cost_cny"],
        "test_outcomes_accessed": False,
        "runs": runs,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--freeze-dir", type=Path, required=True)
    parser.add_argument("--journal", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--aggregate-output", type=Path, required=True)
    args = parser.parse_args()
    if subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True).stdout.strip():
        raise ValueError("repository must be clean before live dry-run")
    config_bytes = args.config.read_bytes()
    config = yaml.safe_load(config_bytes)
    validate_live_dry_run_config(config)
    errors = verify_freeze(args.freeze_dir)
    if errors:
        raise ValueError(f"freeze verification failed: {errors}")
    scenario = Path(config["scenario"])
    if "validation" not in scenario.name.lower() or "test" in scenario.name.lower():
        raise ValueError("live dry-run scenario must be Validation-only")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    identity = RunIdentity(
        run_id="protocol-v1.1-live-validation",
        freeze_id=args.freeze_dir.name,
        git_commit=commit,
        config_hash=hashlib.sha256(config_bytes).hexdigest(),
    )
    journal = JsonlRunJournal(args.journal, identity, BudgetLimits(**config["budgets"]))
    existing: dict[str, dict[str, Any]] = {}
    if args.raw_output.exists():
        for line in args.raw_output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                existing[str(row["cell_id"])] = row
    expected = len(config["models"]) * len(config["methods"]) * len(config["live_seeds"])
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    with args.raw_output.open("a", encoding="utf-8") as stream:
        for model in config["models"]:
            for method in config["methods"]:
                for seed in config["live_seeds"]:
                    cell_id = _cell_id(model["label"], method["config_id"], int(seed))
                    if cell_id in existing:
                        continue
                    delegate = CompatibleAPIProvider(ProviderConfig.from_env(model["profile"], model_override=model["model_id"]))
                    provider = JournaledProvider(delegate, journal, model["input_cny_per_million"], model["output_cny_per_million"])
                    row = run_one(scenario, int(seed), int(config["post_shift_days"]), method, model["profile"], model["model_id"], provider=provider, cell_id=cell_id)
                    row.update({"cell_id": cell_id, "model": model["label"], "model_id": model["model_id"]})
                    existing[cell_id] = row
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
                    stream.flush()
                    _write_aggregate(args.aggregate_output, list(existing.values()), journal, expected)
                    print(json.dumps({"completed": cell_id, "model": model["label"], "method": method["config_id"], "cost_cny": journal.totals()["cost_cny"]}), flush=True)
    _write_aggregate(args.aggregate_output, list(existing.values()), journal, expected)
    return 0 if len(existing) == expected else 1


if __name__ == "__main__":
    raise SystemExit(main())
