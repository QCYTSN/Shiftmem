"""Structured schemas shared by memory baselines."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(min_length=1)
    step: int = Field(ge=0)
    text: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(default_factory=dict)
