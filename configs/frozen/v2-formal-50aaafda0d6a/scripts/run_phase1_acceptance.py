"""Run and gate the network-free 100-seed Phase 1 acceptance matrix."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Callable

import yaml

try:
    from scripts.run_experiment import run_matrix
except ModuleNotFoundError:  # Support direct execution from the scripts directory.
    from run_experiment import run_matrix


@dataclass(frozen=True)
class AcceptanceSummary:
    expected_runs: int
    completed_runs: int
    passed: bool
    gates: dict[str, bool]
    oracle_random_mean_costs: dict[str, dict[str, float]] = field(default_factory=dict)
    failures: dict[str, list[str]] = field(default_factory=dict)


def load_acceptance_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    required = {
        "name", "split", "seeds", "scenarios", "policies", "expected_horizon"
    }
    if set(config) != required:
        raise ValueError(f"acceptance config must contain exactly {sorted(required)}")
    if config["split"] != "development":
        raise ValueError("Phase 1 acceptance is restricted to development")
    return config


def execute_acceptance(
    config: dict[str, Any], runner: Callable[[dict[str, Any]], list[dict[str, Any]]]
) -> AcceptanceSummary:
    runs = runner(config)
    policies = [item["name"] for item in config["policies"]]
    expected_keys = {
        (str(scenario), int(seed), policy)
        for scenario in config["scenarios"]
        for seed in config["seeds"]
        for policy in policies
    }
    actual_keys = [
        (str(run["scenario"]), int(run["seed"]), str(run["policy"]))
        for run in runs
    ]
    # Production runs use scenario names rather than paths, so cardinality and
    # uniqueness are the invariant shared with fake runners.
    expected_runs = len(expected_keys)
    complete = len(runs) == expected_runs and len(set(actual_keys)) == expected_runs

    nonfinite: list[str] = []
    wrong_horizon: list[str] = []
    for run in runs:
        label = _label(run)
        if not all(
            isinstance(value, (int, float)) and math.isfinite(float(value))
            for value in run.get("metrics", {}).values()
        ):
            nonfinite.append(label)
        if int(run.get("metrics", {}).get("days", -1)) != int(config["expected_horizon"]):
            wrong_horizon.append(label)

    grouped: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for run in runs:
        grouped.setdefault((str(run["scenario"]), int(run["seed"])), []).append(run)
    unpaired: list[str] = []
    for key, group in grouped.items():
        trajectories = {
            tuple(int(record["demand"]) for record in run.get("records", []))
            for run in group
        }
        if len(trajectories) != 1 or len(group) != len(policies):
            unpaired.append(f"{key[0]}:{key[1]}")

    marker_failures: list[str] = []
    by_scenario: dict[str, set[int | None]] = {}
    for run in runs:
        marker = run.get("shift_day")
        by_scenario.setdefault(str(run["scenario"]), set()).add(marker)
        if marker is not None and (
            not isinstance(marker, int) or marker <= 0 or marker >= config["expected_horizon"]
        ):
            marker_failures.append(_label(run))
    for scenario, markers in by_scenario.items():
        if len(markers) != 1:
            marker_failures.append(scenario)

    cost_summary: dict[str, dict[str, float]] = {}
    oracle_failures: list[str] = []
    scenarios = sorted({str(run["scenario"]) for run in runs})
    for scenario in scenarios:
        values: dict[str, list[float]] = {"oracle": [], "random": []}
        for run in runs:
            if run["scenario"] == scenario and run["policy"] in values:
                values[run["policy"]].append(float(run["metrics"]["total_cost"]))
        if not values["oracle"] or not values["random"]:
            oracle_failures.append(scenario)
            continue
        cost_summary[scenario] = {name: mean(costs) for name, costs in values.items()}
        if cost_summary[scenario]["oracle"] >= cost_summary[scenario]["random"]:
            oracle_failures.append(scenario)

    failures = {
        "finite_metrics": nonfinite,
        "expected_horizon": wrong_horizon,
        "paired_demand": unpaired,
        "oracle_beats_random": oracle_failures,
        "valid_shift_markers": marker_failures,
    }
    gates = {
        "complete_matrix": complete,
        **{name: not entries for name, entries in failures.items()},
    }
    return AcceptanceSummary(
        expected_runs=expected_runs,
        completed_runs=len(runs),
        passed=all(gates.values()),
        gates=gates,
        oracle_random_mean_costs=cost_summary,
        failures={name: entries[:20] for name, entries in failures.items() if entries},
    )


def run_resumable(config: dict[str, Any], cache: Path) -> list[dict[str, Any]]:
    cached: dict[tuple[str, int, str], dict[str, Any]] = {}
    if cache.exists():
        for line in cache.read_text(encoding="utf-8").splitlines():
            if line.strip():
                run = json.loads(line)
                cached[(run["scenario"], int(run["seed"]), run["policy"])] = run
    cache.parent.mkdir(parents=True, exist_ok=True)
    scenario_names: dict[str, str] = {}
    for scenario_path in config["scenarios"]:
        scenario_doc = yaml.safe_load(Path(scenario_path).read_text(encoding="utf-8"))
        scenario_names[scenario_path] = scenario_doc["name"]
    with cache.open("a", encoding="utf-8") as stream:
        for scenario_path in config["scenarios"]:
            for seed in config["seeds"]:
                keys = [
                    (scenario_names[scenario_path], int(seed), policy["name"])
                    for policy in config["policies"]
                ]
                if all(key in cached for key in keys):
                    continue
                subconfig = {
                    "name": config["name"],
                    "split": config["split"],
                    "seeds": [seed],
                    "scenarios": [scenario_path],
                    "policies": config["policies"],
                }
                for run in run_matrix(subconfig):
                    key = (run["scenario"], int(run["seed"]), run["policy"])
                    if key not in cached:
                        cached[key] = run
                        stream.write(json.dumps(run, ensure_ascii=False, sort_keys=True) + "\n")
                        stream.flush()
    return list(cached.values())


def _label(run: dict[str, Any]) -> str:
    return f"{run.get('scenario')}:{run.get('seed')}:{run.get('policy')}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--cache", type=Path, default=Path("artifacts/raw_runs/phase1_acceptance.jsonl")
    )
    args = parser.parse_args()
    config = load_acceptance_config(args.config)
    summary = execute_acceptance(config, lambda current: run_resumable(current, args.cache))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(asdict(summary), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"passed": summary.passed, "runs": summary.completed_runs}))
    return 0 if summary.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
