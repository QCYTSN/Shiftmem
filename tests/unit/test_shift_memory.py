import pytest

from shiftmem.detection.base import ChangeSignal
from shiftmem.memory.confidence import EvidenceOutcome
from shiftmem.memory.lifecycle import LifecyclePolicy
from shiftmem.memory.schemas import ExperienceRecord, MemoryRecord, MemoryStatus
from shiftmem.memory.shiftmem import ShiftMemory, ShiftMemoryConfig
from shiftmem.memory.validator import ValidationResult


def active_experience() -> ExperienceRecord:
    return ExperienceRecord(
        memory_id="demand-exp",
        created_step=1,
        text="rising demand requires protection",
        variables=["demand"],
        status=MemoryStatus.ACTIVE,
        alpha=3,
        beta=1,
    )


def test_shift_memory_closes_detection_lifecycle_and_retrieval_loop() -> None:
    memory = ShiftMemory(
        config=ShiftMemoryConfig(
            detector_min_samples=4,
            detector_delta=0.01,
            detector_threshold=1,
        ),
        lifecycle_policy=LifecyclePolicy(
            promotion_supports=1,
            promotion_confidence=0.6,
            invalidation_failures=1,
            invalidation_confidence=0.5,
            post_change_failure_weight=2,
        ),
    )
    memory.import_experience(active_experience())
    signals: list[ChangeSignal] = []
    for step, value in enumerate([5, 5, 5, 5, 12, 12]):
        signal = memory.observe_signal("demand", value, step)
        if signal:
            signals.append(signal)

    assert signals
    assert memory.get("demand-exp").status == MemoryStatus.PROBATION

    memory.apply_validation(
        "demand-exp",
        ValidationResult(
            memory_id="demand-exp",
            outcome=EvidenceOutcome.FAILURE,
            metrics={"fill_rate": 0.5},
            reason="service criteria failed",
        ),
        step=7,
        after_related_change=True,
    )

    assert memory.get("demand-exp").status == MemoryStatus.INVALID
    assert memory.audit("demand-exp")[-1].step == 7
    assert memory.retrieve("demand", step=7, top_k=5) == []


def test_registered_decision_extracts_after_delayed_public_window() -> None:
    memory = ShiftMemory(
        config=ShiftMemoryConfig(
            validation_service_window=2,
            support_fill_rate=0.95,
            max_average_cost=50,
        ),
        lifecycle_policy=LifecyclePolicy(
            promotion_supports=1,
            promotion_confidence=0.6,
        ),
    )
    observation = {
        "day": 0,
        "inventory": 10,
        "pipeline_inventory": 0,
        "quoted_lead_time": 1,
        "last_demand": 0,
        "last_sales": 0,
        "costs": {"purchase": 1, "holding": 0.2, "stockout": 5},
        "recent_history": [],
    }
    memory.register_decision(
        "episode", 0, observation, {"order_quantity": 10, "supplier_id": "standard"}
    )
    memory.observe_outcome(
        {"day": 1, "demand": 10, "sales": 10, "lost_sales": 0, "total_cost": 20}
    )
    assert memory.experience_count == 0
    memory.observe_outcome(
        {"day": 2, "demand": 10, "sales": 10, "lost_sales": 0, "total_cost": 20}
    )

    record = memory.get("exp-episode-0")
    assert record.status == MemoryStatus.ACTIVE
    assert record.support_count == 1
    serialized = record.model_dump_json()
    assert "regime_id" not in serialized
    assert "oracle" not in serialized


def test_shift_memory_agent_interface_returns_memory_records() -> None:
    memory = ShiftMemory()
    memory.import_experience(active_experience())

    records = memory.retrieve('{"day": 3, "inventory": 10}', step=3, top_k=1)

    assert records[0].memory_id == "demand-exp"
    assert records[0].payload["status"] == "active"


def test_used_memory_receives_delayed_evidence_and_can_promote() -> None:
    memory = ShiftMemory(
        config=ShiftMemoryConfig(validation_service_window=2),
        lifecycle_policy=LifecyclePolicy(
            promotion_supports=1,
            promotion_confidence=0.6,
        ),
    )
    probation = active_experience().model_copy(
        update={
            "status": MemoryStatus.PROBATION,
            "alpha": 1.0,
            "beta": 1.0,
            "support_count": 0,
        }
    )
    memory.import_experience(probation)
    observation = {
        "day": 0,
        "inventory": 10,
        "pipeline_inventory": 0,
        "quoted_lead_time": 1,
        "last_demand": 0,
        "last_sales": 0,
        "costs": {"purchase": 1, "holding": 0.2, "stockout": 5},
        "recent_history": [],
    }
    memory.register_decision(
        "episode",
        0,
        observation,
        {"order_quantity": 10, "supplier_id": "standard"},
        used_memory_ids=["demand-exp"],
    )

    for day in (1, 2):
        memory.observe_outcome(
            {
                "day": day,
                "demand": 10,
                "sales": 10,
                "lost_sales": 0,
                "total_cost": 20,
            }
        )

    updated = memory.get("demand-exp")
    assert updated.status == MemoryStatus.ACTIVE
    assert updated.support_count == 1
    assert updated.audit_events[-1].reason == "evidence_support"


def test_controlled_import_rejects_hidden_payload_and_audit_records_config() -> None:
    memory = ShiftMemory(config=ShiftMemoryConfig(detector_threshold=7))

    with pytest.raises(ValueError, match="forbidden public field"):
        memory.add(
            MemoryRecord(
                memory_id="hidden",
                step=1,
                text="hidden state",
                payload={"regime_id": "high"},
            )
        )

    summary = memory.audit_summary()
    assert summary["config"]["detector_threshold"] == 7
    assert summary["lifecycle_policy"]["promotion_supports"] == 2
    assert summary["retrieval_weights"]["semantic"] == 1.0
