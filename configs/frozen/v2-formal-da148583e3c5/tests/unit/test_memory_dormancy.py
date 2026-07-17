from shiftmem.memory.schemas import (
    ApplicabilityCondition,
    ExperienceRecord,
    MemoryStatus,
)
from shiftmem.memory.shiftmem import ShiftMemory, ShiftMemoryConfig


def conditioned(status: MemoryStatus = MemoryStatus.ACTIVE) -> ExperienceRecord:
    return ExperienceRecord(
        memory_id="seasonal",
        created_step=0,
        text="high season inventory protection",
        variables=["demand"],
        status=status,
        conditions=[ApplicabilityCondition(field="season", operator="eq", value="high")],
    )


def test_consecutive_misses_mark_record_dormant_at_patience() -> None:
    memory = ShiftMemory(ShiftMemoryConfig(dormancy_patience=2))
    memory.import_experience(conditioned())
    assert memory.retrieve('{"season":"low"}', step=1, top_k=1) == []
    assert memory.get("seasonal").status == MemoryStatus.ACTIVE
    memory.retrieve('{"season":"low"}', step=2, top_k=1)
    record = memory.get("seasonal")
    assert record.status == MemoryStatus.DORMANT
    assert record.consecutive_mismatches == 2
    assert record.audit_events[-1].reason == "context_absent"


def test_match_resets_miss_count_and_duplicate_step_counts_once() -> None:
    memory = ShiftMemory(ShiftMemoryConfig(dormancy_patience=3))
    memory.import_experience(conditioned())
    memory.retrieve('{"season":"low"}', step=1, top_k=1)
    memory.retrieve('{"season":"low"}', step=1, top_k=1)
    assert memory.get("seasonal").consecutive_mismatches == 1
    memory.retrieve('{"season":"high"}', step=2, top_k=1)
    assert memory.get("seasonal").consecutive_mismatches == 0


def test_conditionless_record_is_exempt() -> None:
    memory = ShiftMemory(ShiftMemoryConfig(dormancy_patience=1))
    memory.import_experience(
        ExperienceRecord(
            memory_id="general", created_step=0, text="general advice", status=MemoryStatus.ACTIVE
        )
    )
    assert memory.retrieve("{}", step=1, top_k=1)[0].memory_id == "general"
    assert memory.get("general").consecutive_mismatches == 0


def test_first_returning_match_reactivates_and_is_retrievable() -> None:
    memory = ShiftMemory(ShiftMemoryConfig(dormancy_patience=1))
    memory.import_experience(conditioned())
    memory.retrieve('{"season":"low"}', step=1, top_k=1)
    assert memory.retrieve('{"season":"low"}', step=2, top_k=1) == []
    results = memory.retrieve('{"season":"high"}', step=3, top_k=1)
    record = memory.get("seasonal")
    assert [item.memory_id for item in results] == ["seasonal"]
    assert record.status == MemoryStatus.PROBATION
    assert record.consecutive_mismatches == 0
    assert record.audit_events[-1].reason == "context_returned"


def test_audit_summary_exposes_applicability_state() -> None:
    memory = ShiftMemory(ShiftMemoryConfig(dormancy_patience=2))
    memory.import_experience(conditioned())
    memory.retrieve('{"season":"low"}', step=1, top_k=1)
    row = memory.audit_summary()["records"][0]
    assert row["consecutive_mismatches"] == 1
    assert row["last_condition_check_step"] == 1
