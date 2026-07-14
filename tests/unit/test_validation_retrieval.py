from scripts.run_validation_retrieval import aggregate_rows, estimate_call_count


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
