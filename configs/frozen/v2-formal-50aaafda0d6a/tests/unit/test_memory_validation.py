import pytest

from shiftmem.memory.confidence import EvidenceOutcome
from shiftmem.memory.validator import DelayedValidator, ValidationPolicy


def daily(day: int, *, demand: int = 10, sales: int = 10, lost_sales: int = 0, total_cost: float = 20.0):
    return {
        "day": day,
        "demand": demand,
        "sales": sales,
        "lost_sales": lost_sales,
        "total_cost": total_cost,
    }


def validator() -> DelayedValidator:
    return DelayedValidator(
        ValidationPolicy(
            service_window=3,
            support_fill_rate=0.95,
            failure_fill_rate=0.8,
            failure_lost_sales=2,
            max_average_cost=50,
        )
    )


def test_validation_waits_for_lead_time_plus_complete_window() -> None:
    pending = validator().register("mem-1", decision_step=4, quoted_lead_time=2)

    result = validator().evaluate(pending, [daily(6), daily(7), daily(8)], current_step=8)

    assert pending.due_step == 9
    assert result.outcome == EvidenceOutcome.PENDING


def test_complete_window_classifies_support_from_public_metrics() -> None:
    evaluator = validator()
    pending = evaluator.register("mem-1", decision_step=4, quoted_lead_time=2)

    result = evaluator.evaluate(
        pending, [daily(6), daily(7), daily(8)], current_step=9
    )

    assert result.outcome == EvidenceOutcome.SUPPORT
    assert result.metrics == {
        "demand": 30.0,
        "sales": 30.0,
        "lost_sales": 0.0,
        "fill_rate": 1.0,
        "average_cost": 20.0,
    }
    assert "regime_id" not in result.metrics


def test_failure_and_inconclusive_are_distinct() -> None:
    evaluator = validator()
    failed = evaluator.register("failed", 0, 1)
    failure = evaluator.evaluate(
        failed,
        [daily(1, demand=10, sales=5, lost_sales=5), daily(2), daily(3)],
        current_step=4,
    )
    uncertain = evaluator.register("uncertain", 10, 1)
    inconclusive = evaluator.evaluate(
        uncertain,
        [daily(11, demand=10, sales=9, lost_sales=1), daily(12), daily(13)],
        current_step=14,
    )

    assert failure.outcome == EvidenceOutcome.FAILURE
    assert inconclusive.outcome == EvidenceOutcome.INCONCLUSIVE


def test_complete_window_must_be_contiguous_and_cannot_complete_twice() -> None:
    evaluator = validator()
    pending = evaluator.register("mem-1", 4, 2)
    with pytest.raises(ValueError, match="contiguous"):
        evaluator.evaluate(pending, [daily(6), daily(8)], current_step=9)

    evaluator.evaluate(pending, [daily(6), daily(7), daily(8)], current_step=9)
    with pytest.raises(ValueError, match="already completed"):
        evaluator.evaluate(pending, [daily(6), daily(7), daily(8)], current_step=10)


def test_registration_rejects_invalid_timing() -> None:
    evaluator = validator()
    with pytest.raises(ValueError, match="quoted_lead_time"):
        evaluator.register("mem-1", 0, -1)
