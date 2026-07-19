"""Tests for v2 strategy-revision experience extraction and reuse attribution."""

import pytest

from shiftmem.memory.confidence import EvidenceOutcome
from shiftmem.memory.extractor import ExperienceExtractor
from shiftmem.memory.reuse import ReuseAttribution, classify_reuse
from shiftmem.memory.validator import ValidationResult


def _observation():
    return {
        "day": 5,
        "inventory": 40,
        "pipeline_inventory": 10,
        "quoted_lead_time": 2,
        "recent_history": [],
    }


def _revision():
    return {
        "trigger": "periodic",
        "previous": {"forecast_window": 14, "safety_stock_multiplier": 1.2, "lead_time_buffer": 1},
        "proposed": {"forecast_window": 10, "safety_stock_multiplier": 1.5, "lead_time_buffer": 2},
    }


def _support_validation():
    return ValidationResult(
        memory_id="exp-ep-5",
        outcome=EvidenceOutcome.SUPPORT,
        metrics={"fill_rate": 0.98, "average_cost": 10.0, "lost_sales": 0.0},
        reason="service and cost criteria satisfied",
    )


def test_strategy_experience_unit_is_a_revision_not_a_day():
    extractor = ExperienceExtractor()
    record = extractor.extract_strategy_revision(
        episode_id="ep",
        review_step=5,
        observation=_observation(),
        revision=_revision(),
        validation=_support_validation(),
    )
    payload = record.payload
    assert "revision" in payload
    assert payload["revision"]["proposed"]["safety_stock_multiplier"] == 1.5
    # The recorded unit references the review, not a single order quantity.
    assert "order_quantity" not in payload
    assert record.memory_id == "exp-ep-5"


def test_strategy_extraction_rejects_hidden_fields():
    extractor = ExperienceExtractor()
    leaky = _observation()
    leaky["demand_mean"] = 999
    with pytest.raises(ValueError):
        extractor.extract_strategy_revision(
            episode_id="ep",
            review_step=5,
            observation=leaky,
            revision=_revision(),
            validation=_support_validation(),
        )


def test_strategy_extraction_requires_completed_validation():
    extractor = ExperienceExtractor()
    pending = ValidationResult(
        memory_id="exp-ep-5", outcome=EvidenceOutcome.PENDING, reason="incomplete"
    )
    with pytest.raises(ValueError):
        extractor.extract_strategy_revision(
            episode_id="ep",
            review_step=5,
            observation=_observation(),
            revision=_revision(),
            validation=pending,
        )


def test_reuse_counts_only_supplied_cited_and_accepted():
    result = classify_reuse(
        supplied_ids=["mem-a", "mem-b"],
        cited_ids=["mem-a"],
        proposal_accepted=True,
    )
    assert isinstance(result, ReuseAttribution)
    assert result.reused == ["mem-a"]
    assert result.retrieved_not_cited == ["mem-b"]
    assert result.cited_but_rejected == []


def test_citation_in_rejected_proposal_is_not_reuse():
    result = classify_reuse(
        supplied_ids=["mem-a"],
        cited_ids=["mem-a"],
        proposal_accepted=False,
    )
    assert result.reused == []
    assert result.cited_but_rejected == ["mem-a"]


def test_retrieval_without_citation_reported_separately():
    result = classify_reuse(
        supplied_ids=["mem-a", "mem-b", "mem-c"],
        cited_ids=[],
        proposal_accepted=True,
    )
    assert result.reused == []
    assert set(result.retrieved_not_cited) == {"mem-a", "mem-b", "mem-c"}
