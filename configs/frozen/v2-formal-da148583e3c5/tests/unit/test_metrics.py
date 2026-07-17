import pytest

from shiftmem.evaluation.metrics import summarize_episode


def make_records() -> list[dict]:
    records = []
    for day in range(40):
        demand = 10
        sales = 8 if day >= 10 else 10
        records.append(
            {
                "day": day,
                "demand": demand,
                "sales": sales,
                "lost_sales": demand - sales,
                "ending_inventory": 5,
                "purchase_cost": 1.0,
                "holding_cost": 2.0,
                "stockout_cost": float((demand - sales) * 3),
                "ordering_cost": 0.0,
                "total_cost": 3.0 + float((demand - sales) * 3),
            }
        )
    return records


def test_summary_includes_inventory_and_stockout_metrics() -> None:
    summary = summarize_episode(make_records())
    assert summary["average_inventory"] == 5
    assert summary["stockout_rate"] == 30 / 40
    assert summary["fill_rate"] == summary["service_level"]


def test_summary_reports_shift_segments() -> None:
    summary = summarize_episode(make_records(), shift_day=10)
    assert summary["pre_shift_total_cost"] == 30
    assert summary["pre_shift_service_level"] == 1
    assert summary["post_shift_7_lost_sales"] == 14
    assert summary["post_shift_14_lost_sales"] == 28
    assert summary["post_shift_30_lost_sales"] == 60
    assert summary["post_shift_7_service_level"] == pytest.approx(0.8)
