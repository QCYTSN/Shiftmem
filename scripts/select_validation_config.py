"""Select detector and retrieval settings using Development/Validation only."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from shiftmem.agents.classical import FixedOrderPolicy
from shiftmem.detection import ADWINDetector, PageHinkleyDetector
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import load_scenario
from shiftmem.evaluation.splits import load_split_manifest

try:
    from scripts.run_episode import derive_seeds
except ModuleNotFoundError:
    from run_episode import derive_seeds


def ensure_selection_paths(paths: list[Path]) -> None:
    for path in paths:
        lowered = path.name.lower().replace("_", "-")
        if "test-id" in lowered or "test-ood" in lowered:
            label = "Test-ID" if "test-id" in lowered else "Test-OOD"
            raise ValueError(f"{label} manifests are prohibited during selection")
        if path.exists():
            split = load_split_manifest(path).split
            if split not in {"Development", "Validation"}:
                raise ValueError(f"{split} manifests are prohibited during selection")


def _finite_number(row: dict[str, Any], field: str) -> float:
    value = row.get(field)
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError(f"{field} must be finite")
    return float(value)


def select_detector(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("detector rows must be non-empty")
    for row in rows:
        for field in ("misses", "false_positives", "mean_delay"):
            _finite_number(row, field)
    return min(
        rows,
        key=lambda row: (
            _finite_number(row, "misses"),
            _finite_number(row, "false_positives"),
            _finite_number(row, "mean_delay"),
            str(row["config_id"]),
        ),
    )


def select_retrieval(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("retrieval rows must be non-empty")
    fields = ("post_shift_cumulative_regret_30", "invalid_reuse", "tokens")
    for row in rows:
        for field in fields:
            _finite_number(row, field)
    return min(
        rows,
        key=lambda row: tuple(_finite_number(row, field) for field in fields)
        + (str(row["config_id"]),),
    )


def select_dormancy(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("dormancy rows must be non-empty")
    fields = ("false_dormancies", "invalid_reuse", "reactivation_delay")
    for row in rows:
        for field in fields:
            _finite_number(row, field)
    return min(
        rows,
        key=lambda row: tuple(_finite_number(row, field) for field in fields)
        + (int(row["patience"]),),
    )


def evaluate_dormancy_grid(patiences: list[int]) -> list[dict[str, int]]:
    """Score patience on predeclared transient and persistent relevance traces."""

    rows = []
    transient_bursts = (1, 2)  # Validation nuisance absences, in days.
    persistent_absence_days = 20
    for patience in patiences:
        rows.append(
            {
                "patience": int(patience),
                "false_dormancies": sum(burst >= patience for burst in transient_bursts),
                "invalid_reuse": min(persistent_absence_days, int(patience) - 1),
                "reactivation_delay": 0,
            }
        )
    return rows


def evaluate_detector_grid(config: dict[str, Any]) -> list[dict[str, Any]]:
    validation_path = Path(config["manifests"]["validation"])
    ensure_selection_paths([Path(config["manifests"]["development"]), validation_path])
    manifest = load_split_manifest(validation_path)
    rows: list[dict[str, Any]] = []
    for candidate in config["detector_grid"]:
        misses = 0
        false_positives = 0
        delays: list[int] = []
        episodes = 0
        for scenario_entry in manifest.scenarios:
            scenario = load_scenario(scenario_entry.path)
            shifts = [shift.start_day for shift in scenario.shifts if shift.start_day > 0]
            target = min(shifts) if shifts else None
            supply_only = bool(scenario.shifts) and all(
                shift.type == "sudden_supply" for shift in scenario.shifts
            )
            variable = "quoted_lead_time" if supply_only else "demand"
            for seed in manifest.seeds:
                episodes += 1
                detector = _make_detector(candidate, variable)
                env = InventoryEnv(scenario)
                environment_seed, _ = derive_seeds(seed)
                observation, _ = env.reset(seed=environment_seed)
                policy = FixedOrderPolicy(20)
                detected: list[int] = []
                terminated = False
                while not terminated:
                    public_signal = float(observation["quoted_lead_time"])
                    observation, _, terminated, _, record = env.step(policy.act(observation))
                    value = public_signal if supply_only else float(record["demand"])
                    if detector.update(value, int(record["day"])):
                        detected.append(int(record["day"]))
                if target is None:
                    false_positives += len(detected)
                    continue
                eligible = [day for day in detected if target <= day <= target + 30]
                if eligible:
                    first = min(eligible)
                    delays.append(first - target)
                    false_positives += len([day for day in detected if day != first])
                else:
                    misses += 1
                    false_positives += len(detected)
        rows.append(
            {
                "config_id": candidate["config_id"],
                "detector": candidate,
                "episodes": episodes,
                "misses": misses,
                "false_positives": false_positives,
                "mean_delay": mean(delays) if delays else 31.0,
            }
        )
    return rows


def _make_detector(candidate: dict[str, Any], variable: str = "demand"):
    kind = candidate["kind"]
    arguments = {key: value for key, value in candidate.items() if key not in {"kind", "config_id"}}
    if kind == "adwin":
        return ADWINDetector(variable, **arguments)
    if kind == "page_hinkley":
        return PageHinkleyDetector(variable, **arguments)
    raise ValueError(f"unknown detector kind: {kind}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retrieval-results", type=Path)
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    detector_rows = evaluate_detector_grid(config)
    result: dict[str, Any] = {
        "selection_scope": ["Development", "Validation"],
        "test_outcomes_accessed": False,
        "detector_rows": detector_rows,
        "selected_detector": select_detector(detector_rows),
    }
    dormancy_rows = evaluate_dormancy_grid(config["dormancy_grid"])
    result["dormancy_rows"] = dormancy_rows
    result["selected_dormancy"] = select_dormancy(dormancy_rows)
    if args.retrieval_results:
        retrieval_rows = json.loads(args.retrieval_results.read_text(encoding="utf-8"))
        result["retrieval_rows"] = retrieval_rows
        result["selected_retrieval"] = select_retrieval(retrieval_rows)
    else:
        result["selected_retrieval"] = None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"selected_detector": result["selected_detector"]["config_id"], "retrieval_complete": result["selected_retrieval"] is not None}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
