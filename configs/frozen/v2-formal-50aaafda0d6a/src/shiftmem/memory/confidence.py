"""Deterministic Beta-Bernoulli confidence updates."""

from enum import StrEnum
import math

from .schemas import ExperienceRecord


class EvidenceOutcome(StrEnum):
    PENDING = "pending"
    SUPPORT = "support"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"


class ConfidenceUpdater:
    def apply(
        self,
        record: ExperienceRecord,
        outcome: EvidenceOutcome,
        step: int,
        *,
        weight: float = 1.0,
    ) -> None:
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("weight must be finite and positive")
        if step < record.created_step:
            raise ValueError("validation step cannot precede record creation")
        if record.last_validation_step is not None and step < record.last_validation_step:
            raise ValueError("validation steps must be chronological")
        if outcome == EvidenceOutcome.SUPPORT:
            record.alpha += weight
            record.support_count += 1
        elif outcome == EvidenceOutcome.FAILURE:
            record.beta += weight
            record.failure_count += 1
        else:
            raise ValueError("only support or failure updates confidence")
        record.last_validation_step = step
        evidence_count = record.support_count + record.failure_count
        record.utility = record.support_count / evidence_count
