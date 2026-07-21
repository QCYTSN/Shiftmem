"""Low-frequency review scheduler for the v2 strategy agent.

The LLM may run only when the scheduler permits it: on the fixed periodic
interval or on a detector event outside the frozen cooldown. Same-day periodic
and event triggers are coalesced into one review. Repeated event alerts inside
the cooldown are logged but do not cause a call. The interval and cooldown are
constructor configuration (Validation-selected and frozen later); no model
output can change them.
"""

from dataclasses import dataclass, field
from typing import Any, Literal

Trigger = Literal["periodic", "event", "coalesced", "none"]


@dataclass(frozen=True)
class ReviewDecision:
    should_review: bool
    trigger: Trigger
    last_review_day: int | None
    coalesced: bool = False
    cooldown_suppressed: bool = False
    evidence: dict[str, Any] | None = None


@dataclass
class ReviewScheduler:
    interval: int = 5
    cooldown: int = 3
    _last_review_day: int | None = field(default=None, init=False)
    _last_event_review_day: int | None = field(default=None, init=False)

    def __post_init__(self) -> None:
        if self.interval < 1:
            raise ValueError("interval must be positive")
        if self.cooldown < 0:
            raise ValueError("cooldown must be non-negative")

    def _in_cooldown(self, day: int) -> bool:
        if self._last_event_review_day is None:
            return False
        return (day - self._last_event_review_day) <= self.cooldown

    def evaluate(
        self,
        day: int,
        event: bool,
        evidence: dict[str, Any] | None = None,
    ) -> ReviewDecision:
        periodic = day % self.interval == 0
        event_allowed = event and not self._in_cooldown(day)

        if periodic and event:
            # A periodic review always happens; an overlapping event is folded
            # into the same call rather than producing a second one.
            self._last_review_day = day
            self._last_event_review_day = day
            return ReviewDecision(
                should_review=True,
                trigger="coalesced",
                last_review_day=day,
                coalesced=True,
                evidence=evidence,
            )

        if periodic:
            self._last_review_day = day
            return ReviewDecision(
                should_review=True,
                trigger="periodic",
                last_review_day=day,
            )

        if event_allowed:
            self._last_review_day = day
            self._last_event_review_day = day
            return ReviewDecision(
                should_review=True,
                trigger="event",
                last_review_day=day,
                evidence=evidence,
            )

        if event:  # event present but suppressed by cooldown
            return ReviewDecision(
                should_review=False,
                trigger="none",
                last_review_day=self._last_review_day,
                cooldown_suppressed=True,
                evidence=evidence,
            )

        return ReviewDecision(
            should_review=False,
            trigger="none",
            last_review_day=self._last_review_day,
        )
