from shiftmem.evaluation.metrics import (
    post_shift_cumulative_regret,
    recovery_time,
)


def records(costs: list[float]) -> list[dict]:
    return [{"day": day, "total_cost": cost} for day, cost in enumerate(costs)]


def test_post_shift_regret_uses_fixed_completed_day_window() -> None:
    agent = records([1, 1, 4, 4, 4, 100])
    oracle = records([1, 1, 2, 2, 2, 0])

    assert post_shift_cumulative_regret(agent, oracle, shift_day=2, window=3) == 6


def test_recovery_reports_first_sustained_rolling_window() -> None:
    result = recovery_time(
        records([10.0] * 20),
        records([10.0] * 20),
        shift_day=2,
        rolling_window=3,
        sustain_days=2,
    )

    assert result == {
        "recovered": True,
        "recovery_day": 4,
        "recovery_time": 2,
        "censored_at": None,
    }


def test_recovery_is_right_censored_when_threshold_never_holds() -> None:
    result = recovery_time(
        records([20.0] * 10),
        records([10.0] * 10),
        shift_day=2,
        rolling_window=3,
        sustain_days=2,
    )

    assert result["recovered"] is False
    assert result["recovery_day"] is None
    assert result["censored_at"] == 9
