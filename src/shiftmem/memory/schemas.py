"""Structured schemas shared by memory baselines and ShiftMem."""

from enum import StrEnum
import operator as comparison
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=1)
    step: int = Field(ge=0)
    text: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)


class MemoryStatus(StrEnum):
    """Lifecycle states retained in the experience audit trail."""

    PROBATION = "probation"
    ACTIVE = "active"
    DORMANT = "dormant"
    INVALID = "invalid"


class ConditionOperator(StrEnum):
    EQ = "eq"
    GE = "ge"
    GT = "gt"
    LE = "le"
    LT = "lt"
    IN = "in"


class ApplicabilityCondition(BaseModel):
    """A typed predicate over one public observation field."""

    model_config = ConfigDict(extra="forbid")

    field: str = Field(min_length=1)
    operator: ConditionOperator
    value: Any

    @model_validator(mode="after")
    def validate_operand(self) -> "ApplicabilityCondition":
        if self.operator == ConditionOperator.IN and not isinstance(
            self.value, (list, tuple, set)
        ):
            raise ValueError("in condition value must be a collection")
        return self

    def matches(self, observation: dict[str, Any]) -> bool:
        if self.field not in observation:
            return False
        observed = observation[self.field]
        if self.operator == ConditionOperator.IN:
            return observed in self.value
        functions = {
            ConditionOperator.EQ: comparison.eq,
            ConditionOperator.GE: comparison.ge,
            ConditionOperator.GT: comparison.gt,
            ConditionOperator.LE: comparison.le,
            ConditionOperator.LT: comparison.lt,
        }
        try:
            return bool(functions[self.operator](observed, self.value))
        except TypeError:
            return False


class AuditEvent(BaseModel):
    """One immutable, chronological lifecycle transition."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    step: int = Field(ge=0)
    old_status: MemoryStatus
    new_status: MemoryStatus
    reason: str = Field(min_length=1)
    variable: str | None = None


class ExperienceRecord(BaseModel):
    """Canonical auditable experience stored by ShiftMem."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    memory_id: str = Field(min_length=1)
    created_step: int = Field(ge=0)
    text: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    conditions: list[ApplicabilityCondition] = Field(default_factory=list)
    status: MemoryStatus = MemoryStatus.PROBATION
    alpha: float = Field(default=1.0, gt=0, allow_inf_nan=False)
    beta: float = Field(default=1.0, gt=0, allow_inf_nan=False)
    support_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    last_validation_step: int | None = Field(default=None, ge=0)
    last_applicable_step: int | None = Field(default=None, ge=0)
    dormant_reason: str | None = None
    utility: float = Field(default=0.0, ge=0, le=1, allow_inf_nan=False)
    payload: dict[str, Any] = Field(default_factory=dict)
    audit_events: list[AuditEvent] = Field(default_factory=list)

    @field_validator("variables")
    @classmethod
    def variables_are_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("variables must be unique")
        if any(not item for item in value):
            raise ValueError("variables must be non-empty")
        return value

    @model_validator(mode="after")
    def events_are_chronological(self) -> "ExperienceRecord":
        steps = [event.step for event in self.audit_events]
        if steps != sorted(steps):
            raise ValueError("audit events must be chronological")
        return self

    @property
    def confidence(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    def is_applicable(self, observation: dict[str, Any]) -> bool:
        return all(condition.matches(observation) for condition in self.conditions)

    def to_memory_record(self) -> MemoryRecord:
        metadata = {
            **self.payload,
            "status": self.status.value,
            "confidence": self.confidence,
            "created_step": self.created_step,
        }
        return MemoryRecord(
            memory_id=self.memory_id,
            step=self.created_step,
            text=self.text,
            variables=list(self.variables),
            payload=metadata,
        )
