import pytest

from scripts.aggregate_results import aggregate_runs


def test_aggregation_reports_statistics_and_paired_oracle_regret() -> None:
    runs = [
        {"scenario": "s", "policy": "fixed", "seed": 1, "metrics": {"total_cost": 12.0, "service_level": 0.8}},
        {"scenario": "s", "policy": "fixed", "seed": 2, "metrics": {"total_cost": 16.0, "service_level": 0.9}},
        {"scenario": "s", "policy": "oracle", "seed": 1, "metrics": {"total_cost": 10.0, "service_level": 1.0}},
        {"scenario": "s", "policy": "oracle", "seed": 2, "metrics": {"total_cost": 11.0, "service_level": 1.0}},
    ]
    rows = aggregate_runs(runs)
    fixed = next(row for row in rows if row["policy"] == "fixed")
    assert fixed["n"] == 2
    assert fixed["total_cost_mean"] == 14
    assert fixed["total_cost_sd"] == pytest.approx(2.828427, rel=1e-5)
    assert fixed["total_cost_ci95_low"] == pytest.approx(10.08)
    assert fixed["total_cost_ci95_high"] == pytest.approx(17.92)
    assert fixed["paired_oracle_regret_mean"] == 3.5
