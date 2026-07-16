"""Gate, copy, and hash the canonical formal-experiment package."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any

import yaml

from shiftmem.evaluation.splits import load_split_manifest, validate_split_manifests

try:
    from scripts.validate_protocol import validate_protocol, validate_protocol_v2
    from scripts.run_formal_experiment import (
        validate_v2_config,
        validate_v2_live_gate_config,
    )
except ModuleNotFoundError:
    from validate_protocol import validate_protocol, validate_protocol_v2
    from run_formal_experiment import validate_v2_config, validate_v2_live_gate_config


CORE_LABELS = {"deepseek_v3_2", "minimax_m2_5"}
SPLIT_PATHS = [
    Path("configs/splits/development.yaml"),
    Path("configs/splits/validation.yaml"),
    Path("configs/splits/test_id.yaml"),
    Path("configs/splits/test_ood.yaml"),
]

V2_QUALIFICATION = Path(
    "artifacts/aggregated/"
    "model_qualification_v2_v2-qual-live-20260715-739bc99_summary.json"
)
V2_PILOT_ANALYSIS = Path(
    "artifacts/aggregated/v2-live-pilot-20260715-a148a81_analysis.json"
)
V2_SELECTED_READINESS = Path(
    "artifacts/aggregated/v2_pilot_selected_profile_readiness.json"
)
V2_FORMAL_REHEARSAL = Path(
    "artifacts/aggregated/v2-formal-offline-rehearsal_summary.json"
)
V2_FORMAL_CONFIG = Path("configs/experiments/formal_v2.yaml")


def evaluate_freeze_gates(
    *,
    git_status: str,
    protocol_errors: list[str],
    qualified_core_labels: set[str],
    selection: dict[str, Any],
    split_errors: list[str],
    pilot: dict[str, Any],
    accidental_test_outcomes: list[str],
) -> list[str]:
    errors: list[str] = []
    if git_status.strip():
        errors.append("repository is dirty")
    errors.extend(f"protocol: {error}" for error in protocol_errors)
    if qualified_core_labels != CORE_LABELS:
        errors.append(
            f"qualified core models must be exactly {sorted(CORE_LABELS)}"
        )
    for field in ("selected_detector", "selected_dormancy", "selected_retrieval"):
        if not selection.get(field):
            errors.append(f"validation selection missing {field}")
    if selection.get("test_outcomes_accessed") is not False:
        errors.append("validation selection did not prove test isolation")
    errors.extend(f"split: {error}" for error in split_errors)
    if not pilot.get("complete") or not pilot.get("metric_completeness"):
        errors.append("Phase 4 Pilot is incomplete")
    if pilot.get("test_outcomes_accessed") is not False:
        errors.append("Phase 4 Pilot did not prove test isolation")
    if accidental_test_outcomes:
        errors.append(f"accidental test outcomes found: {accidental_test_outcomes}")
    return errors


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(root: Path, paths: list[Path]) -> str:
    lines = [f"{_sha256(root / path)}  {path.as_posix()}" for path in sorted(set(paths))]
    return "\n".join(lines) + "\n"


def write_freeze(source_root: Path, destination: Path, paths: list[Path]) -> None:
    if destination.exists():
        raise FileExistsError(f"freeze destination already exists: {destination}")
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise FileExistsError(f"freeze staging destination already exists: {staging}")
    for relative in paths:
        source = source_root / relative
        target = staging / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (staging / "manifest.sha256").write_text(
        build_manifest(staging, paths), encoding="utf-8"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staging, destination)


def evaluate_v2_freeze_gates(
    *,
    git_status: str,
    protocol_errors: list[str],
    protocol_final: bool,
    qualified_core_labels: set[str],
    qualification_isolated: bool,
    pilot_complete: bool,
    pilot_isolated: bool,
    selected_profile_ready: bool,
    formal_rehearsal_ready: bool,
    formal_config_errors: list[str],
    budget_approved: bool,
    profile_consistent: bool,
    split_errors: list[str],
    accidental_test_outcomes: list[str],
) -> list[str]:
    """Pure protocol-v2 replacement-freeze gate evaluation."""

    errors: list[str] = []
    if git_status.strip():
        errors.append("repository is dirty")
    errors.extend(f"protocol: {error}" for error in protocol_errors)
    if not protocol_final:
        errors.append("protocol version must be finalized as 2.0")
    if qualified_core_labels != CORE_LABELS:
        errors.append(
            f"qualified v2 core models must be exactly {sorted(CORE_LABELS)}"
        )
    if not qualification_isolated:
        errors.append("v2 qualification did not prove Test isolation")
    if not pilot_complete or not pilot_isolated:
        errors.append("v2 Pilot evidence is incomplete or not Test-isolated")
    if not selected_profile_ready:
        errors.append("selected v2 runtime profile readiness is incomplete")
    if not formal_rehearsal_ready:
        errors.append("v2 formal offline rehearsal is incomplete")
    errors.extend(f"formal config: {error}" for error in formal_config_errors)
    if not budget_approved:
        errors.append("formal API budget is not explicitly approved")
    if not profile_consistent:
        errors.append("formal config does not match selected runtime profile")
    errors.extend(f"split: {error}" for error in split_errors)
    if accidental_test_outcomes:
        errors.append(f"accidental Test outcomes found: {accidental_test_outcomes}")
    return errors


def _python_paths(root: Path, directory: str) -> list[Path]:
    return sorted(
        path.relative_to(root)
        for path in (root / directory).rglob("*.py")
        if "__pycache__" not in path.parts
    )


def canonical_v2_paths(root: Path) -> list[Path]:
    """Return the complete code, contract, config, and evidence package."""

    root = root.resolve()
    paths = [
        Path("pyproject.toml"),
        Path("docs/experiment_protocol.md"),
        Path("docs/related_work_matrix.md"),
        Path("docs/model_card.md"),
        Path("docs/v2_qualification_audit.md"),
        Path("docs/v2_pilot_report.md"),
        Path("docs/v2_formal_readiness_audit.md"),
        Path("configs/experiments/model_qualification_v2.yaml"),
        Path("configs/experiments/v2_pilot.yaml"),
        Path("configs/experiments/v2_pilot_live.yaml"),
        V2_FORMAL_CONFIG,
        Path("configs/experiments/formal_v2_rehearsal.yaml"),
        Path("configs/qualification_freezes/v2-20260715-c22a4d1/manifest.json"),
        Path("configs/qualification_freezes/v2-20260715-739bc99/manifest.json"),
        Path("configs/qualification_freezes/v2-pilot-live-20260715-a148a81/manifest.json"),
        *SPLIT_PATHS,
        Path("artifacts/aggregated/model_qualification_v2_summary.json"),
        V2_QUALIFICATION,
        V2_PILOT_ANALYSIS,
        Path("artifacts/aggregated/v2-live-pilot-20260715-a148a81_summary.json"),
        V2_SELECTED_READINESS,
        Path("artifacts/aggregated/v2-formal-offline-rehearsal_dry_run.json"),
        V2_FORMAL_REHEARSAL,
        Path("artifacts/raw_runs/model_qualification_v2_v2-qual-live-20260715-739bc99.jsonl"),
        Path("artifacts/raw_runs/v2-live-pilot-20260715-a148a81_cells.jsonl"),
        Path("artifacts/raw_runs/v2-live-pilot-20260715-a148a81_journal.jsonl"),
        Path("artifacts/raw_runs/v2-formal-offline-rehearsal_cells.jsonl"),
        *_python_paths(root, "src/shiftmem"),
        *_python_paths(root, "scripts"),
        *_python_paths(root, "tests"),
    ]
    for split_path in SPLIT_PATHS:
        for entry in load_split_manifest(root / split_path).scenarios:
            paths.append(entry.path.relative_to(root))
    unique = sorted(set(paths))
    missing = [str(path) for path in unique if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError(f"canonical v2 freeze inputs missing: {missing}")
    return unique


def _load_json(root: Path, relative: Path) -> dict[str, Any]:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def _accidental_test_outcomes(root: Path) -> list[str]:
    found: list[str] = []
    raw_root = root / "artifacts/raw_runs"
    if not raw_root.exists():
        return found
    for path in raw_root.rglob("*"):
        normalized = path.name.lower().replace("-", "_")
        if path.is_file() and ("test_id" in normalized or "test_ood" in normalized):
            found.append(str(path.relative_to(root)))
    return sorted(found)


def collect_v2_gate_errors(root: Path, *, git_status: str | None = None) -> list[str]:
    root = root.resolve()
    if git_status is None:
        git_status = subprocess.run(
            ["git", "status", "--porcelain"], cwd=root, check=True,
            capture_output=True, text=True,
        ).stdout
    protocol_path = root / "docs/experiment_protocol.md"
    protocol_text = protocol_path.read_text(encoding="utf-8")
    qualification = _load_json(root, V2_QUALIFICATION)
    qualified = {
        str(row["label"])
        for row in qualification.get("models", [])
        if row.get("qualifies") is True
    }
    pilot = _load_json(root, V2_PILOT_ANALYSIS)
    readiness = _load_json(root, V2_SELECTED_READINESS)
    rehearsal = _load_json(root, V2_FORMAL_REHEARSAL)
    config = yaml.safe_load((root / V2_FORMAL_CONFIG).read_text(encoding="utf-8"))
    config_errors: list[str] = []
    try:
        validate_v2_config(config)
        if config.get("budget_approved") is True:
            validate_v2_live_gate_config(config)
    except ValueError as error:
        config_errors.append(str(error))
    selected_profile = readiness.get("run_metadata", {}).get("shiftmem_profile")
    profile_consistent = (
        selected_profile == config.get("shiftmem_profile")
        and readiness.get("run_metadata", {}).get("review_interval")
        == config.get("review_interval")
        and readiness.get("run_metadata", {}).get("cooldown")
        == config.get("cooldown")
    )
    methods = set(rehearsal.get("methods", {}))
    rehearsal_ready = (
        rehearsal.get("complete") is True
        and rehearsal.get("cells") == 48
        and rehearsal.get("provider_calls") == 0
        and rehearsal.get("test_outcomes_accessed") is False
        and methods
        == {"none", "full_history", "summary", "vector", "time_decay", "shiftmem"}
    )
    return evaluate_v2_freeze_gates(
        git_status=git_status,
        protocol_errors=validate_protocol_v2(protocol_path),
        protocol_final=(
            "Protocol version: 2.0\n" in protocol_text
            and "Protocol version: 2.0-draft" not in protocol_text
        ),
        qualified_core_labels=qualified,
        qualification_isolated=(
            qualification.get("schema") == "strategy"
            and all(
                row.get("qualifies") is True
                for row in qualification.get("models", [])
            )
        ),
        pilot_complete=(pilot.get("complete") is True and pilot.get("cells") == 8),
        pilot_isolated=pilot.get("test_outcomes_accessed") is False,
        selected_profile_ready=(
            readiness.get("complete") is True
            and readiness.get("completed_cells") == 40
            and readiness.get("test_outcomes_accessed") is False
        ),
        formal_rehearsal_ready=rehearsal_ready,
        formal_config_errors=config_errors,
        budget_approved=config.get("budget_approved") is True,
        profile_consistent=profile_consistent,
        split_errors=validate_split_manifests(
            [root / path for path in SPLIT_PATHS], require_all=True
        ),
        accidental_test_outcomes=_accidental_test_outcomes(root),
    )


def build_v2_candidate(root: Path, errors: list[str]) -> dict[str, Any]:
    paths = canonical_v2_paths(root)
    manifest = build_manifest(root, paths)
    freeze_id = f"v2-formal-{hashlib.sha256(manifest.encode()).hexdigest()[:12]}"
    git_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    return {
        "schema": "protocol-v2-replacement-freeze-candidate",
        "generated_date": date.today().isoformat(),
        "git_commit": git_commit,
        "ready": not errors,
        "freeze_id": freeze_id,
        "test_outcomes_accessed": False,
        "blockers": errors,
        "file_count": len(paths),
        "files": {
            path.as_posix(): _sha256(root / path) for path in paths
        },
    }


def canonical_paths(root: Path) -> list[Path]:
    paths = [
        Path("docs/experiment_protocol.md"),
        Path("docs/related_work_matrix.md"),
        Path("docs/model_qualification.md"),
        Path("docs/phase4_pilot_report.md"),
        Path("configs/experiments/model_qualification.yaml"),
        Path("configs/experiments/validation_selection.yaml"),
        Path("configs/experiments/phase4_pilot.yaml"),
        *SPLIT_PATHS,
        Path("artifacts/aggregated/phase1_acceptance.json"),
        Path("artifacts/aggregated/model_qualification_summary.json"),
        Path("artifacts/aggregated/validation_selection.json"),
        Path("artifacts/aggregated/validation_retrieval_rows.json"),
        Path("artifacts/aggregated/phase4_pilot.json"),
        Path("artifacts/aggregated/phase4_pilot_call_estimate.json"),
    ]
    for split_path in SPLIT_PATHS:
        for entry in load_split_manifest(root / split_path).scenarios:
            paths.append(entry.path.relative_to(root.resolve()))
    missing = [str(path) for path in paths if not (root / path).is_file()]
    if missing:
        raise FileNotFoundError(f"canonical freeze inputs missing: {missing}")
    return sorted(set(paths))


def collect_gate_errors(root: Path) -> list[str]:
    git_status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=root, check=True,
        capture_output=True, text=True,
    ).stdout
    model_summary = json.loads(
        (root / "artifacts/aggregated/model_qualification_summary.json").read_text(encoding="utf-8")
    )
    qualified = {
        row["label"] for row in model_summary["models"]
        if row.get("qualifies") and row.get("role") in {"formal_candidate", "second_core_candidate"}
    }
    selection = json.loads(
        (root / "artifacts/aggregated/validation_selection.json").read_text(encoding="utf-8")
    )
    pilot = json.loads(
        (root / "artifacts/aggregated/phase4_pilot.json").read_text(encoding="utf-8")
    )
    accidental = []
    raw_root = root / "artifacts/raw_runs"
    if raw_root.exists():
        for path in raw_root.rglob("*"):
            normalized = path.name.lower().replace("-", "_")
            if path.is_file() and ("test_id" in normalized or "test_ood" in normalized):
                accidental.append(str(path.relative_to(root)))
    return evaluate_freeze_gates(
        git_status=git_status,
        protocol_errors=validate_protocol(root / "docs/experiment_protocol.md"),
        qualified_core_labels=qualified,
        selection=selection,
        split_errors=validate_split_manifests(
            [root / path for path in SPLIT_PATHS], require_all=True
        ),
        pilot=pilot,
        accidental_test_outcomes=accidental,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--v2", action="store_true")
    parser.add_argument("--candidate-output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.v2:
        errors = collect_v2_gate_errors(root)
        candidate = build_v2_candidate(root, errors)
        if args.candidate_output is not None:
            output = args.candidate_output
            if not output.is_absolute():
                output = root / output
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(candidate, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        if errors:
            print(
                json.dumps(
                    {
                        "frozen": False,
                        "candidate_freeze_id": candidate["freeze_id"],
                        "file_count": candidate["file_count"],
                        "errors": errors,
                    },
                    indent=2,
                )
            )
            return 1
        if args.check_only:
            print(
                json.dumps(
                    {
                        "ready": True,
                        "freeze_id": candidate["freeze_id"],
                        "file_count": candidate["file_count"],
                    }
                )
            )
            return 0
        destination = root / "configs/frozen" / str(candidate["freeze_id"])
        write_freeze(root, destination, canonical_v2_paths(root))
        print(
            json.dumps(
                {
                    "frozen": True,
                    "freeze_id": candidate["freeze_id"],
                    "path": str(destination),
                }
            )
        )
        return 0
    errors = collect_gate_errors(root)
    if errors:
        print(json.dumps({"frozen": False, "errors": errors}, indent=2))
        return 1
    paths = canonical_paths(root)
    source_manifest = build_manifest(root, paths)
    freeze_id = f"phase4-20260713-{hashlib.sha256(source_manifest.encode()).hexdigest()[:12]}"
    if args.check_only:
        print(json.dumps({"ready": True, "freeze_id": freeze_id}))
        return 0
    destination = root / "configs/frozen" / freeze_id
    write_freeze(root, destination, paths)
    print(json.dumps({"frozen": True, "freeze_id": freeze_id, "path": str(destination)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
