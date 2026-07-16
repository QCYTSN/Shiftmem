"""Shared schemas for structured inventory-agent decisions."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentDecision(BaseModel):
    """Validated decision produced by every structured agent."""

    model_config = ConfigDict(extra="forbid")

    order_quantity: int = Field(ge=0)
    supplier_id: str = Field(default="standard", pattern="^standard$")
    used_memory_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=200)

    def to_action(self) -> dict[str, int | str]:
        return {
            "order_quantity": self.order_quantity,
            "supplier_id": self.supplier_id,
        }


class StrategyProposal(BaseModel):
    """Bounded strategy vector proposed by the v2 low-frequency review agent.

    The agent never emits ``order_quantity``; the deterministic controller owns
    every daily order. ``extra="forbid"`` guarantees an ``order_quantity`` (or
    any other smuggled field) is rejected at parse time.
    """

    model_config = ConfigDict(extra="forbid")

    # Basic structural sanity only; the frozen operational bounds are applied
    # by a separate deterministic clamp step so out-of-range proposals are
    # projected into bounds rather than silently discarded.
    forecast_window: int = Field(ge=1)
    safety_stock_multiplier: float = Field(ge=0.0)
    lead_time_buffer: int = Field(ge=0)
    used_memory_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1, max_length=200)


class ProviderAttemptLog(BaseModel):
    raw_output: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    parse_error: str | None = None


class StrategyReviewLog(BaseModel):
    """Audit record for one strategy review invocation."""

    day: int = Field(ge=0)
    trigger_reason: Literal["periodic", "event", "coalesced"]
    trigger_evidence: dict[str, Any] = Field(default_factory=dict)
    supplied_memory_ids: list[str]
    cited_memory_ids: list[str]
    proposal: StrategyProposal | None
    active_strategy: dict[str, float | int]
    clamped: bool
    attempts: list[ProviderAttemptLog]
    attempt_count: int = Field(ge=1, le=2)
    parse_failure_count: int = Field(ge=0, le=2)
    fallback_used: bool
    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)
    total_latency_ms: float = Field(ge=0)


class DecisionLog(BaseModel):
    step: int = Field(ge=0)
    supplied_memory_ids: list[str]
    decision: AgentDecision
    attempts: list[ProviderAttemptLog]
    attempt_count: int = Field(ge=1, le=2)
    parse_failure_count: int = Field(ge=0, le=2)
    fallback_used: bool
    total_input_tokens: int = Field(ge=0)
    total_output_tokens: int = Field(ge=0)
    total_latency_ms: float = Field(ge=0)
