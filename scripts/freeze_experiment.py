"""Gate, copy, and hash the canonical formal-experiment package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from shiftmem.evaluation.splits import load_split_manifest, validate_split_manifests

try:
    from scripts.validate_protocol import validate_protocol
except ModuleNotFoundError:
    from validate_protocol import validate_protocol


CORE_LABELS = {"deepseek_v3_2", "minimax_m2_5"}
SPLIT_PATHS = [
    Path("configs/splits/development.yaml"),
    Path("configs/splits/validation.yaml"),
    Path("configs/splits/test_id.yaml"),
    Path("configs/splits/test_ood.yaml"),
]


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
    for relative in paths:
        source = source_root / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    (destination / "manifest.sha256").write_text(
        build_manifest(destination, paths), encoding="utf-8"
    )


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
    args = parser.parse_args()
    root = args.root.resolve()
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
