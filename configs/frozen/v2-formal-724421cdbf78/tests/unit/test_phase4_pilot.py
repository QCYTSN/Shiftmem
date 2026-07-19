from scripts.run_phase4_pilot import aggregate_pilot, deduplicate_runs, estimate_pilot_calls


def config() -> dict:
    return {
        "seeds": [1, 2],
        "post_shift_days": 30,
        "models": [{"label": "a"}, {"label": "b"}],
        "methods": [{"config_id": "vector"}, {"config_id": "shiftmem"}],
    }


def test_pilot_matrix_is_bounded_to_240_decisions() -> None:
    assert estimate_pilot_calls(config()) == 240


def test_pilot_aggregation_is_paired_by_model_and_seed() -> None:
    runs = [
        {"model": "a", "config_id": "vector", "seed": 1, "cost": 100, "tokens": 10, "fallbacks": 0, "latency_ms": 2, "calls": 1},
        {"model": "a", "config_id": "shiftmem", "seed": 1, "cost": 90, "tokens": 12, "fallbacks": 0, "latency_ms": 3, "calls": 1},
        {"model": "a", "config_id": "vector", "seed": 2, "cost": 120, "tokens": 11, "fallbacks": 1, "latency_ms": 2, "calls": 2},
        {"model": "a", "config_id": "shiftmem", "seed": 2, "cost": 100, "tokens": 13, "fallbacks": 0, "latency_ms": 4, "calls": 1},
    ]
    result = aggregate_pilot(runs, expected_runs=4)
    assert result["complete"] is True
    assert result["models"][0]["mean_regret"] == -15
    assert result["models"][0]["regret_sd"] > 0
    assert result["total_tokens"] == 46
    assert result["total_fallbacks"] == 1
    assert result["total_calls"] == 5


def test_pilot_aggregation_marks_incomplete_matrix() -> None:
    assert aggregate_pilot([], expected_runs=4)["complete"] is False


def test_duplicate_completed_cell_keeps_first_result() -> None:
    runs = [
        {"model": "a", "config_id": "shiftmem", "seed": 1, "cost": 90},
        {"model": "a", "config_id": "shiftmem", "seed": 1, "cost": 10},
    ]
    assert deduplicate_runs(runs) == [runs[0]]
