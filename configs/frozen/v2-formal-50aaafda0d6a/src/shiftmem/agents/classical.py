"""Classical non-LLM inventory baselines."""

from collections import deque
from math import sqrt
from typing import Mapping

import numpy as np


REQUIRED_OBSERVATION_KEYS = {
    "day",
    "inventory",
    "pipeline_inventory",
    "last_demand",
    "last_sales",
}


def _validate_observation(observation: Mapping[str, int]) -> None:
    if not REQUIRED_OBSERVATION_KEYS.issubset(observation):
        raise ValueError("observation is missing required inventory fields")


def _action(quantity: int) -> dict[str, int | str]:
    return {"order_quantity": max(0, int(quantity)), "supplier_id": "standard"}


class FixedOrderPolicy:
    def __init__(self, order_quantity: int) -> None:
        if not isinstance(order_quantity, int) or order_quantity < 0:
            raise ValueError("order_quantity must be a non-negative integer")
        self.order_quantity = order_quantity

    def act(self, observation: Mapping[str, int]) -> dict[str, int | str]:
        _validate_observation(observation)
        return _action(self.order_quantity)


class RandomOrderPolicy:
    def __init__(self, minimum: int, maximum: int, seed: int | None = None) -> None:
        if minimum < 0 or maximum < minimum:
            raise ValueError("random order bounds are invalid")
        self.minimum = minimum
        self.maximum = maximum
        self.rng = np.random.default_rng(seed)

    def act(self, observation: Mapping[str, int]) -> dict[str, int | str]:
        _validate_observation(observation)
        return _action(int(self.rng.integers(self.minimum, self.maximum + 1)))


class MovingAverageReorderPolicy:
    def __init__(self, window: int, lead_time: int, safety_stock: float = 0) -> None:
        if window < 1 or lead_time < 1 or safety_stock < 0:
            raise ValueError("window and lead_time must be positive; safety_stock non-negative")
        self.history: deque[int] = deque(maxlen=window)
        self.lead_time = lead_time
        self.safety_stock = safety_stock

    def act(self, observation: Mapping[str, int]) -> dict[str, int | str]:
        _validate_observation(observation)
        self.history.append(observation["last_demand"])
        forecast = sum(self.history) / len(self.history)
        target = forecast * (self.lead_time + 1) + self.safety_stock
        position = observation["inventory"] + observation["pipeline_inventory"]
        return _action(round(target - position))


class ExponentialSmoothingPolicy:
    def __init__(self, alpha: float, lead_time: int, safety_stock: float = 0) -> None:
        if not 0 < alpha <= 1 or lead_time < 1 or safety_stock < 0:
            raise ValueError("alpha, lead_time, or safety_stock is invalid")
        self.alpha = alpha
        self.lead_time = lead_time
        self.safety_stock = safety_stock
        self.forecast: float | None = None

    def act(self, observation: Mapping[str, int]) -> dict[str, int | str]:
        _validate_observation(observation)
        demand = observation["last_demand"]
        self.forecast = demand if self.forecast is None else self.alpha * demand + (1 - self.alpha) * self.forecast
        target = self.forecast * (self.lead_time + 1) + self.safety_stock
        position = observation["inventory"] + observation["pipeline_inventory"]
        return _action(round(target - position))


class OraclePolicy:
    def act(
        self,
        observation: Mapping[str, int],
        oracle_context: Mapping[str, float | int | str],
    ) -> dict[str, int | str]:
        _validate_observation(observation)
        required = {
            "demand_model",
            "demand_mean",
            "dispersion",
            "lead_time",
            "fill_rate",
        }
        if not required.issubset(oracle_context):
            raise ValueError("oracle context is incomplete")
        fill_rate = float(oracle_context["fill_rate"])
        if fill_rate <= 0:
            raise ValueError("oracle requires a positive fill_rate")
        protection_mean = float(oracle_context["demand_mean"]) * (
            int(oracle_context["lead_time"]) + 1
        )
        daily_variance = float(oracle_context["demand_mean"])
        if oracle_context["demand_model"] == "negative_binomial":
            dispersion = float(oracle_context["dispersion"])
            if dispersion <= 0:
                raise ValueError("oracle requires positive dispersion")
            daily_variance += float(oracle_context["demand_mean"]) ** 2 / dispersion
        elif oracle_context["demand_model"] != "poisson":
            raise ValueError("oracle received an unsupported demand model")
        protection_variance = daily_variance * (
            int(oracle_context["lead_time"]) + 1
        )
        safety_stock = 2.0 * sqrt(protection_variance)
        target = (protection_mean + safety_stock) / fill_rate
        position = observation["inventory"] + observation["pipeline_inventory"]
        return _action(round(target - position))
