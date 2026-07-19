"""Model-provider request, response, and protocol definitions."""

from typing import Any, Literal, Protocol, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation: dict[str, Any]
    memory: list[dict[str, Any]]
    correction: str | None = None


class StrategyProviderRequest(ProviderRequest):
    """Complete model-facing input for a protocol-v2 strategy review."""

    current_strategy: dict[str, int | float]
    trigger_reason: Literal["periodic", "event", "coalesced"]
    trigger_evidence: dict[str, Any] = Field(default_factory=dict)

    @field_validator("current_strategy")
    @classmethod
    def validate_current_strategy(
        cls, value: dict[str, int | float]
    ) -> dict[str, int | float]:
        required = {
            "forecast_window",
            "safety_stock_multiplier",
            "lead_time_buffer",
        }
        if set(value) != required:
            raise ValueError(
                "current_strategy must contain exactly forecast_window, "
                "safety_stock_multiplier, and lead_time_buffer"
            )
        if value["forecast_window"] < 1:
            raise ValueError("forecast_window must be positive")
        if value["safety_stock_multiplier"] < 0:
            raise ValueError("safety_stock_multiplier must be non-negative")
        if value["lead_time_buffer"] < 0:
            raise ValueError("lead_time_buffer must be non-negative")
        return value

    @model_validator(mode="after")
    def validate_trigger_evidence(self) -> Self:
        if self.trigger_reason in {"event", "coalesced"} and not self.trigger_evidence:
            raise ValueError("event and coalesced reviews require trigger_evidence")
        return self


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)


class ModelProvider(Protocol):
    def generate(self, request: ProviderRequest) -> ProviderResponse: ...
