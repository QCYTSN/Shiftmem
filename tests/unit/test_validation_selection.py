from pathlib import Path

import pytest
import scripts.select_validation_config as selection

from scripts.select_validation_config import (
    ensure_selection_paths,
    select_dormancy,
    select_detector,
    select_retrieval,
)
from shiftmem.envs.shifts import Shift


def test_selection_rejects_test_manifest_paths() -> None:
    with pytest.raises(ValueError, match="Test-ID|Test-OOD"):
        ensure_selection_paths([Path("configs/splits/test_id.yaml")])
    with pytest.raises(ValueError, match="Test-ID|Test-OOD"):
        ensure_selection_paths([Path("configs/splits/test_ood.yaml")])


def test_detector_selection_is_lexicographic_and_deterministic() -> None:
    rows = [
        {"config_id": "c", "misses": 0, "false_positives": 2, "mean_delay": 1.0},
        {"config_id": "b", "misses": 0, "false_positives": 1, "mean_delay": 4.0},
        {"config_id": "a", "misses": 0, "false_positives": 1, "mean_delay": 4.0},
        {"config_id": "fast-but-misses", "misses": 1, "false_positives": 0, "mean_delay": 0.0},
    ]
    assert select_detector(rows)["config_id"] == "a"


def test_retrieval_selection_uses_primary_then_invalid_reuse_then_tokens() -> None:
    rows = [
        {"config_id": "worse", "post_shift_cumulative_regret_30": 11, "invalid_reuse": 0, "tokens": 1},
        {"config_id": "token-high", "post_shift_cumulative_regret_30": 10, "invalid_reuse": 1, "tokens": 200},
        {"config_id": "token-low", "post_shift_cumulative_regret_30": 10, "invalid_reuse": 1, "tokens": 100},
    ]
    assert select_retrieval(rows)["config_id"] == "token-low"


def test_dormancy_selection_prioritizes_false_transitions_then_stale_reuse() -> None:
    rows = [
        {"patience": 2, "false_dormancies": 1, "invalid_reuse": 1, "reactivation_delay": 0},
        {"patience": 7, "false_dormancies": 0, "invalid_reuse": 6, "reactivation_delay": 0},
        {"patience": 3, "false_dormancies": 0, "invalid_reuse": 2, "reactivation_delay": 0},
    ]
    assert select_dormancy(rows)["patience"] == 3


def test_selectors_reject_empty_or_nonfinite_rows() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        select_detector([])
    with pytest.raises(ValueError, match="finite"):
        select_retrieval(
            [{"config_id": "bad", "post_shift_cumulative_regret_30": float("nan"), "invalid_reuse": 0, "tokens": 0}]
        )


def test_supply_selection_uses_runtime_public_signal_contract() -> None:
    assert hasattr(selection, "detector_variable")
    assert selection.detector_variable((Shift("sudden_supply", 10),)) == "quoted_lead_time"
    assert selection.detector_variable((Shift("sudden_demand", 10),)) == "demand"
