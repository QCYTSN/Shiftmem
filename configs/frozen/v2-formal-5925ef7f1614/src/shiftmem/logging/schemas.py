"""Schemas for freeze-bound, auditable formal run records."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RunIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str = Field(min_length=1)
    freeze_id: str = Field(min_length=1)
    git_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class BudgetLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_calls: int = Field(ge=0)
    max_input_tokens: int = Field(ge=0)
    max_output_tokens: int = Field(ge=0)
    max_cost_cny: float = Field(ge=0, allow_inf_nan=False)
    max_successful_cost_cny: float | None = Field(
        default=None, ge=0, allow_inf_nan=False
    )


class DecisionJournalEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: RunIdentity
    cell_id: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    request_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["reserved", "complete", "failed"] = "complete"
    provider_response: dict[str, Any] | None = None
    error_type: str | None = None
    calls: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    estimated_cost_cny: float = Field(ge=0, allow_inf_nan=False)
    fallback_used: bool = False

    @model_validator(mode="after")
    def validate_status_payload(self) -> "DecisionJournalEntry":
        if self.status == "complete" and self.provider_response is None:
            raise ValueError("complete journal entry requires provider_response")
        if self.status == "failed" and not self.error_type:
            raise ValueError("failed journal entry requires error_type")
        if self.status == "reserved" and (
            self.provider_response is not None or self.error_type is not None
        ):
            raise ValueError("reserved journal entry cannot contain a terminal payload")
        return self
