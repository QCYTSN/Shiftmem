"""Shared change-detector interface over realized public signals."""

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ChangeDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"


class ChangeSignal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    detected_step: int = Field(ge=0)
    variable: str = Field(min_length=1)
    direction: ChangeDirection
    statistic: float = Field(gt=0, allow_inf_nan=False)
    threshold: float = Field(gt=0, allow_inf_nan=False)
    suspected_start: int | None = Field(default=None, ge=0)


class ChangeDetector(Protocol):
    def update(self, value: float, step: int) -> ChangeSignal | None: ...

    def reset(self) -> None: ...
