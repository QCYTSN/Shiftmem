"""Delayed deterministic validation of inventory experiences."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .confidence import EvidenceOutcome


class ValidationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    service_window: int = Field(default=3, ge=1)
    support_fill_rate: float = Field(default=0.95, ge=0, le=1)
    failure_fill_rate: float = Field(default=0.80, ge=0, le=1)
    failure_lost_sales: float = Field(default=1.0, ge=0, allow_inf_nan=False)
    max_average_cost: float = Field(default=100.0, gt=0, allow_inf_nan=False)


class PendingValidation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str = Field(min_length=1)
    decision_step: int = Field(ge=0)
    arrival_step: int = Field(ge=0)
    due_step: int = Field(ge=0)


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str = Field(min_length=1)
    outcome: EvidenceOutcome
    metrics: dict[str, float] = Field(default_factory=dict)
    reason: str = Field(min_length=1)


class DelayedValidator:
    def __init__(self, policy: ValidationPolicy | None = None) -> None:
        self.policy = policy or ValidationPolicy()
        self._registered: set[str] = set()
        self._completed: set[str] = set()

    def register(
        self, memory_id: str, decision_step: int, quoted_lead_time: int
    ) -> PendingValidation:
        if decision_step < 0:
            raise ValueError("decision_step must be non-negative")
        if quoted_lead_time < 0:
            raise ValueError("quoted_lead_time must be non-negative")
        if memory_id in self._registered:
            raise ValueError(f"validation already registered: {memory_id}")
        arrival_step = decision_step + quoted_lead_time
        pending = PendingValidation(
            memory_id=memory_id,
            decision_step=decision_step,
            arrival_step=arrival_step,
            due_step=arrival_step + self.policy.service_window,
        )
        self._registered.add(memory_id)
        return pending

    def evaluate(
        self,
        pending: PendingValidation,
        records: list[dict[str, Any]],
        *,
        current_step: int,
    ) -> ValidationResult:
        if pending.memory_id in self._completed:
            raise ValueError(f"validation already completed: {pending.memory_id}")
        if current_step < pending.due_step:
            return ValidationResult(
                memory_id=pending.memory_id,
                outcome=EvidenceOutcome.PENDING,
                reason="validation window is incomplete",
            )

        expected_days = list(range(pending.arrival_step, pending.due_step))
        by_day = {
            int(record["day"]): record
            for record in records
            if "day" in record and pending.arrival_step <= int(record["day"]) < pending.due_step
        }
        if sorted(by_day) != expected_days:
            raise ValueError("validation records must form a contiguous complete window")
        window = [by_day[day] for day in expected_days]
        required = {"demand", "sales", "lost_sales", "total_cost"}
        if any(not required.issubset(record) for record in window):
            raise ValueError("validation records are missing public outcome fields")

        demand = float(sum(record["demand"] for record in window))
        sales = float(sum(record["sales"] for record in window))
        lost_sales = float(sum(record["lost_sales"] for record in window))
        average_cost = float(
            sum(record["total_cost"] for record in window) / len(window)
        )
        fill_rate = sales / demand if demand > 0 else 1.0
        metrics = {
            "demand": demand,
            "sales": sales,
            "lost_sales": lost_sales,
            "fill_rate": fill_rate,
            "average_cost": average_cost,
        }
        if (
            fill_rate <= self.policy.failure_fill_rate
            or lost_sales >= self.policy.failure_lost_sales
        ):
            outcome = EvidenceOutcome.FAILURE
            reason = "service criteria failed"
        elif (
            fill_rate >= self.policy.support_fill_rate
            and lost_sales == 0
            and average_cost <= self.policy.max_average_cost
        ):
            outcome = EvidenceOutcome.SUPPORT
            reason = "service and cost criteria satisfied"
        else:
            outcome = EvidenceOutcome.INCONCLUSIVE
            reason = "outcome falls between support and failure criteria"
        self._completed.add(pending.memory_id)
        return ValidationResult(
            memory_id=pending.memory_id,
            outcome=outcome,
            metrics=metrics,
            reason=reason,
        )
