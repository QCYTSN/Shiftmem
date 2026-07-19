from scripts.report_phase4_pilot import render_report


def test_report_contains_required_readiness_fields() -> None:
    aggregate = {
        "complete": True,
        "expected_runs": 8,
        "completed_runs": 8,
        "total_tokens": 1000,
        "total_fallbacks": 0,
        "total_latency_ms": 5000,
        "metric_completeness": True,
        "models": [{"model": "core-a", "paired_seeds": 2, "mean_regret": -10, "regret_sd": 5}],
    }
    report = render_report(aggregate, minimum_effect=10)
    assert "Variance" in report
    assert "Runtime and token usage" in report
    assert "Metric completeness" in report
    assert "Recommended formal seed count" in report
    assert "Core A" in report
