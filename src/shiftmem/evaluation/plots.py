"""Research plots and diagnostic figures."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_episode(records: Sequence[dict[str, Any]], output_path: str | Path) -> Path:
    """Save a four-panel diagnostic plot for one inventory episode."""
    if not records:
        raise ValueError("cannot plot an empty episode")
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    days = [record["day"] for record in records]
    figure, axes = plt.subplots(4, 1, figsize=(10, 10), sharex=True)
    axes[0].plot(days, [record["demand"] for record in records], label="Demand")
    axes[0].plot(days, [record["sales"] for record in records], label="Sales")
    axes[0].legend()
    axes[0].set_ylabel("Units")
    axes[1].plot(days, [record["ending_inventory"] for record in records], label="Inventory")
    axes[1].plot(days, [record["pipeline_inventory"] for record in records], label="Pipeline")
    axes[1].legend()
    axes[1].set_ylabel("Units")
    axes[2].plot(days, [record["order_quantity"] for record in records], label="Orders")
    axes[2].plot(days, [record["arrivals"] for record in records], label="Arrivals")
    axes[2].legend()
    axes[2].set_ylabel("Units")
    axes[3].plot(days, [record["total_cost"] for record in records], label="Daily cost")
    axes[3].legend()
    axes[3].set_ylabel("Cost")
    axes[3].set_xlabel("Day")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)
    return path
