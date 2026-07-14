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
