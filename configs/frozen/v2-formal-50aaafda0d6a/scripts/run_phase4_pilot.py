"""Run the bounded two-core, two-method Phase 4 Validation Pilot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean, stdev
from typing import Any

import yaml

try:
    from scripts.run_validation_retrieval import run_one
    from scripts.select_validation_config import ensure_selection_paths
except ModuleNotFoundError:
    from run_validation_retrieval import run_one
    from select_validation_config import ensure_selection_paths


def estimate_pilot_calls(config: dict[str, Any]) -> int:
    return (
        len(config["seeds"])
        * len(config["models"])
        * len(config["methods"])
        * int(config["post_shift_days"])
    )


def deduplicate_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the first completed cell to prevent post-hoc outcome selection."""

    unique: dict[tuple[str, str, int], dict[str, Any]] = {}
    for run in runs:
        key = (str(run["model"]), str(run["config_id"]), int(run["seed"]))
        unique.setdefault(key, run)
    return list(unique.values())


def aggregate_pilot(runs: list[dict[str, Any]], expected_runs: int) -> dict[str, Any]:
    required = {"model", "config_id", "seed", "cost", "tokens", "fallbacks", "latency_ms", "calls"}
    metric_completeness = all(required.issubset(run) for run in runs)
    baselines = {
        (str(run["model"]), int(run["seed"])): float(run["cost"])
        for run in runs
        if run.get("config_id") == "vector"
    }
    models = []
    for model in sorted({str(run["model"]) for run in runs}):
        shift_runs = [
            run for run in runs
            if run.get("model") == model and run.get("config_id") == "shiftmem"
        ]
        regrets = [
            float(run["cost"]) - baselines[(model, int(run["seed"]))]
            for run in shift_runs
            if (model, int(run["seed"])) in baselines
        ]
        if regrets:
            models.append(
                {
                    "model": model,
                    "paired_seeds": len(regrets),
                    "mean_regret": mean(regrets),
                    "regret_sd": stdev(regrets) if len(regrets) > 1 else 0.0,
                }
            )
    return {
        "expected_runs": expected_runs,
        "completed_runs": len(runs),
        "complete": len(runs) == expected_runs and metric_completeness,
        "metric_completeness": metric_completeness,
        "total_tokens": sum(int(run.get("tokens", 0)) for run in runs),
        "total_calls": sum(int(run.get("calls", 0)) for run in runs),
        "total_fallbacks": sum(int(run.get("fallbacks", 0)) for run in runs),
        "total_latency_ms": sum(float(run.get("latency_ms", 0)) for run in runs),
        "models": models,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--aggregate-output", type=Path, required=True)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    ensure_selection_paths([Path(path) for path in config["manifests"].values()])
    if estimate_pilot_calls(config) > int(config["max_calls"]):
        raise ValueError("Phase 4 Pilot exceeds max_calls")
    existing: dict[tuple[str, str, int], dict[str, Any]] = {}
    if args.raw_output.exists():
        for line in args.raw_output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                existing.setdefault(
                    (row["model"], row["config_id"], int(row["seed"])), row
                )
    args.raw_output.parent.mkdir(parents=True, exist_ok=True)
    with args.raw_output.open("a", encoding="utf-8") as stream:
        for model in config["models"]:
            for method in config["methods"]:
                for seed in config["seeds"]:
                    key = (model["label"], method["config_id"], int(seed))
                    if key in existing:
                        continue
                    row = run_one(
                        Path(config["scenario"]), int(seed), int(config["post_shift_days"]),
                        method, model["profile"], model["model_id"],
                    )
                    row["model"] = model["label"]
                    row["model_id"] = model["model_id"]
                    existing[key] = row
                    stream.write(json.dumps(row, sort_keys=True) + "\n")
                    stream.flush()
                    print(json.dumps({"completed": key, "fallbacks": row["fallbacks"]}), flush=True)
    expected_runs = len(config["seeds"]) * len(config["models"]) * len(config["methods"])
    aggregate = aggregate_pilot(list(existing.values()), expected_runs)
    aggregate["estimated_calls"] = estimate_pilot_calls(config)
    aggregate["test_outcomes_accessed"] = False
    aggregate["operational_notes"] = config.get("operational_notes", [])
    args.aggregate_output.parent.mkdir(parents=True, exist_ok=True)
    args.aggregate_output.write_text(json.dumps(aggregate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"complete": aggregate["complete"], "runs": aggregate["completed_runs"]}), flush=True)
    return 0 if aggregate["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
