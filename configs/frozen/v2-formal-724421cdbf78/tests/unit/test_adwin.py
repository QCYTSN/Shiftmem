import math

import pytest

from shiftmem.detection import ADWINDetector, ChangeDirection


def replay(detector: ADWINDetector, values: list[float]):
    return [detector.update(value, step) for step, value in enumerate(values)]


def signals(results):
    return [result for result in results if result is not None]


def test_stationary_trace_does_not_signal() -> None:
    detector = ADWINDetector("demand", delta=0.002, min_window=8)
    assert signals(replay(detector, [10.0] * 100)) == []


@pytest.mark.parametrize(
    ("before", "after", "direction"),
    [
        (5.0, 20.0, ChangeDirection.INCREASE),
        (20.0, 5.0, ChangeDirection.DECREASE),
    ],
)
def test_detects_two_sided_level_shift(before, after, direction) -> None:
    detector = ADWINDetector("demand", delta=0.01, min_window=5)
    detected = signals(replay(detector, [before] * 30 + [after] * 30))
    assert detected
    assert detected[0].direction == direction
    assert detected[0].statistic > detected[0].threshold
    assert 30 <= detected[0].detected_step < 60


def test_detection_shrinks_obsolete_prefix() -> None:
    detector = ADWINDetector("demand", delta=0.01, min_window=5)
    for step, value in enumerate([5.0] * 30 + [20.0] * 10):
        signal = detector.update(value, step)
        if signal:
            assert detector.window_size < step + 1
            assert detector.window_start_step >= signal.suspected_start
            return
    pytest.fail("expected a change signal")


def test_reset_replays_identically() -> None:
    detector = ADWINDetector("demand", delta=0.01, min_window=5, clock=2)
    values = [8.0] * 25 + [16.0] * 25
    first = replay(detector, values)
    detector.reset()
    assert replay(detector, values) == first


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_rejects_nonfinite_values(value: float) -> None:
    detector = ADWINDetector("demand")
    with pytest.raises(ValueError, match="finite"):
        detector.update(value, 0)


def test_requires_ordered_steps() -> None:
    detector = ADWINDetector("demand")
    with pytest.raises(ValueError, match="non-negative"):
        detector.update(1, -1)
    detector.update(1, 0)
    with pytest.raises(ValueError, match="strictly increasing"):
        detector.update(1, 0)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"variable": ""}, "variable"),
        ({"variable": "x", "delta": 0}, "delta"),
        ({"variable": "x", "delta": 1}, "delta"),
        ({"variable": "x", "min_window": 1}, "min_window"),
        ({"variable": "x", "clock": 0}, "clock"),
        ({"variable": "x", "min_window": 5, "max_window": 9}, "max_window"),
    ],
)
def test_validates_configuration(kwargs, message) -> None:
    with pytest.raises(ValueError, match=message):
        ADWINDetector(**kwargs)
