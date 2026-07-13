"""Regime-shift definitions and scenario scheduling."""

from dataclasses import dataclass, field, replace
from math import pi, sin
from pathlib import Path
from typing import Any, Mapping

import yaml

from .demand_models import DemandParameters
from .supply_models import SupplyParameters


SHIFT_TYPES = {
    "stable",
    "sudden_demand",
    "gradual_demand",
    "periodic_demand",
    "sudden_supply",
    "combined",
    "false_alarm",
}


@dataclass(frozen=True)
class CostParameters:
    purchase: float
    holding: float
    stockout: float
    fixed_order: float = 0.0

    def __post_init__(self) -> None:
        if any(value < 0 for value in (self.purchase, self.holding, self.stockout, self.fixed_order)):
            raise ValueError("cost parameters must be non-negative")


@dataclass(frozen=True)
class Shift:
    type: str
    start_day: int
    end_day: int | None = None
    changes: Mapping[str, float | int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.type not in SHIFT_TYPES:
            raise ValueError(f"unsupported shift type: {self.type}")
        if self.start_day < 0:
            raise ValueError("start_day must be non-negative")
        if self.end_day is not None and self.end_day < self.start_day:
            raise ValueError("end_day must not precede start_day")


@dataclass(frozen=True)
class DailyParameters:
    demand: DemandParameters
    supply: SupplyParameters


@dataclass(frozen=True)
class Scenario:
    name: str
    episode_length: int
    initial_inventory: int
    demand_model: str
    demand: DemandParameters
    supply: SupplyParameters
    costs: CostParameters
    shifts: tuple[Shift, ...] = ()

    def __post_init__(self) -> None:
        if self.episode_length < 1:
            raise ValueError("episode_length must be positive")
        if self.initial_inventory < 0:
            raise ValueError("initial_inventory must be non-negative")
        if self.demand_model not in {"poisson", "negative_binomial"}:
            raise ValueError("unsupported demand_model")

    def parameters_at(self, day: int) -> DailyParameters:
        if not 0 <= day < self.episode_length:
            raise ValueError("day is outside the episode")
        demand = self.demand
        supply = self.supply
        for shift in self.shifts:
            demand, supply = _apply_shift(demand, supply, shift, day)
        return DailyParameters(demand, supply)


def _apply_shift(
    demand: DemandParameters,
    supply: SupplyParameters,
    shift: Shift,
    day: int,
) -> tuple[DemandParameters, SupplyParameters]:
    if shift.type == "stable" or day < shift.start_day:
        return demand, supply
    if shift.type == "false_alarm" and shift.end_day is not None and day > shift.end_day:
        return demand, supply

    multiplier = 1.0
    if shift.type in {"sudden_demand", "combined", "false_alarm"}:
        multiplier = float(shift.changes.get("base_level_multiplier", 1.0))
    elif shift.type == "gradual_demand":
        if shift.end_day is None:
            raise ValueError("gradual_demand requires end_day")
        target = float(shift.changes.get("base_level_multiplier", 1.0))
        progress = min(1.0, (day - shift.start_day) / (shift.end_day - shift.start_day))
        multiplier = 1.0 + (target - 1.0) * progress
    elif shift.type == "periodic_demand":
        amplitude = float(shift.changes.get("amplitude", 0.0))
        period = int(shift.changes.get("period", 1))
        if period < 1:
            raise ValueError("period must be positive")
        multiplier = 1.0 + amplitude * sin(2 * pi * (day - shift.start_day) / period)

    if shift.type in {"sudden_demand", "gradual_demand", "periodic_demand", "combined", "false_alarm"}:
        demand = replace(demand, base_level=demand.base_level * multiplier)
    if shift.type in {"sudden_supply", "combined"}:
        supply = replace(
            supply,
            lead_time=int(shift.changes.get("lead_time", supply.lead_time)),
            fill_rate=float(shift.changes.get("fill_rate", supply.fill_rate)),
        )
    return demand, supply


def load_scenario(path: str | Path) -> Scenario:
    with Path(path).open("r", encoding="utf-8") as stream:
        data: dict[str, Any] = yaml.safe_load(stream)
    allowed = {"name", "episode_length", "initial_inventory", "demand_model", "demand", "supply", "costs", "shifts"}
    unknown = set(data) - allowed
    if unknown:
        raise ValueError(f"unknown scenario keys: {sorted(unknown)}")
    shifts = tuple(Shift(**item) for item in data.get("shifts", []))
    return Scenario(
        name=data["name"],
        episode_length=int(data.get("episode_length", 150)),
        initial_inventory=int(data["initial_inventory"]),
        demand_model=data["demand_model"],
        demand=DemandParameters(**data["demand"]),
        supply=SupplyParameters(**data["supply"]),
        costs=CostParameters(**data["costs"]),
        shifts=shifts,
    )
