import pytest

from shiftmem.memory.confidence import EvidenceOutcome
from shiftmem.memory.extractor import ExperienceExtractor
from shiftmem.memory.validator import ValidationResult


def validation() -> ValidationResult:
    return ValidationResult(
        memory_id="pending-1",
        outcome=EvidenceOutcome.SUPPORT,
        metrics={"fill_rate": 1.0, "lost_sales": 0.0, "average_cost": 20.0},
        reason="service and cost criteria satisfied",
    )


def observation() -> dict:
    return {
        "day": 4,
        "inventory": 12,
        "pipeline_inventory": 5,
        "quoted_lead_time": 2,
        "last_demand": 10,
        "last_sales": 10,
        "costs": {"purchase": 1.0, "holding": 0.2, "stockout": 5.0},
        "recent_history": [],
    }


def test_extractor_replay_is_stable_and_public_only() -> None:
    extractor = ExperienceExtractor()
    first = extractor.extract(
        "ep-7", 4, observation(), {"order_quantity": 8, "supplier_id": "standard"}, validation()
    )
    second = extractor.extract(
        "ep-7", 4, observation(), {"order_quantity": 8, "supplier_id": "standard"}, validation()
    )

    assert first == second
    assert first.memory_id == "exp-ep-7-4"
    assert first.variables == ["demand", "inventory", "lead_time"]
    assert "order 8" in first.text.lower()
    assert first.payload["validation"]["fill_rate"] == 1.0
    serialized = first.model_dump_json()
    for forbidden in ("regime_id", "demand_mean", "future_fill", "oracle"):
        assert forbidden not in serialized


def test_extractor_adds_public_applicability_conditions() -> None:
    record = ExperienceExtractor().extract(
        "ep", 4, observation(), {"order_quantity": 8, "supplier_id": "standard"}, validation()
    )

    assert record.is_applicable(observation())
    changed = {**observation(), "quoted_lead_time": 5}
    assert not record.is_applicable(changed)


@pytest.mark.parametrize("forbidden", ["regime_id", "demand_mean", "future_fill", "oracle_context"])
def test_extractor_rejects_hidden_source_fields(forbidden: str) -> None:
    source = {**observation(), forbidden: "secret"}
    with pytest.raises(ValueError, match="forbidden public field"):
        ExperienceExtractor().extract(
            "ep", 4, source, {"order_quantity": 8, "supplier_id": "standard"}, validation()
        )


def test_extractor_requires_completed_validation() -> None:
    pending = validation().model_copy(update={"outcome": EvidenceOutcome.PENDING})
    with pytest.raises(ValueError, match="completed validation"):
        ExperienceExtractor().extract(
            "ep", 4, observation(), {"order_quantity": 8, "supplier_id": "standard"}, pending
        )
