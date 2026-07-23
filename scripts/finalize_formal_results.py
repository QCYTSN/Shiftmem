"""Verify and aggregate the immutable Protocol-v2 formal Test evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import yaml

from shiftmem.evaluation.formal_v2 import FormalV2CellResult, validate_plan_completeness
from shiftmem.evaluation.post_test import (
    atomic_write_json,
    build_reliability_audit,
    build_statistical_analysis,
    evidence_identity,
    load_declared_cells,
    summarize_journals,
    validate_expected_matrix,
    verify_declared_sources,
)
from shiftmem.evaluation.splits import load_split_manifest

try:
    from scripts.run_formal_experiment import build_v2_cell_plan
    from scripts.verify_freeze import verify_freeze
except ModuleNotFoundError:
    from run_formal_experiment import build_v2_cell_plan
    from verify_freeze import verify_freeze


DEFAULT_SPEC = Path("configs/experiments/formal_v2_post_test.yaml")
DEFAULT_MANIFEST = Path("artifacts/aggregated/v2_formal_evidence_manifest.json")
DEFAULT_ANALYSIS = Path("artifacts/aggregated/v2_formal_statistical_analysis.json")
DEFAULT_RELIABILITY = Path("artifacts/aggregated/v2_formal_reliability_audit.json")


def _load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected mapping in {path}")
    return value


def build_outputs(root: Path, spec_path: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    spec = _load_yaml(root / spec_path)
    if spec.get("schema") != "shiftmem-formal-v2-post-test-spec-v1":
        raise ValueError("post-Test evidence specification schema is invalid")
    if spec.get("test_outcomes_accessed") is not True:
        raise ValueError("post-Test evidence specification must disclose Test access")
    files = verify_declared_sources(root, spec["sources"])
    evidence_id, manifest_digest = evidence_identity(files)
    cells, anomalies = load_declared_cells(root, spec["sources"])
    validate_expected_matrix(cells, spec["expected_matrix"])

    formal_config = _load_yaml(root / Path(spec["formal_config"]))
    for split, manifest_name in spec["split_manifests"].items():
        manifest = load_split_manifest(root / Path(manifest_name))
        if manifest.split != split:
            raise ValueError(f"split manifest identity mismatch: {manifest_name}")
        plan = build_v2_cell_plan(
            formal_config,
            [row.id for row in manifest.scenarios],
            manifest.seeds[: int(formal_config["primary_seeds"])],
            "primary",
            allow_held_out=True,
        )
        results = [
            row for row in cells if row["manifest_split"] == split
        ]
        validate_plan_completeness(
            plan,
            [
                FormalV2CellResult.model_validate(
                    {key: value for key, value in row.items() if key != "manifest_split"}
                )
                for row in results
            ],
        )

    freeze_checks = {}
    for relative in spec["freeze_directories"]:
        errors = verify_freeze(root / Path(relative))
        freeze_checks[Path(relative).name] = {"valid": not errors, "errors": errors}
    if not all(row["valid"] for row in freeze_checks.values()):
        raise ValueError(f"formal source freeze verification failed: {freeze_checks}")

    summary_anomalies = []
    for source in spec["sources"]:
        if source["kind"] != "summary":
            continue
        value = json.loads((root / source["path"]).read_text(encoding="utf-8"))
        if value.get("complete") is not True or int(value.get("cells", -1)) != 80:
            raise ValueError(f"formal summary is incomplete: {source['path']}")
        if value.get("test_outcomes_accessed") is not True:
            summary_anomalies.append(
                {
                    "type": "summary_test_access_flag_false",
                    "path": Path(source["path"]).as_posix(),
                    "observed": value.get("test_outcomes_accessed"),
                    "derived_interpretation": True,
                }
            )

    journal = summarize_journals(root, spec["sources"], cells)
    manifest = {
        "schema": "shiftmem-formal-v2-evidence-manifest-v1",
        "evidence_freeze_id": evidence_id,
        "manifest_sha256": manifest_digest,
        "test_outcomes_accessed": True,
        "raw_evidence_mutated": False,
        "complete": True,
        "cells": len(cells),
        "files": files,
        "freeze_verification": freeze_checks,
        "source_metadata_anomalies": {
            "affected_records": sum(row["affected_cells"] for row in anomalies)
            + len(summary_anomalies),
            "source_entries": len(anomalies) + len(summary_anomalies),
            "cell_flags": anomalies,
            "summary_flags": summary_anomalies,
            "effect_on_numeric_outcomes": "none",
            "repair_policy": "preserve raw bytes and disclose corrected interpretation only in derived artifacts",
        },
    }
    analysis = build_statistical_analysis(cells, evidence_id)
    expected_pairs = int(spec["expected_matrix"]["primary_pairs"])
    if analysis["primary_endpoint"]["overall"]["n"] != expected_pairs:
        raise ValueError("primary paired sample count mismatch")
    reliability = build_reliability_audit(cells, journal, evidence_id)
    return manifest, analysis, reliability


def _same_json(path: Path, expected: dict[str, Any]) -> bool:
    return path.is_file() and json.loads(path.read_text(encoding="utf-8")) == expected


def verify_outputs(root: Path, spec_path: Path = DEFAULT_SPEC) -> list[str]:
    manifest, analysis, reliability = build_outputs(root, spec_path)
    checks = [
        (root / DEFAULT_MANIFEST, manifest),
        (root / DEFAULT_ANALYSIS, analysis),
        (root / DEFAULT_RELIABILITY, reliability),
    ]
    return [str(path.relative_to(root)) for path, expected in checks if not _same_json(path, expected)]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.verify:
        mismatched = verify_outputs(root, args.spec)
        print(json.dumps({"valid": not mismatched, "mismatched_outputs": mismatched}, indent=2))
        return int(bool(mismatched))
    manifest, analysis, reliability = build_outputs(root, args.spec)
    atomic_write_json(root / DEFAULT_MANIFEST, manifest)
    atomic_write_json(root / DEFAULT_ANALYSIS, analysis)
    atomic_write_json(root / DEFAULT_RELIABILITY, reliability)
    print(
        json.dumps(
            {
                "complete": True,
                "evidence_freeze_id": manifest["evidence_freeze_id"],
                "cells": manifest["cells"],
                "primary_pairs": analysis["primary_endpoint"]["overall"]["n"],
                "outputs": [str(DEFAULT_MANIFEST), str(DEFAULT_ANALYSIS), str(DEFAULT_RELIABILITY)],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
