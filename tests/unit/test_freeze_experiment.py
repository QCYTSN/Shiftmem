from pathlib import Path

from scripts.freeze_experiment import (
    build_manifest,
    evaluate_freeze_gates,
    write_freeze,
)
from scripts.verify_freeze import verify_freeze


def passing_gate_kwargs() -> dict:
    return {
        "git_status": "",
        "protocol_errors": [],
        "qualified_core_labels": {"deepseek_v3_2", "minimax_m2_5"},
        "selection": {"selected_detector": {}, "selected_dormancy": {}, "selected_retrieval": {}, "test_outcomes_accessed": False},
        "split_errors": [],
        "pilot": {"complete": True, "metric_completeness": True, "test_outcomes_accessed": False},
        "accidental_test_outcomes": [],
    }


def test_each_freeze_gate_blocks() -> None:
    changes = [
        ("git_status", " M file"),
        ("protocol_errors", ["missing"]),
        ("qualified_core_labels", {"deepseek_v3_2"}),
        ("selection", {"selected_detector": None}),
        ("split_errors", ["overlap"]),
        ("pilot", {"complete": False}),
        ("accidental_test_outcomes", ["test_ood.jsonl"]),
    ]
    for field, value in changes:
        kwargs = passing_gate_kwargs()
        kwargs[field] = value
        assert evaluate_freeze_gates(**kwargs), field


def test_manifest_is_sorted_and_deterministic(tmp_path: Path) -> None:
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    first = build_manifest(tmp_path, [Path("b.txt"), Path("a.txt")])
    second = build_manifest(tmp_path, [Path("a.txt"), Path("b.txt")])
    assert first == second
    assert first.splitlines()[0].endswith("a.txt")


def test_write_and_verify_detects_tampering(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "config.yaml").write_text("value: 1\n", encoding="utf-8")
    freeze = tmp_path / "freeze"
    write_freeze(source, freeze, [Path("config.yaml")])
    assert verify_freeze(freeze) == []
    (freeze / "config.yaml").write_text("value: 2\n", encoding="utf-8")
    assert any("hash mismatch" in error for error in verify_freeze(freeze))
