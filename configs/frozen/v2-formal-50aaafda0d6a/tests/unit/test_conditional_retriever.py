import math

import pytest
from pydantic import ValidationError

from shiftmem.memory.retriever import (
    ConditionalRetriever,
    RetrievalWeights,
)
from shiftmem.memory.schemas import (
    ApplicabilityCondition,
    ExperienceRecord,
    MemoryStatus,
)


def experience(memory_id: str, **updates) -> ExperienceRecord:
    values = {
        "memory_id": memory_id,
        "created_step": 10,
        "text": "rising demand requires inventory protection",
        "variables": ["demand"],
        "status": MemoryStatus.ACTIVE,
        "alpha": 3,
        "beta": 1,
        "utility": 0.8,
    }
    values.update(updates)
    return ExperienceRecord(**values)


def test_hard_filter_excludes_inapplicable_dormant_invalid_and_unrelated() -> None:
    records = [
        experience("active-match"),
        experience("probation-match", status=MemoryStatus.PROBATION),
        experience("dormant", status=MemoryStatus.DORMANT),
        experience("invalid", status=MemoryStatus.INVALID),
        experience(
            "condition-miss",
            conditions=[
                ApplicabilityCondition(field="inventory", operator="le", value=5)
            ],
        ),
        experience("unrelated", variables=["lead_time"]),
    ]

    results = ConditionalRetriever().retrieve(
        records,
        query="rising demand",
        observation={"inventory": 10},
        step=30,
        top_k=5,
        variables={"demand"},
    )

    assert [item.record.memory_id for item in results] == [
        "active-match",
        "probation-match",
    ]


def test_ranking_exposes_weighted_components_and_penalties() -> None:
    results = ConditionalRetriever().retrieve(
        [
            experience("active"),
            experience("probation", status=MemoryStatus.PROBATION),
        ],
        query="rising demand",
        observation={},
        step=20,
        top_k=2,
        recently_changed_variables={"demand"},
    )

    score = results[0].score
    assert score.total == pytest.approx(
        score.semantic
        + score.confidence
        + score.recency
        + score.utility
        - score.shift_penalty
    )
    assert results[1].score.shift_penalty > results[0].score.shift_penalty


def test_deterministic_tie_break_prefers_newer_then_memory_id() -> None:
    records = [
        experience("z-older", created_step=5),
        experience("b-newer", created_step=10),
        experience("a-newer", created_step=10),
    ]

    results = ConditionalRetriever().retrieve(
        records, "demand", {}, step=10, top_k=3
    )

    assert [item.record.memory_id for item in results] == [
        "a-newer",
        "b-newer",
        "z-older",
    ]


def test_injected_semantic_scorer_controls_semantic_component() -> None:
    class ConstantScorer:
        def score(self, query: str, text: str) -> float:
            return 0.25

    weights = RetrievalWeights(
        semantic=2,
        confidence=0,
        recency=0,
        utility=0,
        probation_penalty=0,
        changed_variable_penalty=0,
    )
    result = ConditionalRetriever(weights=weights, scorer=ConstantScorer()).retrieve(
        [experience("one")], "anything", {}, step=10, top_k=1
    )[0]

    assert result.score.semantic == 0.5
    assert result.score.total == 0.5


def test_retrieval_validates_top_k_step_scores_and_weights() -> None:
    retriever = ConditionalRetriever()
    with pytest.raises(ValueError, match="top_k"):
        retriever.retrieve([], "query", {}, step=1, top_k=0)
    with pytest.raises(ValueError, match="step"):
        retriever.retrieve([], "query", {}, step=-1, top_k=1)
    with pytest.raises(ValidationError):
        RetrievalWeights(semantic=math.inf)
