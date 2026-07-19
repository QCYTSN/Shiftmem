"""Tests for the low-frequency review scheduler."""

from shiftmem.control.scheduler import ReviewScheduler


def test_periodic_review_every_five_completed_days():
    scheduler = ReviewScheduler(interval=5, cooldown=3)
    triggered = [d for d in range(21) if scheduler.evaluate(d, event=False).should_review]
    # Origin at day 0, then every five completed days.
    assert triggered == [0, 5, 10, 15, 20]


def test_event_outside_cooldown_triggers_review():
    scheduler = ReviewScheduler(interval=5, cooldown=3)
    scheduler.evaluate(0, event=False)  # periodic origin
    decision = scheduler.evaluate(2, event=True, evidence={"variable": "demand"})
    assert decision.should_review is True
    assert decision.trigger == "event"
    assert decision.evidence == {"variable": "demand"}


def test_same_day_periodic_and_event_coalesce_to_one_review():
    scheduler = ReviewScheduler(interval=5, cooldown=3)
    scheduler.evaluate(0, event=False)
    decision = scheduler.evaluate(5, event=True, evidence={"variable": "demand"})
    assert decision.should_review is True
    assert decision.trigger == "coalesced"
    assert decision.coalesced is True


def test_repeated_event_inside_cooldown_is_suppressed():
    scheduler = ReviewScheduler(interval=5, cooldown=3)
    scheduler.evaluate(0, event=False)
    first = scheduler.evaluate(2, event=True)
    assert first.should_review is True
    suppressed = scheduler.evaluate(3, event=True)
    assert suppressed.should_review is False
    assert suppressed.cooldown_suppressed is True
    assert suppressed.trigger == "none"


def test_event_after_cooldown_expires_triggers_again():
    scheduler = ReviewScheduler(interval=5, cooldown=3)
    scheduler.evaluate(0, event=False)
    scheduler.evaluate(2, event=True)  # review at 2, cooldown covers 3,4
    later = scheduler.evaluate(6, event=True)
    assert later.should_review is True


def test_last_review_day_tracked():
    scheduler = ReviewScheduler(interval=5, cooldown=3)
    scheduler.evaluate(0, event=False)
    decision = scheduler.evaluate(5, event=False)
    assert decision.last_review_day == 5


def test_no_trigger_returns_none():
    scheduler = ReviewScheduler(interval=5, cooldown=3)
    scheduler.evaluate(0, event=False)
    decision = scheduler.evaluate(3, event=False)
    assert decision.should_review is False
    assert decision.trigger == "none"
