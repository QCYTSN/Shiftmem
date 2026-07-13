import math

import pytest

from shiftmem.detection.base import ChangeDirection
from shiftmem.detection.page_hinkley import PageHinkleyDetector


def replay(detector: PageHinkleyDetector, values: list[float]):
    return [detector.update(value, step) for step, value in enumerate(values)]


def first_signal(results):
    return next(item for item in results if item is not None)


def test_detector_ignores_warmup_then_detects_increase() -> None:
    detector = PageHinkleyDetector(
        variable="demand", min_samples=5, delta=0.05, threshold=2
    )

    assert all(detector.update(10, step) is None for step in range(5))
    signal = first_signal(
        [detector.update(20, step) for step in range(5, 10)]
    )

    assert signal.variable == "demand"
    assert signal.direction == ChangeDirection.INCREASE
    assert signal.detected_step >= 5
    assert signal.statistic > signal.threshold


def test_detector_detects_decrease() -> None:
    detector = PageHinkleyDetector(
        variable="realized_lead_time", min_samples=5, delta=0.05, threshold=2
    )
    values = [10] * 5 + [2] * 5

    signal = first_signal(replay(detector, values))

    assert signal.direction == ChangeDirection.DECREASE
    assert signal.variable == "realized_lead_time"


def test_detector_reset_replays_identically() -> None:
    detector = PageHinkleyDetector(
        variable="demand", min_samples=4, delta=0.01, threshold=1
    )
    values = [5, 5, 5, 5, 12, 12]
    first = replay(detector, values)

    detector.reset()

    assert replay(detector, values) == first


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_detector_rejects_non_finite_values(value: float) -> None:
    detector = PageHinkleyDetector(variable="demand")
    with pytest.raises(ValueError, match="finite"):
        detector.update(value, 0)


def test_detector_requires_strictly_increasing_non_negative_steps() -> None:
    detector = PageHinkleyDetector(variable="demand")
    with pytest.raises(ValueError, match="non-negative"):
        detector.update(1, -1)
    detector.update(1, 0)
    with pytest.raises(ValueError, match="strictly increasing"):
        detector.update(2, 0)


def test_detector_validates_configuration() -> None:
    with pytest.raises(ValueError, match="min_samples"):
        PageHinkleyDetector(variable="demand", min_samples=1)
    with pytest.raises(ValueError, match="threshold"):
        PageHinkleyDetector(variable="demand", threshold=0)
