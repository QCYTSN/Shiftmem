"""Facade composing the deterministic ShiftMem memory loop."""

from copy import deepcopy
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from shiftmem.detection.base import ChangeSignal
from shiftmem.detection.page_hinkley import PageHinkleyDetector

from .extractor import ExperienceExtractor, validate_public_data
from .lifecycle import LifecycleManager, LifecyclePolicy
from .retriever import ConditionalRetriever, RetrievalWeights
from .schemas import AuditEvent, ExperienceRecord, MemoryRecord, MemoryStatus
from .store import ExperienceStore
from .validator import (
    DelayedValidator,
    PendingValidation,
    ValidationPolicy,
    ValidationResult,
)


class ShiftMemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detector_min_samples: int = Field(default=10, ge=2)
    detector_delta: float = Field(default=0.05, ge=0, allow_inf_nan=False)
    detector_threshold: float = Field(default=5.0, gt=0, allow_inf_nan=False)
    validation_service_window: int = Field(default=3, ge=1)
    support_fill_rate: float = Field(default=0.95, ge=0, le=1)
    failure_fill_rate: float = Field(default=0.80, ge=0, le=1)
    failure_lost_sales: float = Field(default=1.0, ge=0, allow_inf_nan=False)
    max_average_cost: float = Field(default=100.0, gt=0, allow_inf_nan=False)
    change_penalty_window: int = Field(default=14, ge=0)
    dormancy_patience: int = Field(default=7, ge=1)


