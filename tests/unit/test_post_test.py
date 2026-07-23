import hashlib
import json
from pathlib import Path

import pytest

from shiftmem.evaluation.post_test import (
    build_reliability_outcome_impact,
    evidence_identity,
    load_declared_cells,
    paired_result,
    summarize_journals,
    verify_declared_sources,
)


def _cell(
    cell_id: str, method: str, value: float, *, access: bool = False, seed: int = 1
) -> dict:
    return {
        "cell_id": cell_id,
        "tier": "primary",
        "scenario_id": "test-id-change",
        "seed": seed,
        "model": "deepseek",
        "method": method,
        "complete": True,
        "endpoint_applicable": True,
        "shift_day": 5,
        "post_shift_cumulative_regret_30": value,
        "recovery": {"recovered": False, "recovery_day": None, "recovery_time": None},
        "inventory_metrics": {"total_cost": 10.0},
        "review_metrics": {},
        "reuse_metrics": {"reused": 0, "retrieved_not_cited": 0, "cited_but_rejected": 0},
        "provider_attempts": 1,
        "input_tokens": 1,
        "output_tokens": 1,
        "parse_failures": 0,
        "fallback_count": 0,
        "environment_records": [],
        "review_logs": [],
        "scheduler_log": [],
        "daily_decision_log": [],
        "memory_audit": None,
        "run_identity": None,
        "test_outcomes_accessed": access,
    }


def _source(path: Path, kind: str, **extra) -> dict:
    return {
        "kind": kind,
        "path": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        **extra,
    }


def test_evidence_sources_are_hash_and_record_count_bound(tmp_path: Path) -> None:
    path = tmp_path / "cells.jsonl"
    path.write_text(json.dumps(_cell("a", "vector", 2.0)) + "\n", encoding="utf-8")
    source = _source(path, "cells", split="Test-ID", records=1)

    verified = verify_declared_sources(tmp_path, [source])
    assert verified[0]["records"] == 1
    assert evidence_identity(verified) == evidence_identity(list(reversed(verified)))

    path.write_text(path.read_text(encoding="utf-8") + "{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        verify_declared_sources(tmp_path, [source])


def test_test_access_metadata_is_disclosed_without_rewriting_raw_cell(tmp_path: Path) -> None:
    path = tmp_path / "cells.jsonl"
    original = json.dumps(_cell("a", "vector", 2.0)) + "\n"
    path.write_text(original, encoding="utf-8")
    source = _source(path, "cells", split="Test-ID", records=1)

    cells, anomalies = load_declared_cells(tmp_path, [source])

    assert cells[0]["test_outcomes_accessed"] is False
    assert anomalies == [
        {
            "type": "cell_test_access_flag_false",
            "path": "cells.jsonl",
            "affected_cells": 1,
            "observed": False,
            "derived_interpretation": True,
        }
    ]
    assert path.read_text(encoding="utf-8") == original


def test_paired_result_uses_shiftmem_minus_vector_direction() -> None:
    rows = []
    for seed, shiftmem, vector in [(1, 8.0, 10.0), (2, 9.0, 10.0)]:
        for method, value in [("shiftmem", shiftmem), ("vector", vector)]:
            rows.append(
                {
                    "manifest_split": "Test-ID",
                    "scenario_id": "change",
                    "model": "deepseek",
                    "seed": seed,
                    "method": method,
                    "value": value,
                }
            )

    result = paired_result(rows, lambda row: row["value"])

    assert result["mean_difference"] == pytest.approx(-1.5)
    assert result["shiftmem_wins"] == 2
    assert result["shiftmem_losses"] == 0


def test_journal_audit_rejects_unresolved_reservation(tmp_path: Path) -> None:
    journal = tmp_path / "journal.jsonl"
    row = {
        "identity": {"run_id": "run"},
        "cell_id": "cell",
        "decision_id": "cell:day-1:attempt-0",
        "status": "reserved",
        "estimated_cost_cny": 0.1,
    }
    journal.write_text(json.dumps(row) + "\n", encoding="utf-8")
    source = _source(journal, "journal", records=1)
    cells = [{"cell_id": "cell"}]

    with pytest.raises(ValueError, match="unresolved formal reservations"):
        summarize_journals(tmp_path, [source], cells)


def test_reliability_outcome_impact_keeps_primary_result_unchanged() -> None:
    cells = []
    by_cell = {}
    for seed, values in [(1, (8.0, 10.0)), (2, (12.0, 10.0))]:
        for method, value in zip(("shiftmem", "vector"), values):
            cell = _cell(f"{seed}-{method}", method, value, seed=seed)
            cell["manifest_split"] = "Test-ID"
            cells.append(cell)
            by_cell[cell["cell_id"]] = {
                "terminal_attempts": 1,
                "successful_responses": 1,
                "failed_attempts": 0,
            }

    result = build_reliability_outcome_impact(cells, {"by_cell": by_cell})

    assert result["paired_units"] == 2
    assert result["confirmatory_primary_result_changed"] is False
    assert result["causal_interpretation_allowed"] is False
    assert (
        result["metrics"]["provider_failure"]["overall"]
        ["zero_event_pair_sensitivity"]["n"]
        == 2
    )
