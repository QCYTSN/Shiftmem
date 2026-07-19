from pathlib import Path

import pytest

from scripts.run_validation_retrieval import aggregate_rows, estimate_call_count, run_one
from shiftmem.providers.base import ProviderResponse


def test_call_estimate_includes_one_vector_baseline_per_seed() -> None:
    config = {
        "seeds": [1, 2],
        "post_shift_days": 30,
        "retrieval_grid": [{"config_id": "a"}, {"config_id": "b"}, {"config_id": "c"}],
    }
    assert estimate_call_count(config) == 240


def test_aggregate_uses_paired_vector_cost_and_tie_metrics() -> None:
    runs = [
        {"config_id": "vector", "seed": 1, "cost": 100, "invalid_reuse": 0, "tokens": 50},
        {"config_id": "a", "seed": 1, "cost": 90, "invalid_reuse": 1, "tokens": 60},
        {"config_id": "b", "seed": 1, "cost": 110, "invalid_reuse": 0, "tokens": 40},
    ]
    rows = aggregate_rows(runs)
    assert rows == [
        {
            "config_id": "a",
            "post_shift_cumulative_regret_30": -10.0,
            "invalid_reuse": 1,
            "tokens": 60,
            "completed_runs": 1,
        },
        {
            "config_id": "b",
            "post_shift_cumulative_regret_30": 10.0,
            "invalid_reuse": 0,
            "tokens": 40,
            "completed_runs": 1,
        },
    ]


class ContextProvider:
    def __init__(self) -> None:
        self.contexts = []

    def set_decision(self, cell_id: str, day: int) -> None:
        self.contexts.append((cell_id, day))

    def generate(self, request):
        return ProviderResponse(
            text='{"order_quantity":20,"supplier_id":"standard","used_memory_ids":[],"confidence":0.5,"reason":"bounded test"}',
            input_tokens=10,
            output_tokens=5,
            latency_ms=1,
        )


@pytest.mark.parametrize(
    "method",
    ["none", "full_history", "summary", "vector", "time_decay", "shiftmem"],
)
def test_run_one_supports_six_methods_and_sets_decision_context(method: str) -> None:
    provider = ContextProvider()
    config = {"config_id": method}
    if method == "shiftmem":
        config.update(
            {
                "dormancy_patience": 3,
                "detector_min_samples": 10,
                "detector_delta": 0.1,
                "detector_threshold": 48.0,
                "weights": {
                    "semantic": 0.75,
                    "confidence": 0.5,
                    "recency": 1.0,
                    "utility": 0.25,
                    "probation_penalty": 0.25,
                    "changed_variable_penalty": 0.5,
                },
            }
        )

    result = run_one(
        Path("configs/environments/validation_demand_jump.yaml"),
        1000,
        1,
        config,
        "siliconflow",
        "fake",
        provider=provider,
        cell_id=f"cell-{method}",
    )

    assert result["calls"] == 1
    assert provider.contexts == [(f"cell-{method}", 70)]