class ShiftMemory:
    """Agent-compatible memory plus explicit lifecycle and audit operations."""

    def __init__(
        self,
        config: ShiftMemoryConfig | None = None,
        *,
        lifecycle_policy: LifecyclePolicy | None = None,
        retrieval_weights: RetrievalWeights | None = None,
    ) -> None:
        self.config = config or ShiftMemoryConfig()
        self.store = ExperienceStore()
        self.lifecycle = LifecycleManager(lifecycle_policy)
        self.retriever = ConditionalRetriever(retrieval_weights)
        self.extractor = ExperienceExtractor()
        self.validator = DelayedValidator(
            ValidationPolicy(
                service_window=self.config.validation_service_window,
                support_fill_rate=self.config.support_fill_rate,
                failure_fill_rate=self.config.failure_fill_rate,
                failure_lost_sales=self.config.failure_lost_sales,
                max_average_cost=self.config.max_average_cost,
            )
        )
        self._detectors: dict[str, PageHinkleyDetector] = {}
        self._changed_at: dict[str, int] = {}
        self._changed_memory_ids: set[str] = set()
        self._history: list[dict[str, Any]] = []
        self._pending: dict[str, PendingValidation] = {}
        self._sources: dict[str, dict[str, Any]] = {}

    @property
    def experience_count(self) -> int:
        return len(self.store.all())

    def import_experience(self, record: ExperienceRecord) -> None:
        self.store.add(record)

    def add(self, record: MemoryRecord) -> None:
        """Import a baseline record without inventing validation evidence."""

        validate_public_data(record.payload)
        self.import_experience(
            ExperienceRecord(
                memory_id=record.memory_id,
                created_step=record.step,
                text=record.text,
                variables=list(record.variables),
                payload=deepcopy(record.payload),
            )
        )

    def get(self, memory_id: str) -> ExperienceRecord:
        return self.store.get(memory_id)

    def audit(self, memory_id: str) -> list[AuditEvent]:
        return list(self.store.get(memory_id).audit_events)

    def observe_signal(
        self, variable: str, value: float, step: int
    ) -> ChangeSignal | None:
        detector = self._detectors.setdefault(
            variable,
            PageHinkleyDetector(
                variable,
                min_samples=self.config.detector_min_samples,
                delta=self.config.detector_delta,
                threshold=self.config.detector_threshold,
            ),
        )
        signal = detector.update(float(value), step)
        if signal is None:
            return None
        records = self.store.all()
        changed_ids = self.lifecycle.apply_change(records, signal, step)
        for record in records:
            if record.memory_id in changed_ids:
                self.store.replace(record)
                self._changed_memory_ids.add(record.memory_id)
        self._changed_at[variable] = step
        return signal

    def register_decision(
        self,
        episode_id: str,
        step: int,
        observation: dict[str, Any],
        action: dict[str, Any],
        used_memory_ids: list[str] | None = None,
    ) -> str:
        memory_id = f"exp-{episode_id}-{step}"
        pending = self.validator.register(
            memory_id,
            decision_step=step,
            quoted_lead_time=int(observation["quoted_lead_time"]),
        )
        self._pending[memory_id] = pending
        self._sources[memory_id] = {
            "kind": "new",
            "episode_id": episode_id,
            "step": step,
            "observation": deepcopy(observation),
            "action": deepcopy(action),
        }
        for used_memory_id in used_memory_ids or []:
            self.store.get(used_memory_id)
            validation_id = f"reuse-{used_memory_id}-{step}"
            reuse_pending = self.validator.register(
                validation_id,
                decision_step=step,
                quoted_lead_time=int(observation["quoted_lead_time"]),
            )
            self._pending[validation_id] = reuse_pending
            self._sources[validation_id] = {
                "kind": "reuse",
                "target_memory_id": used_memory_id,
            }
        return memory_id

    def observe_outcome(self, record: dict[str, Any]) -> list[ValidationResult]:
        step = int(record["day"])
        for variable in ("demand", "lost_sales"):
            if variable in record:
                self.observe_signal(variable, float(record[variable]), step)
        self._history.append(deepcopy(record))
        return self.process_validations(current_step=step + 1)

    def process_validations(self, current_step: int) -> list[ValidationResult]:
        completed: list[ValidationResult] = []
        for memory_id, pending in list(self._pending.items()):
            if current_step < pending.due_step:
                continue
            result = self.validator.evaluate(
                pending, self._history, current_step=current_step
            )
            source = self._sources[memory_id]
            if source["kind"] == "new":
                experience = self.extractor.extract(
                    source["episode_id"],
                    source["step"],
                    source["observation"],
                    source["action"],
                    result,
                )
                self.lifecycle.apply_evidence(
                    experience,
                    result.outcome,
                    current_step,
                    after_related_change=False,
                )
                self.store.add(experience)
            else:
                target_id = source["target_memory_id"]
                experience = self.store.get(target_id)
                if experience.status not in {
                    MemoryStatus.DORMANT,
                    MemoryStatus.INVALID,
                }:
                    self.lifecycle.apply_evidence(
                        experience,
                        result.outcome,
                        current_step,
                        after_related_change=target_id
                        in self._changed_memory_ids,
                    )
                    self.store.replace(experience)
                    if experience.status != MemoryStatus.PROBATION:
                        self._changed_memory_ids.discard(target_id)
            del self._pending[memory_id]
            del self._sources[memory_id]
            completed.append(result)
        return completed

    def apply_validation(
        self,
        memory_id: str,
        result: ValidationResult,
        *,
        step: int,
        after_related_change: bool = False,
    ) -> None:
        if result.memory_id != memory_id:
            raise ValueError("validation memory_id does not match target")
        record = self.store.get(memory_id)
        self.lifecycle.apply_evidence(
            record,
            result.outcome,
            step,
            after_related_change=after_related_change,
        )
        self.store.replace(record)

    def retrieve(
        self, query: str, step: int, top_k: int
    ) -> list[MemoryRecord]:
        try:
            parsed = json.loads(query)
            observation = parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            observation = {}
        self._update_applicability(observation, step)
        recent_changes = {
            variable
            for variable, changed_step in self._changed_at.items()
            if step - changed_step <= self.config.change_penalty_window
        }
        results = self.retriever.retrieve(
            self.store.all(),
            query,
            observation,
            step,
            top_k,
            recently_changed_variables=recent_changes,
        )
        return [item.record.to_memory_record() for item in results]

    def _update_applicability(
        self, observation: dict[str, Any], step: int
    ) -> None:
        """Advance condition lifecycle at most once per environment step."""

        for record in self.store.all():
            if (
                not record.conditions
                or record.status == MemoryStatus.INVALID
                or record.last_condition_check_step == step
            ):
                continue
            matched = record.is_applicable(observation)
            record.last_condition_check_step = step
            if matched:
                record.last_applicable_step = step
                record.consecutive_mismatches = 0
                if record.status == MemoryStatus.DORMANT:
                    self.lifecycle.reactivate(
                        record, step=step, reason="context_returned"
                    )
            elif record.status in {MemoryStatus.ACTIVE, MemoryStatus.PROBATION}:
                record.consecutive_mismatches += 1
                if record.consecutive_mismatches >= self.config.dormancy_patience:
                    self.lifecycle.mark_dormant(
                        record, step=step, reason="context_absent"
                    )
            self.store.replace(record)

    def audit_summary(self) -> dict[str, Any]:
        return {
            "config": self.config.model_dump(mode="json"),
            "lifecycle_policy": self.lifecycle.policy.model_dump(mode="json"),
            "retrieval_weights": self.retriever.weights.model_dump(mode="json"),
            "experience_count": self.experience_count,
            "pending_validation_count": len(self._pending),
            "records": [
                record.model_dump(mode="json") for record in self.store.all()
            ],
        }
