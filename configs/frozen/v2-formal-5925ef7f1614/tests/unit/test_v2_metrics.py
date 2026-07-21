"""Tests for v2 operational strategy-review metrics."""

from shiftmem.evaluation.metrics import summarize_strategy_reviews


def _scheduler_log():
    return [
        {"day": 0, "trigger": "periodic", "should_review": True, "coalesced": False, "cooldown_suppressed": False},
        {"day": 2, "trigger": "none", "should_review": False, "coalesced": False, "cooldown_suppressed": True},
        {"day": 5, "trigger": "coalesced", "should_review": True, "coalesced": True, "cooldown_suppressed": False},
        {"day": 7, "trigger": "event", "should_review": True, "coalesced": False, "cooldown_suppressed": False},
    ]


def _review_logs():
    return [
        {"day": 0, "trigger_reason": "periodic", "fallback_used": False, "clamped": False,
         "active_strategy": {"forecast_window": 14, "safety_stock_multiplier": 1.2, "lead_time_buffer": 1},
         "proposal": {"forecast_window": 14}},
        {"day": 5, "trigger_reason": "coalesced", "fallback_used": False, "clamped": True,
         "active_strategy": {"forecast_window": 10, "safety_stock_multiplier": 1.5, "lead_time_buffer": 2},
         "proposal": {"forecast_window": 10}},
        {"day": 7, "trigger_reason": "event", "fallback_used": True, "clamped": False,
         "active_strategy": {"forecast_window": 10, "safety_stock_multiplier": 1.5, "lead_time_buffer": 2},
         "proposal": None},
    ]


def test_review_counts_by_trigger():
    metrics = summarize_strategy_reviews(_scheduler_log(), _review_logs())
    assert metrics["scheduled_reviews"] == 1
    assert metrics["event_reviews"] == 1
    assert metrics["coalesced_reviews"] == 1
    assert metrics["cooldown_suppressed"] == 1
    assert metrics["total_reviews"] == 3


def test_fallback_and_clamp_and_invalid_rates():
    metrics = summarize_strategy_reviews(_scheduler_log(), _review_logs())
    assert metrics["fallback_count"] == 1
    assert metrics["clamped_count"] == 1
    # Invalid proposal rate = fallbacks / reviews.
    assert abs(metrics["invalid_proposal_rate"] - 1 / 3) < 1e-9


def test_parameter_churn_measures_changes_between_active_strategies():
    metrics = summarize_strategy_reviews(_scheduler_log(), _review_logs())
    # forecast_window changed 14->10 once; multiplier 1.2->1.5; buffer 1->2; then no change.
    assert metrics["parameter_churn"] >= 1
    assert "mean_forecast_window" in metrics


def test_empty_logs_are_safe():
    metrics = summarize_strategy_reviews([], [])
    assert metrics["total_reviews"] == 0
    assert metrics["invalid_proposal_rate"] == 0.0
