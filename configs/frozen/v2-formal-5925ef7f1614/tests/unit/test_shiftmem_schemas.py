import math

import pytest
from pydantic import ValidationError

from shiftmem.memory.schemas import (
    ApplicabilityCondition,
    AuditEvent,
    ExperienceRecord,
    MemoryStatus,
)
from shiftmem.memory.store import ExperienceStore


def experience(**updates) -> ExperienceRecord:
    values = {
        "memory_id": "exp-1",
        "created_step": 4,
        "text": "Order conservatively when inventory is low.",
        "variables": ["demand", "inventory"],
        "conditions": [],
    }
    values.update(updates)
    return ExperienceRecord(**values)


def test_experience_confidence_predicate_and_conversion() -> None:
    record = experience(
        alpha=3,
        beta=1,
        conditions=[
            ApplicabilityCondition(field="inventory", operator="le", value=20)
        ],
    )

    assert record.confidence == 0.75
    assert record.is_applicable({"inventory": 20})
    assert not record.is_applicable({"inventory": 21})
    converted = record.to_memory_record()
    assert converted.step == 4
    assert converted.payload["status"] == "probation"
    assert converted.payload["confidence"] == 0.75


@pytest.mark.parametrize(
    ("operator", "value", "observed", "matches"),
    [
        ("eq", "high", "high", True),
        ("ge", 10, 10, True),
        ("gt", 10, 10, False),
        ("le", 10, 9, True),
        ("lt", 10, 10, False),
        ("in", ["poisson", "negative_binomial"], "poisson", True),
    ],
)
def test_applicability_condition_operators(
    operator: str, value: object, observed: object, matches: bool
) -> None:
    condition = ApplicabilityCondition(
        field="signal", operator=operator, value=value
    )
    assert condition.matches({"signal": observed}) is matches
    assert not condition.matches({})


def test_experience_rejects_invalid_evidence_and_event_order() -> None:
    with pytest.raises(ValidationError):
        experience(alpha=math.inf)
    with pytest.raises(ValidationError):
        experience(alpha=0)
    with pytest.raises(ValidationError):
        experience(variables=["demand", "demand"])
    with pytest.raises(ValidationError):
        experience(
            audit_events=[
                AuditEvent(
                    step=5,
                    old_status=MemoryStatus.PROBATION,
                    new_status=MemoryStatus.ACTIVE,
                    reason="supported",
                ),
                AuditEvent(
                    step=4,
                    old_status=MemoryStatus.ACTIVE,
                    new_status=MemoryStatus.PROBATION,
                    reason="change",
                ),
            ]
        )


def test_store_accepts_identical_replay_and_rejects_conflicting_duplicate() -> None:
    store = ExperienceStore()
    first = experience()
    store.add(first)
    store.add(first.model_copy(deep=True))

    assert store.get("exp-1") == first
    assert store.all() == [first]
    with pytest.raises(ValueError, match="duplicate memory_id"):
        store.add(experience(text="Different rule."))


def test_store_returns_defensive_record_copies() -> None:
    store = ExperienceStore()
    store.add(experience())

    loaded = store.get("exp-1")
    loaded.text = "mutated"

    assert store.get("exp-1").text != "mutated"
