import math

import pytest

from shiftmem.detection.base import ChangeDirection, ChangeSignal
from shiftmem.memory.confidence import ConfidenceUpdater, EvidenceOutcome
from shiftmem.memory.lifecycle import LifecycleManager, LifecyclePolicy
from shiftmem.memory.schemas import ExperienceRecord, MemoryStatus


def experience(**updates) -> ExperienceRecord:
    values = {
        "memory_id": "demand-exp",
        "created_step": 1,
        "text": "Demand experience",
        "variables": ["demand"],
    }
    values.update(updates)
    return ExperienceRecord(**values)


def change(variable: str = "demand") -> ChangeSignal:
    return ChangeSignal(
        detected_step=20,
        variable=variable,
        direction=ChangeDirection.INCREASE,
        statistic=6,
        threshold=5,
        suspected_start=16,
    )


def manager() -> LifecycleManager:
    return LifecycleManager(
        LifecyclePolicy(
            promotion_supports=1,
            promotion_confidence=0.6,
            invalidation_failures=1,
            invalidation_confidence=0.4,
            post_change_failure_weight=2,
        )
    )


def test_change_only_demotes_related_active_record() -> None:
    demand = experience(status=MemoryStatus.ACTIVE)
    lead = experience(
        memory_id="lead-exp",
        status=MemoryStatus.ACTIVE,
        variables=["lead_time"],
    )

    changed = manager().apply_change([demand, lead], change(), step=20)

    assert changed == ["demand-exp"]
    assert demand.status == MemoryStatus.PROBATION
    assert lead.status == MemoryStatus.ACTIVE
    assert demand.audit_events[-1].reason == "related_change"
    assert demand.audit_events[-1].variable == "demand"


def test_support_updates_confidence_and_promotes_probation() -> None:
    record = experience()

    manager().apply_evidence(record, EvidenceOutcome.SUPPORT, step=5)

    assert record.alpha == 2
    assert record.beta == 1
    assert record.support_count == 1
    assert record.status == MemoryStatus.ACTIVE
    assert record.audit_events[-1].reason == "evidence_support"


def test_weighted_post_change_failure_invalidates_probation() -> None:
    record = experience()

    manager().apply_evidence(
        record,
        EvidenceOutcome.FAILURE,
        step=6,
        after_related_change=True,
    )

    assert record.beta == 3
    assert record.failure_count == 1
    assert record.status == MemoryStatus.INVALID
    assert record.audit_events[-1].new_status == MemoryStatus.INVALID


def test_inconclusive_evidence_does_not_change_record() -> None:
    record = experience()
    original = record.model_copy(deep=True)

    manager().apply_evidence(record, EvidenceOutcome.INCONCLUSIVE, step=5)

    assert record == original


def test_dormant_record_reactivates_to_probation() -> None:
    record = experience(status=MemoryStatus.ACTIVE)
    lifecycle = manager()

    lifecycle.mark_dormant(record, step=8, reason="context_absent")
    assert record.status == MemoryStatus.DORMANT
    assert record.dormant_reason == "context_absent"
    lifecycle.reactivate(record, step=12, reason="context_returned")
    assert record.status == MemoryStatus.PROBATION
    assert record.dormant_reason is None


def test_illegal_transition_and_non_chronological_update_are_rejected() -> None:
    record = experience(status=MemoryStatus.INVALID)
    with pytest.raises(ValueError, match="illegal lifecycle transition"):
        manager().reactivate(record, step=5, reason="bad")

    active = experience(status=MemoryStatus.ACTIVE)
    manager().mark_dormant(active, step=8, reason="absent")
    with pytest.raises(ValueError, match="chronological"):
        manager().reactivate(active, step=7, reason="returned")


def test_confidence_updater_validates_weight() -> None:
    updater = ConfidenceUpdater()
    for weight in (0, -1, math.inf, math.nan):
        with pytest.raises(ValueError, match="weight"):
            updater.apply(experience(), EvidenceOutcome.SUPPORT, step=5, weight=weight)


def test_multiple_evidence_updates_may_complete_at_same_step_and_update_utility() -> None:
    record = experience()
    lifecycle = LifecycleManager(
        LifecyclePolicy(promotion_supports=1, promotion_confidence=0.6)
    )

    lifecycle.apply_evidence(record, EvidenceOutcome.SUPPORT, step=5)
    lifecycle.apply_evidence(record, EvidenceOutcome.SUPPORT, step=5)

    assert record.alpha == 3
    assert record.support_count == 2
    assert record.utility == 1.0
    assert [event.step for event in record.audit_events] == [5, 5]
