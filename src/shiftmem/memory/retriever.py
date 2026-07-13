"""Two-stage condition-aware experience retrieval."""

import math
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from .schemas import ExperienceRecord, MemoryStatus
from .store import lexical_cosine


class SemanticScorer(Protocol):
    def score(self, query: str, text: str) -> float: ...


class LexicalSemanticScorer:
    def score(self, query: str, text: str) -> float:
        return lexical_cosine(query, text)


class RetrievalWeights(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic: float = Field(default=1.0, ge=0, allow_inf_nan=False)
    confidence: float = Field(default=0.5, ge=0, allow_inf_nan=False)
    recency: float = Field(default=0.25, ge=0, allow_inf_nan=False)
    utility: float = Field(default=0.25, ge=0, allow_inf_nan=False)
    probation_penalty: float = Field(default=0.25, ge=0, allow_inf_nan=False)
    changed_variable_penalty: float = Field(
        default=0.5, ge=0, allow_inf_nan=False
    )
    recency_half_life: float = Field(default=30.0, gt=0, allow_inf_nan=False)


class RetrievalScore(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic: float = Field(allow_inf_nan=False)
    confidence: float = Field(allow_inf_nan=False)
    recency: float = Field(allow_inf_nan=False)
    utility: float = Field(allow_inf_nan=False)
    shift_penalty: float = Field(ge=0, allow_inf_nan=False)
    total: float = Field(allow_inf_nan=False)


class RetrievedExperience(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record: ExperienceRecord
    score: RetrievalScore


class ConditionalRetriever:
    def __init__(
        self,
        weights: RetrievalWeights | None = None,
        scorer: SemanticScorer | None = None,
    ) -> None:
        self.weights = weights or RetrievalWeights()
        self.scorer = scorer or LexicalSemanticScorer()

    def retrieve(
        self,
        records: list[ExperienceRecord],
        query: str,
        observation: dict,
        step: int,
        top_k: int,
        *,
        variables: set[str] | None = None,
        recently_changed_variables: set[str] | None = None,
    ) -> list[RetrievedExperience]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        if step < 0:
            raise ValueError("step must be non-negative")
        changed = recently_changed_variables or set()
        eligible = [
            record
            for record in records
            if record.status in {MemoryStatus.ACTIVE, MemoryStatus.PROBATION}
            and record.is_applicable(observation)
            and (variables is None or bool(set(record.variables) & variables))
        ]
        ranked: list[RetrievedExperience] = []
        for record in eligible:
            raw_semantic = self.scorer.score(query, record.text)
            if not math.isfinite(raw_semantic) or not 0 <= raw_semantic <= 1:
                raise ValueError("semantic scorer must return a finite value in [0, 1]")
            age = max(0, step - record.created_step)
            semantic = self.weights.semantic * raw_semantic
            confidence = self.weights.confidence * record.confidence
            recency = self.weights.recency * 0.5 ** (
                age / self.weights.recency_half_life
            )
            utility = self.weights.utility * record.utility
            penalty = 0.0
            if record.status == MemoryStatus.PROBATION:
                penalty += self.weights.probation_penalty
            if set(record.variables) & changed:
                penalty += self.weights.changed_variable_penalty
            score = RetrievalScore(
                semantic=semantic,
                confidence=confidence,
                recency=recency,
                utility=utility,
                shift_penalty=penalty,
                total=semantic + confidence + recency + utility - penalty,
            )
            ranked.append(
                RetrievedExperience(
                    record=record.model_copy(deep=True),
                    score=score,
                )
            )
        ranked.sort(
            key=lambda item: (
                -item.score.total,
                -item.record.created_step,
                item.record.memory_id,
            )
        )
        return ranked[:top_k]
