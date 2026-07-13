"""Inventory and adaptation metrics."""

from collections.abc import Sequence
from typing import Any


def summarize_episode(records: Sequence[dict[str, Any]]) -> dict[str, float | int]:
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
    }
    for key in (
        "purchase_cost",
        "holding_cost",
        "stockout_cost",
        "ordering_cost",
        "total_cost",
    ):
        summary[key] = float(sum(float(record[key]) for record in records))
    return summary
