"""Deterministic parameterized order-up-to controller for protocol v2.

The controller is shared by every LLM memory method. The LLM only proposes a
bounded ``StrategyParameters`` vector at low-frequency reviews; this module
turns that vector plus public state into the daily integer order. It never
calls a provider and never reads hidden demand parameters, the regime ID, the
shift schedule, future demand, realized future fill, or Oracle context.
"""

from math import sqrt
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field

# Provisional Development defaults and bounds. Final values are Validation
# decisions and become frozen protocol fields before any Test execution.
_BOUNDS: dict[str, tuple[float, float]] = {
    "forecast_window": (1, 60),
    "safety_stock_multiplier": (0.0, 5.0),
    "lead_time_buffer": (0, 14),
}

_MAX_REVIEW_DELTAS: dict[str, float] = {
    "forecast_window": 7,
    "safety_stock_multiplier": 1.0,
    "lead_time_buffer": 1,
}

# Public observation keys the controller is allowed to read. Anything that
# resembles hidden truth (demand_mean, dispersion, fill_rate, regime_id, ...)
# is refused in strict mode so leakage fails loudly during development.
_ALLOWED_KEYS = frozenset(
    {
        "day",
        "inventory",
        "pipeline_inventory",
        "pipeline_orders",
        "quoted_lead_time",
        "last_demand",
        "last_sales",
        "costs",
        "recent_history",
    }
)


class StrategyParameters(BaseModel):
    """Bounded strategy vector the LLM may propose at a review.

    The review interval, controller formula, supplier, and daily order are not
    part of this vector and cannot be model-controlled.
    """

    model_config = ConfigDict(extra="forbid")

    forecast_window: int = Field(default=14, ge=1, le=60)
    safety_stock_multiplier: float = Field(default=1.2, ge=0.0, le=5.0)
    lead_time_buffer: int = Field(default=1, ge=0, le=14)

    @staticmethod
    def bounds() -> dict[str, tuple[float, float]]:
        return dict(_BOUNDS)

    @staticmethod
    def max_review_deltas() -> dict[str, float]:
        return dict(_MAX_REVIEW_DELTAS)

    @classmethod
    def clamp(
        cls,
        forecast_window: float,
        safety_stock_multiplier: float,
        lead_time_buffer: float,
    ) -> "StrategyParameters":
        """Project any proposed values into the declared bounds."""

        fw_lo, fw_hi = _BOUNDS["forecast_window"]
        ss_lo, ss_hi = _BOUNDS["safety_stock_multiplier"]
        lt_lo, lt_hi = _BOUNDS["lead_time_buffer"]
        return cls(
            forecast_window=int(min(max(forecast_window, fw_lo), fw_hi)),
            safety_stock_multiplier=min(max(safety_stock_multiplier, ss_lo), ss_hi),
            lead_time_buffer=int(min(max(lead_time_buffer, lt_lo), lt_hi)),
        )

    @classmethod
    def clamp_revision(
        cls,
        current: "StrategyParameters",
        *,
        forecast_window: float,
        safety_stock_multiplier: float,
        lead_time_buffer: float,
    ) -> "StrategyParameters":
        """Project a proposal into absolute bounds and per-review delta caps."""

        bounded = cls.clamp(
            forecast_window=forecast_window,
            safety_stock_multiplier=safety_stock_multiplier,
            lead_time_buffer=lead_time_buffer,
        )
        return cls(
            forecast_window=int(
                min(
                    max(
                        bounded.forecast_window,
                        current.forecast_window - _MAX_REVIEW_DELTAS["forecast_window"],
                    ),
                    current.forecast_window + _MAX_REVIEW_DELTAS["forecast_window"],
                )
            ),
            safety_stock_multiplier=min(
                max(
                    bounded.safety_stock_multiplier,
                    current.safety_stock_multiplier
                    - _MAX_REVIEW_DELTAS["safety_stock_multiplier"],
                ),
                current.safety_stock_multiplier
                + _MAX_REVIEW_DELTAS["safety_stock_multiplier"],
            ),
            lead_time_buffer=int(
                min(
                    max(
                        bounded.lead_time_buffer,
                        current.lead_time_buffer
                        - _MAX_REVIEW_DELTAS["lead_time_buffer"],
                    ),
                    current.lead_time_buffer
                    + _MAX_REVIEW_DELTAS["lead_time_buffer"],
                )
            ),
        )


