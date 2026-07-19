"""Experience lifecycle and confidence transitions."""

from pydantic import BaseModel, ConfigDict, Field

from shiftmem.detection.base import ChangeSignal

from .confidence import ConfidenceUpdater, EvidenceOutcome
from .schemas import AuditEvent, ExperienceRecord, MemoryStatus


class LifecyclePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    promotion_supports: int = Field(default=2, ge=1)
    promotion_confidence: float = Field(default=0.65, gt=0, lt=1)
    invalidation_failures: int = Field(default=2, ge=1)
    invalidation_confidence: float = Field(default=0.35, gt=0, lt=1)
    post_change_failure_weight: float = Field(
        default=2.0, ge=1, allow_inf_nan=False
    )


class LifecycleManager:
    _ALLOWED = {
        MemoryStatus.PROBATION: {
            MemoryStatus.ACTIVE,
            MemoryStatus.DORMANT,
            MemoryStatus.INVALID,
        },
        MemoryStatus.ACTIVE: {MemoryStatus.PROBATION, MemoryStatus.DORMANT},
        MemoryStatus.DORMANT: {MemoryStatus.PROBATION},
        MemoryStatus.INVALID: set(),
    }

    def __init__(
        self,
        policy: LifecyclePolicy | None = None,
        updater: ConfidenceUpdater | None = None,
    ) -> None:
        self.policy = policy or LifecyclePolicy()
        self.updater = updater or ConfidenceUpdater()

    @staticmethod
    def _validate_step(record: ExperienceRecord, step: int) -> None:
        if step < record.created_step:
            raise ValueError("event step cannot precede record creation")
        if record.audit_events and step < record.audit_events[-1].step:
            raise ValueError("audit events must be chronological")

    def _transition(
        self,
        record: ExperienceRecord,
        new_status: MemoryStatus,
        step: int,
        reason: str,
        variable: str | None = None,
    ) -> None:
        self._validate_step(record, step)
        old_status = record.status
        if new_status not in self._ALLOWED[old_status]:
            raise ValueError(
                f"illegal lifecycle transition: {old_status.value} -> {new_status.value}"
            )
        record.status = new_status
        record.audit_events.append(
            AuditEvent(
                step=step,
                old_status=old_status,
                new_status=new_status,
                reason=reason,
                variable=variable,
            )
        )

    def apply_evidence(
        self,
        record: ExperienceRecord,
        outcome: EvidenceOutcome,
        step: int,
        *,
        after_related_change: bool = False,
    ) -> None:
        if outcome == EvidenceOutcome.INCONCLUSIVE:
            return
        if outcome not in {EvidenceOutcome.SUPPORT, EvidenceOutcome.FAILURE}:
            raise ValueError("pending evidence cannot update lifecycle")
        if record.status in {MemoryStatus.DORMANT, MemoryStatus.INVALID}:
            raise ValueError(f"cannot validate {record.status.value} experience")
        self._validate_step(record, step)
        old_status = record.status
        weight = (
            self.policy.post_change_failure_weight
            if outcome == EvidenceOutcome.FAILURE and after_related_change
            else 1.0
        )
        self.updater.apply(record, outcome, step, weight=weight)

        new_status = old_status
        if old_status == MemoryStatus.PROBATION:
            if (
                outcome == EvidenceOutcome.SUPPORT
                and record.support_count >= self.policy.promotion_supports
                and record.confidence >= self.policy.promotion_confidence
            ):
                new_status = MemoryStatus.ACTIVE
            elif (
                outcome == EvidenceOutcome.FAILURE
                and record.failure_count >= self.policy.invalidation_failures
                and record.confidence <= self.policy.invalidation_confidence
            ):
                new_status = MemoryStatus.INVALID
        elif old_status == MemoryStatus.ACTIVE and outcome == EvidenceOutcome.FAILURE:
            new_status = MemoryStatus.PROBATION

        if new_status != old_status:
            record.status = new_status
        record.audit_events.append(
            AuditEvent(
                step=step,
                old_status=old_status,
                new_status=new_status,
                reason=f"evidence_{outcome.value}",
            )
        )

    def apply_change(
        self,
        records: list[ExperienceRecord],
        signal: ChangeSignal,
        step: int,
    ) -> list[str]:
        changed: list[str] = []
        for record in records:
            if record.status == MemoryStatus.ACTIVE and signal.variable in record.variables:
                self._transition(
                    record,
                    MemoryStatus.PROBATION,
                    step,
                    "related_change",
                    signal.variable,
                )
                changed.append(record.memory_id)
        return changed

    def mark_dormant(
        self, record: ExperienceRecord, step: int, reason: str
    ) -> None:
        self._transition(record, MemoryStatus.DORMANT, step, reason)
        record.dormant_reason = reason

    def reactivate(
        self, record: ExperienceRecord, step: int, reason: str
    ) -> None:
        self._transition(record, MemoryStatus.PROBATION, step, reason)
        record.dormant_reason = None
