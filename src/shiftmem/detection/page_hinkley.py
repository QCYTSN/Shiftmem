"""Deterministic two-sided Page-Hinkley change detector."""

import math

from .base import ChangeDirection, ChangeSignal


class PageHinkleyDetector:
    def __init__(
        self,
        variable: str,
        *,
        min_samples: int = 10,
        delta: float = 0.05,
        threshold: float = 5.0,
    ) -> None:
        if not variable:
            raise ValueError("variable must be non-empty")
        if min_samples < 2:
            raise ValueError("min_samples must be at least 2")
        if not math.isfinite(delta) or delta < 0:
            raise ValueError("delta must be finite and non-negative")
        if not math.isfinite(threshold) or threshold <= 0:
            raise ValueError("threshold must be finite and positive")
        self.variable = variable
        self.min_samples = min_samples
        self.delta = delta
        self.threshold = threshold
        self.reset()

    def reset(self) -> None:
        self._last_step: int | None = None
        self._reset_detection_state()

    def _reset_detection_state(self) -> None:
        self._sample_count = 0
        self._mean = 0.0
        self._increase_sum = 0.0
        self._increase_min = 0.0
        self._decrease_sum = 0.0
        self._decrease_min = 0.0

    def update(self, value: float, step: int) -> ChangeSignal | None:
        if step < 0:
            raise ValueError("step must be non-negative")
        if self._last_step is not None and step <= self._last_step:
            raise ValueError("steps must be strictly increasing")
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        self._last_step = step
        self._sample_count += 1
        self._mean += (value - self._mean) / self._sample_count

        self._increase_sum += value - self._mean - self.delta
        self._increase_min = min(self._increase_min, self._increase_sum)
        increase_statistic = self._increase_sum - self._increase_min

        self._decrease_sum += self._mean - value - self.delta
        self._decrease_min = min(self._decrease_min, self._decrease_sum)
        decrease_statistic = self._decrease_sum - self._decrease_min

        if self._sample_count < self.min_samples:
            return None
        direction: ChangeDirection | None = None
        statistic = 0.0
        if increase_statistic > self.threshold:
            direction = ChangeDirection.INCREASE
            statistic = increase_statistic
        elif decrease_statistic > self.threshold:
            direction = ChangeDirection.DECREASE
            statistic = decrease_statistic
        if direction is None:
            return None

        signal = ChangeSignal(
            detected_step=step,
            variable=self.variable,
            direction=direction,
            statistic=statistic,
            threshold=self.threshold,
            suspected_start=max(0, step - self.min_samples + 1),
        )
        self._reset_detection_state()
        return signal