class DeterministicController:
    """Compute a non-negative integer daily order from public state."""

    def order(
        self,
        observation: Mapping[str, Any],
        strategy: StrategyParameters,
        strict: bool = False,
    ) -> dict[str, int | str]:
        if strict:
            unexpected = set(observation) - _ALLOWED_KEYS
            if unexpected:
                raise ValueError(
                    f"observation carries non-public keys: {sorted(unexpected)}"
                )

        forecast = self._forecast(observation, strategy.forecast_window)
        sigma = self._demand_std(observation, strategy.forecast_window)
        lead_time = int(observation["quoted_lead_time"])

        # Protection horizon covers the quoted lead time, the strategy buffer,
        # and the day being ordered for.
        protection_periods = lead_time + strategy.lead_time_buffer + 1
        base_stock = forecast * protection_periods
        safety_stock = strategy.safety_stock_multiplier * sigma * sqrt(protection_periods)
        target = base_stock + safety_stock

        position = int(observation["inventory"]) + int(observation["pipeline_inventory"])
        quantity = max(0, round(target - position))
        return {"order_quantity": int(quantity), "supplier_id": "standard"}

    def order_up_to_target(
        self, observation: Mapping[str, Any], strategy: StrategyParameters
    ) -> float:
        """Return the order-up-to target (base stock + safety stock) a strategy
        induces, before subtracting inventory position.

        This is the actual decision-relevant quantity the strategy controls, so
        a qualification gate should compare it rather than any single parameter:
        forecast_window, safety_stock_multiplier, and lead_time_buffer all feed
        it jointly, and only their combined effect is behaviorally meaningful.
        """

        forecast = self._forecast(observation, strategy.forecast_window)
        sigma = self._demand_std(observation, strategy.forecast_window)
        lead_time = int(observation["quoted_lead_time"])
        protection_periods = lead_time + strategy.lead_time_buffer + 1
        base_stock = forecast * protection_periods
        safety = strategy.safety_stock_multiplier * sigma * sqrt(protection_periods)
        return base_stock + safety

    def safety_stock(
        self, observation: Mapping[str, Any], strategy: StrategyParameters
    ) -> float:
        """Return the actual safety-stock level a strategy induces.

        This is the strategy-controlled protection component, ``multiplier * σ *
        sqrt(protection_periods)``, using the demand variability observed in
        public history. It is the meaningful quantity to compare across
        scenarios: a lower multiplier can still yield more protection when
        observed demand variability rose, so a qualification gate must compare
        this level rather than the bare multiplier coefficient.
        """

        sigma = self._demand_std(observation, strategy.forecast_window)
        lead_time = int(observation["quoted_lead_time"])
        protection_periods = lead_time + strategy.lead_time_buffer + 1
        return strategy.safety_stock_multiplier * sigma * sqrt(protection_periods)

    @staticmethod
    def _recent_demand(observation: Mapping[str, Any], window: int) -> list[float]:
        history = observation.get("recent_history") or []
        demands = [float(record["demand"]) for record in history]
        if not demands:
            return [float(observation.get("last_demand", 0))]
        return demands[-window:]

    def _forecast(self, observation: Mapping[str, Any], window: int) -> float:
        demands = self._recent_demand(observation, window)
        return sum(demands) / len(demands)

    def _demand_std(self, observation: Mapping[str, Any], window: int) -> float:
        demands = self._recent_demand(observation, window)
        if len(demands) < 2:
            return 0.0
        mean = sum(demands) / len(demands)
        variance = sum((value - mean) ** 2 for value in demands) / (len(demands) - 1)
        return sqrt(variance)
