"""Deterministic post-Test evidence, statistics, and reliability aggregation."""

from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
import json
from math import sqrt
from pathlib import Path
from random import Random
from statistics import median
from typing import Any, Callable, Iterable

from .formal_v2 import FormalV2CellResult
from .statistics import paired_analysis


def file_sha256(path: str | Path) -> str:
    digest = sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        Path(path).read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{line_number}: {error}") from error
    return rows


def verify_declared_sources(root: Path, sources: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Verify immutable evidence sources and return their canonical manifest rows."""

    verified: list[dict[str, Any]] = []
    seen: set[str] = set()
    for source in sources:
        relative = Path(str(source["path"]))
        normalized = relative.as_posix()
        if normalized in seen:
            raise ValueError(f"duplicate evidence source: {normalized}")
        seen.add(normalized)
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(f"evidence source missing: {normalized}")
        digest = file_sha256(path)
        if digest != source["sha256"]:
            raise ValueError(f"evidence hash mismatch: {normalized}")
        row = {
            "kind": str(source["kind"]),
            "path": normalized,
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
        if path.suffix.lower() == ".jsonl":
            row["records"] = len(load_jsonl(path))
            expected = source.get("records")
            if expected is not None and row["records"] != int(expected):
                raise ValueError(
                    f"evidence record count mismatch: {normalized}: "
                    f"expected={expected}, actual={row['records']}"
                )
        if source.get("split") is not None:
            row["split"] = str(source["split"])
        verified.append(row)
    return sorted(verified, key=lambda item: item["path"])


def evidence_identity(files: Iterable[dict[str, Any]]) -> tuple[str, str]:
    lines = [f"{row['sha256']}  {row['path']}" for row in files]
    manifest = "\n".join(sorted(lines)) + "\n"
    digest = sha256(manifest.encode("utf-8")).hexdigest()
    return f"v2-formal-results-{digest[:12]}", digest


def load_declared_cells(
    root: Path, sources: Iterable[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load cells without rewriting source metadata and report disclosure anomalies."""

    cells: list[dict[str, Any]] = []
    anomaly_counts: dict[str, int] = defaultdict(int)
    seen_ids: set[str] = set()
    for source in sources:
        if source["kind"] != "cells":
            continue
        split = str(source["split"])
        path = root / source["path"]
        rows = load_jsonl(path)
        for line_number, row in enumerate(rows, 1):
            validated = FormalV2CellResult.model_validate(row)
            if validated.cell_id in seen_ids:
                raise ValueError(f"duplicate formal cell: {validated.cell_id}")
            seen_ids.add(validated.cell_id)
            value = validated.model_dump(mode="json")
            value["manifest_split"] = split
            cells.append(value)
            if validated.test_outcomes_accessed is not True:
                anomaly_counts[Path(source["path"]).as_posix()] += 1
    anomalies = [
        {
            "type": "cell_test_access_flag_false",
            "path": path,
            "affected_cells": count,
            "observed": False,
            "derived_interpretation": True,
        }
        for path, count in sorted(anomaly_counts.items())
    ]
    return cells, anomalies


def validate_expected_matrix(cells: list[dict[str, Any]], expected: dict[str, Any]) -> None:
    if len(cells) != int(expected["total_cells"]):
        raise ValueError(
            f"formal matrix cell count mismatch: expected={expected['total_cells']}, "
            f"actual={len(cells)}"
        )
    for split, split_expected in expected["splits"].items():
        rows = [row for row in cells if row["manifest_split"] == split]
        applicable = sum(bool(row["endpoint_applicable"]) for row in rows)
        if len(rows) != int(split_expected["cells"]):
            raise ValueError(f"{split} cell count mismatch")
        if applicable != int(split_expected["applicable_endpoint_cells"]):
            raise ValueError(f"{split} applicable endpoint count mismatch")
    observed_models = sorted({str(row["model"]) for row in cells})
    observed_methods = sorted({str(row["method"]) for row in cells})
    if observed_models != sorted(expected["models"]):
        raise ValueError(f"formal model matrix mismatch: {observed_models}")
    if observed_methods != sorted(expected["methods"]):
        raise ValueError(f"formal method matrix mismatch: {observed_methods}")


def _paired_rows(
    cells: Iterable[dict[str, Any]],
    metric: Callable[[dict[str, Any]], float | None],
) -> list[tuple[float, float]]:
    units: dict[tuple[str, str, str, int], dict[str, float]] = defaultdict(dict)
    for row in cells:
        value = metric(row)
        if value is None:
            continue
        key = (
            str(row["manifest_split"]),
            str(row["scenario_id"]),
            str(row["model"]),
            int(row["seed"]),
        )
        method = str(row["method"])
        if method in units[key]:
            raise ValueError(f"duplicate method within paired unit: {key}: {method}")
        units[key][method] = float(value)
    incomplete = sorted(key for key, methods in units.items() if set(methods) != {"shiftmem", "vector"})
    if incomplete:
        raise ValueError(f"incomplete paired units: {incomplete}")
    return [(methods["shiftmem"], methods["vector"]) for _, methods in sorted(units.items())]


def paired_result(
    cells: Iterable[dict[str, Any]],
    metric: Callable[[dict[str, Any]], float | None],
) -> dict[str, Any]:
    pairs = _paired_rows(cells, metric)
    return summarize_pairs(pairs)


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("quantile requires non-empty values")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _stratified_resampled_mean_inference(
    strata: dict[str, list[float]], *, resamples: int, seed: int
) -> dict[str, Any]:
    """Resample environment seeds within fixed scenario strata at equal weight."""

    if not strata or any(len(values) < 2 for values in strata.values()):
        raise ValueError("stratified inference requires at least two values per stratum")
    ordered = [(name, strata[name]) for name in sorted(strata)]
    observed = sum(sum(values) / len(values) for _, values in ordered) / len(ordered)
    bootstrap_rng = Random(seed)
    bootstrap_means = []
    for _ in range(resamples):
        stratum_means = [
            sum(values[bootstrap_rng.randrange(len(values))] for _ in values)
            / len(values)
            for _, values in ordered
        ]
        bootstrap_means.append(sum(stratum_means) / len(stratum_means))
    sign_rng = Random(seed + 1)
    extreme = 0
    for _ in range(resamples):
        candidate = sum(
            sum(value if sign_rng.getrandbits(1) else -value for value in values)
            / len(values)
            for _, values in ordered
        ) / len(ordered)
        if abs(candidate) >= abs(observed) - 1e-12:
            extreme += 1
    return {
        "n_clusters": sum(len(values) for _, values in ordered),
        "n_fixed_scenario_strata": len(ordered),
        "mean_difference": observed,
        "cluster_bootstrap_ci_low": _quantile(bootstrap_means, 0.025),
        "cluster_bootstrap_ci_high": _quantile(bootstrap_means, 0.975),
        "cluster_sign_flip_p_value": (extreme + 1) / (resamples + 1),
        "resamples": resamples,
        "random_seed": seed,
        "ci_method": "environment-seed bootstrap within fixed scenario strata",
        "test_method": (
            "two-sided Monte Carlo cluster sign-flip test of the equal-scenario mean"
        ),
    }


def build_clustered_primary_sensitivity(
    cells: list[dict[str, Any]], *, resamples: int = 50000, seed: int = 20260723
) -> dict[str, Any]:
    """Use scenario-seed clusters without replacing the frozen cell-level result."""

    applicable = [row for row in cells if row["endpoint_applicable"]]
    units: dict[tuple[str, str, int], dict[str, dict[str, float]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    for row in applicable:
        key = (
            str(row["manifest_split"]),
            str(row["scenario_id"]),
            int(row["seed"]),
        )
        model = str(row["model"])
        method = str(row["method"])
        units[key][model][method] = float(row["post_shift_cumulative_regret_30"])

    expected_models = sorted({str(row["model"]) for row in applicable})
    cluster_means_by_scenario: dict[str, list[float]] = defaultdict(list)
    model_contrasts_by_scenario: dict[str, list[float]] = defaultdict(list)
    cluster_rows: list[dict[str, Any]] = []
    for key, models in sorted(units.items()):
        if sorted(models) != expected_models:
            raise ValueError(f"incomplete model cluster: {key}")
        differences = {}
        for model in expected_models:
            methods = models[model]
            if set(methods) != {"shiftmem", "vector"}:
                raise ValueError(f"incomplete method cluster: {key}: {model}")
            difference = methods["shiftmem"] - methods["vector"]
            differences[model] = difference
        cluster_mean = sum(differences.values()) / len(differences)
        cluster_means_by_scenario[key[1]].append(cluster_mean)
        cluster_rows.append(
            {
                "split": key[0],
                "scenario": key[1],
                "seed": key[2],
                "mean_model_difference": cluster_mean,
            }
        )
        if expected_models == ["deepseek", "minimax"]:
            contrast = differences["deepseek"] - differences["minimax"]
            model_contrasts_by_scenario[key[1]].append(contrast)

    result = {
        "status": "post_hoc_mean_aligned_sensitivity",
        "confirmatory_primary_result_changed": False,
        "cluster_definition": "manifest split x scenario x environment seed",
        "reason": (
            "The two model cells in each cluster share the deterministic demand and "
            "supply realization; resampling clusters avoids treating them as independent."
        ),
        "overall": _stratified_resampled_mean_inference(
            cluster_means_by_scenario, resamples=resamples, seed=seed
        ),
        "cluster_count": len(cluster_rows),
        "cells_per_cluster": len(expected_models) * 2,
        "models": expected_models,
    }
    if model_contrasts_by_scenario:
        result["model_heterogeneity"] = {
            **_stratified_resampled_mean_inference(
                model_contrasts_by_scenario, resamples=resamples, seed=seed + 10
            ),
            "contrast": "DeepSeek method difference minus MiniMax method difference",
            "status": "post_hoc_exploratory_interaction",
            "multiplicity_adjusted": False,
        }
    return result


def summarize_pairs(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    """Apply the frozen paired analysis and retain direction counts."""

    result = paired_analysis(pairs)
    differences = [left - right for left, right in pairs]
    return {
        **result,
        "shiftmem_mean": sum(left for left, _ in pairs) / len(pairs),
        "vector_mean": sum(right for _, right in pairs) / len(pairs),
        "shiftmem_wins": sum(value < 0 for value in differences),
        "ties": sum(value == 0 for value in differences),
        "shiftmem_losses": sum(value > 0 for value in differences),
    }


def _pearson(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    left_centered = [value - left_mean for value in left]
    right_centered = [value - right_mean for value in right]
    denominator = sqrt(
        sum(value * value for value in left_centered)
        * sum(value * value for value in right_centered)
    )
    if denominator == 0:
        return None
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left_centered, right_centered)
    ) / denominator


def _average_ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start + 1
        while end < len(order) and values[order[end]] == values[order[start]]:
            end += 1
        rank = (start + 1 + end) / 2
        for index in order[start:end]:
            ranks[index] = rank
        start = end
    return ranks


def _association(outcome: list[float], burden: list[float]) -> dict[str, Any]:
    return {
        "n": len(outcome),
        "pearson_correlation": _pearson(outcome, burden),
        "spearman_correlation": _pearson(
            _average_ranks(outcome), _average_ranks(burden)
        ),
        "p_values_reported": False,
        "interpretation": "descriptive association, not a causal effect",
    }


def _sensitivity_summary(pairs: list[tuple[float, float]]) -> dict[str, Any]:
    if len(pairs) < 2:
        return {"n": len(pairs), "status": "insufficient_pairs"}
    return {
        **summarize_pairs(pairs),
        "status": "post_hoc_descriptive",
        "p_value_status": "unadjusted_post_hoc",
    }


def build_reliability_outcome_impact(
    cells: list[dict[str, Any]], journal: dict[str, Any]
) -> dict[str, Any]:
    """Relate reliability burden to paired regret without altering H1."""

    journal_by_cell = journal["by_cell"]
    units: dict[tuple[str, str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in cells:
        if not row["endpoint_applicable"]:
            continue
        key = (
            str(row["manifest_split"]),
            str(row["scenario_id"]),
            str(row["model"]),
            int(row["seed"]),
        )
        units[key][str(row["method"])] = row
    incomplete = sorted(key for key, methods in units.items() if set(methods) != {"shiftmem", "vector"})
    if incomplete:
        raise ValueError(f"incomplete reliability paired units: {incomplete}")

    metric_specs: dict[str, tuple[Callable[[dict[str, Any]], int], Callable[[dict[str, Any]], int]]] = {
        "parse_failure": (
            lambda row: int(row["parse_failures"]),
            lambda row: int(row["provider_attempts"]),
        ),
        "fallback": (
            lambda row: int(row["fallback_count"]),
            lambda row: len(row["review_logs"]),
        ),
        "provider_failure": (
            lambda row: int(journal_by_cell[str(row["cell_id"])]["failed_attempts"]),
            lambda row: int(journal_by_cell[str(row["cell_id"])]["terminal_attempts"]),
        ),
    }

    def metric_records(
        numerator: Callable[[dict[str, Any]], int],
        denominator: Callable[[dict[str, Any]], int],
    ) -> list[dict[str, Any]]:
        records = []
        for key, methods in sorted(units.items()):
            shiftmem = methods["shiftmem"]
            vector = methods["vector"]
            shift_count = numerator(shiftmem)
            vector_count = numerator(vector)
            shift_denominator = denominator(shiftmem)
            vector_denominator = denominator(vector)
            shift_rate = shift_count / shift_denominator if shift_denominator else 0.0
            vector_rate = vector_count / vector_denominator if vector_denominator else 0.0
            records.append(
                {
                    "split": key[0],
                    "scenario": key[1],
                    "model": key[2],
                    "seed": key[3],
                    "outcome_pair": (
                        float(shiftmem["post_shift_cumulative_regret_30"]),
                        float(vector["post_shift_cumulative_regret_30"]),
                    ),
                    "outcome_difference": float(
                        shiftmem["post_shift_cumulative_regret_30"]
                        - vector["post_shift_cumulative_regret_30"]
                    ),
                    "burden_difference": shift_rate - vector_rate,
                    "maximum_pair_burden_rate": max(shift_rate, vector_rate),
                    "zero_event_pair": shift_count == 0 and vector_count == 0,
                }
            )
        return records

    def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
        threshold = median([row["maximum_pair_burden_rate"] for row in records])
        low = [
            row for row in records if row["maximum_pair_burden_rate"] <= threshold
        ]
        high = [
            row for row in records if row["maximum_pair_burden_rate"] > threshold
        ]
        zero = [row for row in records if row["zero_event_pair"]]
        def stratum(rows: list[dict[str, Any]]) -> dict[str, Any]:
            return {
                "n": len(rows),
                "mean_outcome_difference": (
                    sum(row["outcome_difference"] for row in rows) / len(rows)
                    if rows
                    else None
                ),
            }

        return {
            "burden_difference_association": _association(
                [row["outcome_difference"] for row in records],
                [row["burden_difference"] for row in records],
            ),
            "zero_event_pair_sensitivity": _sensitivity_summary(
                [row["outcome_pair"] for row in zero]
            ),
            "empirical_median_burden_strata": {
                "threshold": threshold,
                "threshold_status": "post_hoc_empirical_median",
                "lower_or_equal": stratum(low),
                "higher": stratum(high),
            },
        }

    metrics = {}
    for name, (numerator, denominator) in metric_specs.items():
        records = metric_records(numerator, denominator)
        metrics[name] = {
            "overall": summarize_records(records),
            "by_split": {
                split: summarize_records(
                    [row for row in records if row["split"] == split]
                )
                for split in sorted({row["split"] for row in records})
            },
            "by_model": {
                model: summarize_records(
                    [row for row in records if row["model"] == model]
                )
                for model in sorted({row["model"] for row in records})
            },
        }

    zero_event_means = {
        name: float(value["overall"]["zero_event_pair_sensitivity"].get("mean_difference", 0.0))
        for name, value in metrics.items()
    }
    return {
        "status": "post_hoc_descriptive_sensitivity",
        "causal_interpretation_allowed": False,
        "confirmatory_primary_result_changed": False,
        "paired_units": len(units),
        "metrics": metrics,
        "descriptive_pattern": {
            "zero_event_subset_mean_differences": zero_event_means,
            "all_zero_event_subset_means_unfavorable_to_shiftmem": all(
                value > 0 for value in zero_event_means.values()
            ),
            "interpretation": (
                "The unfavorable overall ShiftMem-minus-VectorMemory direction "
                "persists in every zero-event sensitivity subset. These subsets are "
                "post-hoc and model-imbalanced, so they do not establish robustness, "
                "but observed reliability burden does not provide a simple explanation "
                "for the primary result."
            ),
        },
    }


def build_execution_order_audit(
    cells: list[dict[str, Any]], journal: dict[str, Any]
) -> dict[str, Any]:
    """Audit fixed method order using append order because journals lack timestamps."""

    journal_by_cell = journal["by_cell"]
    units: dict[tuple[str, str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in cells:
        if row["endpoint_applicable"]:
            key = (
                str(row["manifest_split"]),
                str(row["scenario_id"]),
                str(row["model"]),
                int(row["seed"]),
            )
            units[key][str(row["method"])] = row

    def rate(numerator: int, denominator: int) -> float:
        return numerator / denominator if denominator else 0.0

    records: list[dict[str, Any]] = []
    for key, methods in sorted(units.items()):
        if set(methods) != {"shiftmem", "vector"}:
            raise ValueError(f"incomplete execution-order paired unit: {key}")
        shiftmem = methods["shiftmem"]
        vector = methods["vector"]
        shift_journal = journal_by_cell[str(shiftmem["cell_id"])]
        vector_journal = journal_by_cell[str(vector["cell_id"])]
        shift_order = int(shift_journal["first_terminal_order"])
        vector_order = int(vector_journal["first_terminal_order"])
        shift_runs = tuple(shift_journal["run_ids"])
        vector_runs = tuple(vector_journal["run_ids"])
        run_pair = (
            f"same:{shift_runs[0]}"
            if shift_runs == vector_runs and len(shift_runs) == 1
            else "cross-run-or-multiple"
        )
        records.append(
            {
                "split": key[0],
                "scenario": key[1],
                "model": key[2],
                "seed": key[3],
                "outcome_difference": float(
                    shiftmem["post_shift_cumulative_regret_30"]
                    - vector["post_shift_cumulative_regret_30"]
                ),
                "pair_terminal_midpoint": (shift_order + vector_order) / 2,
                "shiftmem_after_vector": shift_order > vector_order,
                "run_pair": run_pair,
                "parse_burden_difference": rate(
                    int(shiftmem["parse_failures"]), int(shiftmem["provider_attempts"])
                )
                - rate(int(vector["parse_failures"]), int(vector["provider_attempts"])),
                "fallback_burden_difference": rate(
                    int(shiftmem["fallback_count"]), len(shiftmem["review_logs"])
                )
                - rate(int(vector["fallback_count"]), len(vector["review_logs"])),
                "provider_failure_burden_difference": rate(
                    int(shift_journal["failed_attempts"]),
                    int(shift_journal["terminal_attempts"]),
                )
                - rate(
                    int(vector_journal["failed_attempts"]),
                    int(vector_journal["terminal_attempts"]),
                ),
            }
        )

    median_position = median([row["pair_terminal_midpoint"] for row in records])

    def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
        def average(field: str) -> float | None:
            return (
                sum(float(row[field]) for row in rows) / len(rows) if rows else None
            )

        return {
            "n": len(rows),
            "mean_outcome_difference": average("outcome_difference"),
            "mean_parse_burden_difference": average("parse_burden_difference"),
            "mean_fallback_burden_difference": average("fallback_burden_difference"),
            "mean_provider_failure_burden_difference": average(
                "provider_failure_burden_difference"
            ),
        }

    run_pairs = sorted({str(row["run_pair"]) for row in records})
    return {
        "status": "post_hoc_descriptive_execution_order_audit",
        "causal_interpretation_allowed": False,
        "confirmatory_primary_result_changed": False,
        "sequence_basis": "terminal record append order across the four declared journals",
        "wall_clock_timestamps_available": False,
        "paired_units": len(records),
        "method_order": {
            "shiftmem_after_vector_pairs": sum(
                bool(row["shiftmem_after_vector"]) for row in records
            ),
            "vector_after_shiftmem_pairs": sum(
                not bool(row["shiftmem_after_vector"]) for row in records
            ),
            "interpretation": (
                "Method execution was not randomized or counterbalanced; append order "
                "can diagnose trends but cannot remove this design limitation."
            ),
        },
        "outcome_vs_execution_position": _association(
            [float(row["outcome_difference"]) for row in records],
            [float(row["pair_terminal_midpoint"]) for row in records],
        ),
        "execution_halves": {
            "median_terminal_midpoint": median_position,
            "early": summarize(
                [row for row in records if row["pair_terminal_midpoint"] <= median_position]
            ),
            "late": summarize(
                [row for row in records if row["pair_terminal_midpoint"] > median_position]
            ),
        },
        "by_run_pair": {
            run_pair: summarize(
                [row for row in records if row["run_pair"] == run_pair]
            )
            for run_pair in run_pairs
        },
    }


def build_statistical_analysis(cells: list[dict[str, Any]], evidence_id: str) -> dict[str, Any]:
    applicable = [row for row in cells if row["endpoint_applicable"]]
    endpoint = lambda row: row["post_shift_cumulative_regret_30"]
    by_split = {
        split: paired_result(
            [row for row in applicable if row["manifest_split"] == split], endpoint
        )
        for split in sorted({row["manifest_split"] for row in applicable})
    }
    by_model = {
        model: paired_result(
            [row for row in applicable if row["model"] == model], endpoint
        )
        for model in sorted({row["model"] for row in applicable})
    }
    by_scenario = {
        scenario: paired_result(
            [row for row in applicable if row["scenario_id"] == scenario], endpoint
        )
        for scenario in sorted({row["scenario_id"] for row in applicable})
    }
    stable = [row for row in cells if not row["endpoint_applicable"]]
    overall = paired_result(applicable, endpoint)
    equal_group_mean = sum(
        float(result["mean_difference"]) for result in by_scenario.values()
    ) / len(by_scenario)
    return {
        "schema": "shiftmem-formal-v2-statistical-analysis-v1",
        "evidence_freeze_id": evidence_id,
        "test_outcomes_accessed": True,
        "analysis_status": "final_machine_readable",
        "paper_claims_finalized": False,
        "primary_endpoint": {
            "field": "post_shift_cumulative_regret_30",
            "reporting_label": "30-day oracle-relative cost gap",
            "construct_note": (
                "OraclePolicy is a parameter-aware base-stock heuristic, not a proof "
                "of globally optimal control; the shared Oracle term cancels from "
                "the paired ShiftMem-minus-VectorMemory difference."
            ),
            "difference_direction": "ShiftMem minus VectorMemory; negative favors ShiftMem",
            "confirmatory_population": "declared non-stable Test-ID and Test-OOD groups",
            "equal_group_weighting": True,
            "equal_group_weighted_mean_difference": equal_group_mean,
            "overall": {
                **overall,
                "alpha": 0.05,
                "two_sided": True,
                "h1_supported": bool(
                    float(overall["mean_difference"]) < 0
                    and float(overall["test"]["p_value"]) < 0.05
                ),
            },
            "by_split": by_split,
            "by_split_inference": "predeclared split decomposition; p-values are unadjusted",
            "by_model": by_model,
            "by_model_inference": "heterogeneity decomposition; p-values are unadjusted",
            "by_scenario": by_scenario,
            "by_scenario_inference": "descriptive subgroup decomposition; p-values are unadjusted",
            "clustered_mean_sensitivity": build_clustered_primary_sensitivity(cells),
        },
        "stable_environment_descriptive": {
            "status": "descriptive_only",
            "metric": "inventory_metrics.total_cost",
            "analysis": paired_result(
                stable, lambda row: row["inventory_metrics"]["total_cost"]
            ),
        },
    }


def _cell_reliability(rows: list[dict[str, Any]]) -> dict[str, Any]:
    attempts = sum(int(row["provider_attempts"]) for row in rows)
    parse_failures = sum(int(row["parse_failures"]) for row in rows)
    reviews = sum(len(row["review_logs"]) for row in rows)
    fallbacks = sum(int(row["fallback_count"]) for row in rows)
    applicable = [row for row in rows if row["endpoint_applicable"]]
    recovered = sum(bool(row["recovery"]["recovered"]) for row in applicable)
    reuse_keys = ("reused", "retrieved_not_cited", "cited_but_rejected")
    return {
        "cells": len(rows),
        "provider_attempts_recorded_by_cells": attempts,
        "parse_failures": parse_failures,
        "parse_failures_per_attempt": parse_failures / attempts if attempts else 0.0,
        "reviews": reviews,
        "fallbacks": fallbacks,
        "fallbacks_per_review": fallbacks / reviews if reviews else 0.0,
        "input_tokens": sum(int(row["input_tokens"]) for row in rows),
        "output_tokens": sum(int(row["output_tokens"]) for row in rows),
        "applicable_recovery_cells": len(applicable),
        "recovered_cells": recovered,
        "recovery_rate": recovered / len(applicable) if applicable else None,
        "memory_reuse": {
            key: sum(int(row["reuse_metrics"][key]) for row in rows)
            for key in reuse_keys
        },
    }


def summarize_journals(
    root: Path,
    sources: Iterable[dict[str, Any]],
    cells: list[dict[str, Any]],
) -> dict[str, Any]:
    cell_by_id = {str(row["cell_id"]): row for row in cells}
    terminal: list[dict[str, Any]] = []
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    terminal_order = 0
    for source_order, source in enumerate(sources):
        if source["kind"] != "journal":
            continue
        for record_order, raw_row in enumerate(load_jsonl(root / source["path"])):
            row = dict(raw_row)
            identity = row.get("identity") or {}
            key = (str(identity.get("run_id", "")), str(row["decision_id"]))
            latest[key] = row
            if row.get("status") in {"complete", "failed"}:
                row["_source_path"] = Path(source["path"]).as_posix()
                row["_source_order"] = source_order
                row["_record_order"] = record_order
                row["_terminal_order"] = terminal_order
                row["_run_id"] = str(identity.get("run_id", ""))
                terminal.append(row)
                terminal_order += 1
    unresolved = [row for row in latest.values() if row.get("status") == "reserved"]
    if unresolved:
        raise ValueError(
            "unresolved formal reservations: "
            + ", ".join(str(row["decision_id"]) for row in unresolved)
        )
    unmatched = sorted(
        {str(row["cell_id"]) for row in terminal if str(row["cell_id"]) not in cell_by_id}
    )
    if unmatched:
        raise ValueError(f"journal rows reference unknown formal cells: {unmatched}")

    def attempt_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
        complete = [row for row in rows if row.get("status") == "complete"]
        failed = [row for row in rows if row.get("status") == "failed"]
        latency = [
            float(row["provider_response"]["latency_ms"])
            for row in complete
            if (row.get("provider_response") or {}).get("latency_ms") is not None
        ]
        return {
            "terminal_attempts": len(rows),
            "successful_responses": len(complete),
            "failed_attempts": len(failed),
            "successful_cost_cny": sum(
                float(row.get("estimated_cost_cny") or 0) for row in complete
            ),
            "failed_reservation_ledger_cny": sum(
                float(row.get("estimated_cost_cny") or 0) for row in failed
            ),
            "input_tokens": sum(int(row.get("input_tokens") or 0) for row in rows),
            "output_tokens": sum(int(row.get("output_tokens") or 0) for row in rows),
            "mean_success_latency_ms": sum(latency) / len(latency) if latency else None,
            "latency_observations": len(latency),
        }

    def grouped(field: str) -> dict[str, Any]:
        values = sorted({str(cell_by_id[str(row["cell_id"])][field]) for row in terminal})
        return {
            value: attempt_summary(
                [
                    row
                    for row in terminal
                    if str(cell_by_id[str(row["cell_id"])][field]) == value
                ]
            )
            for value in values
        }

    def cell_attempt_summary(cell_id: str) -> dict[str, Any]:
        rows = [row for row in terminal if str(row["cell_id"]) == cell_id]
        orders = [int(row["_terminal_order"]) for row in rows]
        return {
            **attempt_summary(rows),
            "run_ids": sorted({str(row["_run_id"]) for row in rows}),
            "journal_sources": sorted({str(row["_source_path"]) for row in rows}),
            "first_terminal_order": min(orders) if orders else None,
            "last_terminal_order": max(orders) if orders else None,
        }

    detail = []
    for split in sorted({str(row["manifest_split"]) for row in cells}):
        for model in sorted({str(row["model"]) for row in cells}):
            for method in sorted({str(row["method"]) for row in cells}):
                rows = [
                    row
                    for row in terminal
                    if cell_by_id[str(row["cell_id"])]["manifest_split"] == split
                    and cell_by_id[str(row["cell_id"])]["model"] == model
                    and cell_by_id[str(row["cell_id"])]["method"] == method
                ]
                detail.append(
                    {"split": split, "model": model, "method": method, **attempt_summary(rows)}
                )

    return {
        **attempt_summary(terminal),
        "unresolved_reservations": 0,
        "official_provider_billing_cny": None,
        "official_billing_status": "requires_provider_statement_reconciliation",
        "by_split": grouped("manifest_split"),
        "by_model": grouped("model"),
        "by_method": grouped("method"),
        "by_split_model_method": detail,
        "by_cell": {
            cell_id: cell_attempt_summary(cell_id)
            for cell_id in sorted(cell_by_id)
        },
    }


def build_reliability_audit(
    cells: list[dict[str, Any]],
    journal: dict[str, Any],
    evidence_id: str,
) -> dict[str, Any]:
    def grouped(field: str) -> dict[str, Any]:
        return {
            value: _cell_reliability([row for row in cells if str(row[field]) == value])
            for value in sorted({str(row[field]) for row in cells})
        }

    detail = []
    for split in sorted({str(row["manifest_split"]) for row in cells}):
        for model in sorted({str(row["model"]) for row in cells}):
            for method in sorted({str(row["method"]) for row in cells}):
                rows = [
                    row
                    for row in cells
                    if row["manifest_split"] == split
                    and row["model"] == model
                    and row["method"] == method
                ]
                detail.append(
                    {"split": split, "model": model, "method": method, **_cell_reliability(rows)}
                )
    overall = _cell_reliability(cells)
    return {
        "schema": "shiftmem-formal-v2-reliability-audit-v1",
        "evidence_freeze_id": evidence_id,
        "test_outcomes_accessed": True,
        "overall": overall,
        "journal": journal,
        "attempt_reconciliation": {
            "journal_terminal_attempts": journal["terminal_attempts"],
            "cell_recorded_attempts": overall["provider_attempts_recorded_by_cells"],
            "difference": journal["terminal_attempts"] - overall["provider_attempts_recorded_by_cells"],
            "interpretation": "journal includes terminalized interrupted or otherwise non-cell-final attempts",
        },
        "by_split": grouped("manifest_split"),
        "by_model": grouped("model"),
        "by_method": grouped("method"),
        "by_split_model_method": detail,
        "outcome_impact": build_reliability_outcome_impact(cells, journal),
        "execution_order_audit": build_execution_order_audit(cells, journal),
    }


def atomic_write_json(path: str | Path, value: dict[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
