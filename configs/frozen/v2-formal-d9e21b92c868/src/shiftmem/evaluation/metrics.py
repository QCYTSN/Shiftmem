"""Inventory and adaptation metrics."""

from collections.abc import Sequence
from typing import Any


def summarize_episode(
    records: Sequence[dict[str, Any]], shift_day: int | None = None
) -> dict[str, float | int]:
    """Aggregate auditable daily environment records."""
    total_demand = sum(int(record["demand"]) for record in records)
    total_sales = sum(int(record["sales"]) for record in records)
    total_lost_sales = sum(int(record["lost_sales"]) for record in records)
    summary: dict[str, float | int] = {
        "days": len(records),
        "total_demand": total_demand,
        "total_sales": total_sales,
        "lost_sales": total_lost_sales,
        "service_level": total_sales / total_demand if total_demand else 1.0,
        "fill_rate": total_sales / total_demand if total_demand else 1.0,
        "stockout_rate": (
            sum(int(record["lost_sales"]) > 0 for record in records) / len(records)
            if records
            else 0.0
        ),
        "average_inventory": (
            sum(float(record["ending_inventory"]) for record in records) / len(records)
            if records
            else 0.0
        ),
    }
    for key in (
        "purchase_cost",
        "holding_cost",
        "stockout_cost",
        "ordering_cost",
        "total_cost",
    ):
        summary[key] = float(sum(float(record[key]) for record in records))
    if shift_day is not None:
        pre_shift = [record for record in records if int(record["day"]) < shift_day]
        _add_segment(summary, "pre_shift", pre_shift)
        for window in (7, 14, 30):
            post_shift = [
                record
                for record in records
                if shift_day <= int(record["day"]) < shift_day + window
            ]
            _add_segment(summary, f"post_shift_{window}", post_shift)
    return summary


def _add_segment(
    summary: dict[str, float | int], prefix: str, records: Sequence[dict[str, Any]]
) -> None:
    demand = sum(int(record["demand"]) for record in records)
    sales = sum(int(record["sales"]) for record in records)
    summary[f"{prefix}_total_cost"] = float(
        sum(float(record["total_cost"]) for record in records)
    )
    summary[f"{prefix}_lost_sales"] = sum(
        int(record["lost_sales"]) for record in records
    )
    summary[f"{prefix}_service_level"] = sales / demand if demand else 1.0


def summarize_strategy_reviews(
    scheduler_log: Sequence[dict[str, Any]],
    review_logs: Sequence[dict[str, Any]],
) -> dict[str, float | int]:
    """Aggregate v2 operational review metrics from separated logs.

    Counts scheduled/event/coalesced/cooldown-suppressed triggers, fallback and
    clamp counts, invalid-proposal rate, parameter churn, and mean parameter
    levels. All inputs are auditable log rows, not hidden state.
    """

    scheduled = sum(1 for row in scheduler_log if row.get("trigger") == "periodic")
    event = sum(1 for row in scheduler_log if row.get("trigger") == "event")
    coalesced = sum(1 for row in scheduler_log if row.get("trigger") == "coalesced")
    suppressed = sum(1 for row in scheduler_log if row.get("cooldown_suppressed"))

    total_reviews = len(review_logs)
    fallback_count = sum(1 for row in review_logs if row.get("fallback_used"))
    clamped_count = sum(1 for row in review_logs if row.get("clamped"))

    params = ("forecast_window", "safety_stock_multiplier", "lead_time_buffer")
    churn = 0
    previous: dict[str, Any] | None = None
    windows: list[float] = []
    for row in review_logs:
        active = row.get("active_strategy") or {}
        if "forecast_window" in active:
            windows.append(float(active["forecast_window"]))
        if previous is not None:
            churn += sum(1 for key in params if active.get(key) != previous.get(key))
        previous = active

    return {
        "total_reviews": total_reviews,
        "scheduled_reviews": scheduled,
        "event_reviews": event,
        "coalesced_reviews": coalesced,
        "cooldown_suppressed": suppressed,
        "fallback_count": fallback_count,
        "clamped_count": clamped_count,
        "invalid_proposal_rate": fallback_count / total_reviews if total_reviews else 0.0,
        "parameter_churn": churn,
        "mean_forecast_window": sum(windows) / len(windows) if windows else 0.0,
    }


def post_shift_cumulative_regret(
    records: Sequence[dict[str, Any]],
    oracle_records: Sequence[dict[str, Any]],
    shift_day: int,
    window: int = 30,
) -> float:
    """Return paired excess cost over an exact completed post-shift window."""

    if shift_day < 0 or window < 1:
        raise ValueError("shift_day must be non-negative and window must be positive")
    agent = {int(row["day"]): float(row["total_cost"]) for row in records}
    oracle = {
        int(row["day"]): float(row["total_cost"]) for row in oracle_records
    }
    days = range(shift_day, shift_day + window)
    missing = [day for day in days if day not in agent or day not in oracle]
    if missing:
        raise ValueError(f"paired post-shift window is incomplete: {missing}")
    return float(sum(agent[day] - oracle[day] for day in days))


def recovery_time(
    records: Sequence[dict[str, Any]],
    oracle_records: Sequence[dict[str, Any]],
    shift_day: int,
    *,
    rolling_window: int = 7,
    tolerance: float = 0.10,
    sustain_days: int = 7,
) -> dict[str, int | bool | None]:
    """Find the first sustained rolling-cost recovery or right-censor it."""

    if shift_day < 0 or rolling_window < 1 or sustain_days < 1:
        raise ValueError("recovery windows and shift_day must be positive")
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    agent = {int(row["day"]): float(row["total_cost"]) for row in records}
    oracle = {
        int(row["day"]): float(row["total_cost"]) for row in oracle_records
    }
    paired_days = sorted(set(agent) & set(oracle))
    if not paired_days:
        raise ValueError("paired records must be non-empty")
    last_day = paired_days[-1]
    consecutive = 0
    for end_day in range(shift_day + rolling_window - 1, last_day + 1):
        window_days = range(end_day - rolling_window + 1, end_day + 1)
        if any(day not in agent or day not in oracle for day in window_days):
            consecutive = 0
            continue
        agent_cost = sum(agent[day] for day in window_days)
        oracle_cost = sum(oracle[day] for day in window_days)
        within = abs(agent_cost - oracle_cost) <= tolerance * max(
            abs(oracle_cost), 1e-12
        )
        consecutive = consecutive + 1 if within else 0
        if consecutive >= sustain_days:
            recovery_day = end_day - sustain_days + 1
            return {
                "recovered": True,
                "recovery_day": recovery_day,
                "recovery_time": recovery_day - shift_day,
                "censored_at": None,
            }
    return {
        "recovered": False,
        "recovery_day": None,
        "recovery_time": None,
        "censored_at": last_day,
    }
