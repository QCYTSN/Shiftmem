from pathlib import Path

from shiftmem.evaluation.plots import plot_episode


def test_plot_accepts_shift_markers(tmp_path: Path) -> None:
    record = {
        "day": 0,
        "demand": 1,
        "sales": 1,
        "ending_inventory": 1,
        "pipeline_inventory": 0,
        "order_quantity": 0,
        "arrivals": 0,
        "total_cost": 0,
    }
    output = plot_episode([record], tmp_path / "marked.png", shift_days=[0])
    assert output.stat().st_size > 0
