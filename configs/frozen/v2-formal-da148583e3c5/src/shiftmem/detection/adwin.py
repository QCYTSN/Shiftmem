"""Deterministic exact-window ADWIN-style change detector.

This implementation deliberately scans the retained window exactly.  The
episodes in ShiftMem are short, so the simpler auditable algorithm is a better
fit than a bucket-compressed approximation.
"""

from __future__ import annotations

import math

from .base import ChangeDirection, ChangeSignal


class ADWINDetector:
    def __init__(
        self,
        variable: str,
        *,
        delta: float = 0.002,
        min_window: int = 5,
        clock: int = 1,
        max_window: int = 256,
    ) -> None:
        if not variable:
            raise ValueError("variable must be non-empty")
        if not math.isfinite(delta) or not 0 < delta < 1:
            raise ValueError("delta must be finite and between zero and one")
        if min_window < 2:
            raise ValueError("min_window must be at least 2")
        if clock < 1:
            raise ValueError("clock must be at least 1")
        if max_window < 2 * min_window:
            raise ValueError("max_window must hold two min_window segments")
        self.variable = variable
        self.delta = float(delta)
        self.min_window = int(min_window)
        self.clock = int(clock)
        self.max_window = int(max_window)
        self.reset()

    @property
    def window_size(self) -> int:
        return len(self._window)

    @property
    def window_start_step(self) -> int | None:
        return self._window[0][0] if self._window else None

    def reset(self) -> None:
        self._window: list[tuple[int, float]] = []
        self._last_step: int | None = None
        self._samples_seen = 0

    def update(self, value: float, step: int) -> ChangeSignal | None:
        if step < 0:
            raise ValueError("step must be non-negative")
        if self._last_step is not None and step <= self._last_step:
            raise ValueError("steps must be strictly increasing")
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        self._last_step = step
        self._samples_seen += 1
        self._window.append((step, float(value)))
        if len(self._window) > self.max_window:
            del self._window[: len(self._window) - self.max_window]

        if (
            len(self._window) < 2 * self.min_window
            or self._samples_seen % self.clock
        ):
            return None

        values = [item[1] for item in self._window]
        total = sum(values)
        total_square = sum(item * item for item in values)
        variance = max(0.0, total_square / len(values) - (total / len(values)) ** 2)
        prefix = sum(values[: self.min_window - 1])
        log_term = math.log(2.0 / self.delta)
        for cut in range(self.min_window, len(values) - self.min_window + 1):
            prefix += values[cut - 1]
            older_count = cut
            newer_count = len(values) - cut
            older_mean = prefix / older_count
            newer_mean = (total - prefix) / newer_count
            inverse_size = 1.0 / older_count + 1.0 / newer_count
            threshold = math.sqrt(
                2.0 * variance * inverse_size * log_term
            ) + (2.0 / 3.0) * inverse_size * log_term
            statistic = abs(newer_mean - older_mean)
            if statistic <= threshold:
                continue
            suspected_start = self._window[cut][0]
            direction = (
                ChangeDirection.INCREASE
                if newer_mean > older_mean
                else ChangeDirection.DECREASE
            )
            del self._window[:cut]
            return ChangeSignal(
                detected_step=step,
                variable=self.variable,
                direction=direction,
                statistic=statistic,
                threshold=threshold,
                suspected_start=suspected_start,
            )
        return None
