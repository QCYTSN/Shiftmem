"""Aggregate JSONL experiment runs into reproducible CSV statistics."""

import argparse
import csv
import json
from collections import defaultdict
from math import sqrt
from pathlib import Path
from statistics import mean, stdev
from typing import Any


def aggregate_runs(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    oracle_costs: dict[tuple[str, int], float] = {}
    for run in runs:
        grouped[(run["scenario"], run["policy"])].append(run)
        if run["policy"] == "oracle":
            oracle_costs[(run["scenario"], int(run["seed"]))] = float(
                run["metrics"]["total_cost"]
            )

    rows: list[dict[str, Any]] = []
    for (scenario, policy), group in sorted(grouped.items()):
        row: dict[str, Any] = {"scenario": scenario, "policy": policy, "n": len(group)}
        metric_names = sorted(
            set.intersection(*(set(run["metrics"]) for run in group))
        )
        for metric_name in metric_names:
            values = [run["metrics"][metric_name] for run in group]
            if not all(isinstance(value, (int, float)) for value in values):
                continue
            numeric = [float(value) for value in values]
            average = mean(numeric)
            deviation = stdev(numeric) if len(numeric) > 1 else 0.0
            margin = 1.96 * deviation / sqrt(len(numeric)) if numeric else 0.0
            row[f"{metric_name}_mean"] = average
            row[f"{metric_name}_sd"] = deviation
            row[f"{metric_name}_ci95_low"] = average - margin
            row[f"{metric_name}_ci95_high"] = average + margin
        regrets = [
            float(run["metrics"]["total_cost"])
            - oracle_costs[(scenario, int(run["seed"]))]
            for run in group
            if (scenario, int(run["seed"])) in oracle_costs
        ]
        if regrets:
            row["paired_oracle_regret_mean"] = mean(regrets)
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    runs = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = aggregate_runs(runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    leading = ["scenario", "policy", "n"]
    remaining = sorted(set().union(*(row.keys() for row in rows)) - set(leading))
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=leading + remaining)
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({"groups": len(rows), "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
