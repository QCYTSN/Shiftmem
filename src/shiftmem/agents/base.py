"""Shared schemas for structured inventory-agent decisions."""

from pydantic import BaseModel, ConfigDict, Field


class AgentDecision(BaseModel):
    """Validated decision produced by every structured agent."""

    model_config = ConfigDict(extra="forbid")

    order_quantity: int = Field(ge=0)
    supplier_id: str = Field(default="standard", pattern="^standard$")
    used_memory_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(min_length=1)

    def to_action(self) -> dict[str, int | str]:
        return {
            "order_quantity": self.order_quantity,
            "supplier_id": self.supplier_id,
        }


class ProviderAttemptLog(BaseModel):
    raw_output: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)
    parse_error: str | None = None


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
