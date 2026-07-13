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
