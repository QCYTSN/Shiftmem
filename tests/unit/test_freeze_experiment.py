from pathlib import Path

from scripts.freeze_experiment import (
    build_v2_candidate,
    build_manifest,
    canonical_v2_paths,
    collect_v2_gate_errors,
    evaluate_freeze_gates,
    evaluate_v2_freeze_gates,
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


def passing_v2_gate_kwargs() -> dict:
    return {
        "git_status": "",
        "protocol_errors": [],
        "protocol_final": True,
        "qualified_core_labels": {"deepseek_v3_2", "minimax_m2_5"},
        "qualification_isolated": True,
        "pilot_complete": True,
        "pilot_isolated": True,
        "selected_profile_ready": True,
        "formal_rehearsal_ready": True,
        "formal_config_errors": [],
        "budget_approved": True,
        "profile_consistent": True,
        "split_errors": [],
        "accidental_test_outcomes": [],
    }


def test_each_v2_replacement_freeze_gate_blocks() -> None:
    changes = [
        ("git_status", " M file"),
        ("protocol_errors", ["missing"]),
        ("protocol_final", False),
        ("qualified_core_labels", {"deepseek_v3_2"}),
        ("qualification_isolated", False),
        ("pilot_complete", False),
        ("pilot_isolated", False),
        ("selected_profile_ready", False),
        ("formal_rehearsal_ready", False),
        ("formal_config_errors", ["bad config"]),
        ("budget_approved", False),
        ("profile_consistent", False),
        ("split_errors", ["overlap"]),
        ("accidental_test_outcomes", ["test_ood.jsonl"]),
    ]
    for field, value in changes:
        kwargs = passing_v2_gate_kwargs()
        kwargs[field] = value
        assert evaluate_v2_freeze_gates(**kwargs), field


def test_v2_candidate_package_covers_code_contract_configs_and_raw_evidence() -> None:
    root = Path.cwd().resolve()
    paths = canonical_v2_paths(root)
    required = {
        Path("docs/experiment_protocol.md"),
        Path("configs/experiments/formal_v2.yaml"),
        Path("scripts/run_formal_experiment.py"),
        Path("src/shiftmem/control/episode.py"),
        Path("tests/unit/test_run_logger.py"),
        Path("artifacts/raw_runs/v2-formal-offline-rehearsal_cells.jsonl"),
    }
    assert required.issubset(paths)
    candidate = build_v2_candidate(root, ["budget blocked"])
    assert candidate["ready"] is False
    assert candidate["test_outcomes_accessed"] is False
    assert candidate["blockers"] == ["budget blocked"]
    assert candidate["file_count"] == len(paths)
    assert set(candidate["files"]) == {path.as_posix() for path in paths}


def test_current_v2_candidate_is_blocked_only_by_declared_pre_freeze_gates() -> None:
    errors = collect_v2_gate_errors(Path.cwd(), git_status="")
    assert errors == [
        "protocol version must be finalized as 2.0",
        "formal API budget is not explicitly approved",
    ]
