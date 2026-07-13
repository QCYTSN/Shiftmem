"""Model-provider request, response, and protocol definitions."""

from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observation: dict[str, Any]
    memory: list[dict[str, Any]]
    correction: str | None = None


class ProviderResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    latency_ms: float = Field(ge=0)


class ModelProvider(Protocol):
    def generate(self, request: ProviderRequest) -> ProviderResponse: ...
