"""Deterministic experience extraction from completed decisions."""

from copy import deepcopy
from typing import Any

from .confidence import EvidenceOutcome
from .schemas import ApplicabilityCondition, ExperienceRecord
from .validator import ValidationResult


_FORBIDDEN_FIELDS = {
    "demand_mean",
    "dispersion",
    "future_demand",
    "future_fill",
    "shift_schedule",
    "regime_id",
    "oracle",
    "oracle_context",
}


def _find_forbidden(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            normalized = str(key).lower()
            if normalized in _FORBIDDEN_FIELDS or normalized.startswith("oracle_"):
                return normalized
            found = _find_forbidden(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _find_forbidden(nested)
            if found:
                return found
    return None


def validate_public_data(value: Any) -> None:
    forbidden = _find_forbidden(value)
    if forbidden:
        raise ValueError(f"forbidden public field: {forbidden}")


class ExperienceExtractor:
    def extract(
        self,
        episode_id: str,
        decision_step: int,
        observation: dict[str, Any],
        action: dict[str, Any],
        validation: ValidationResult,
    ) -> ExperienceRecord:
        if not episode_id or any(character.isspace() for character in episode_id):
            raise ValueError("episode_id must be non-empty and contain no whitespace")
        if decision_step < 0:
            raise ValueError("decision_step must be non-negative")
        validate_public_data(observation)
        if validation.outcome == EvidenceOutcome.PENDING:
            raise ValueError("experience extraction requires completed validation")
        if set(action) != {"order_quantity", "supplier_id"}:
            raise ValueError("action requires order_quantity and supplier_id")
        quantity = action["order_quantity"]
        if not isinstance(quantity, int) or quantity < 0:
            raise ValueError("order_quantity must be a non-negative integer")
        if action["supplier_id"] != "standard":
            raise ValueError("unsupported supplier_id")

        lead_time = observation.get("quoted_lead_time")
        conditions = []
        if lead_time is not None:
            conditions.append(
                ApplicabilityCondition(
                    field="quoted_lead_time", operator="eq", value=lead_time
                )
            )
        metrics = dict(validation.metrics)
        text = (
            f"Order {quantity} units under observed inventory and demand conditions; "
            f"delayed outcome was {validation.outcome.value} with fill rate "
            f"{metrics.get('fill_rate', 0.0):.3f}."
        )
        return ExperienceRecord(
            memory_id=f"exp-{episode_id}-{decision_step}",
            created_step=decision_step,
            text=text,
            variables=["demand", "inventory", "lead_time"],
            conditions=conditions,
            payload={
                "observation": deepcopy(observation),
                "action": deepcopy(action),
                "validation": {
                    **metrics,
                    "outcome": validation.outcome.value,
                    "reason": validation.reason,
                },
            },
        )
