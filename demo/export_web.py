"""Export verified formal evidence into deterministic web-facing view models.

The TypeScript Demo never reads historical run folders directly. This adapter
reuses :mod:`demo.data` so the browser receives only complete cells declared by
the frozen evidence manifest, after SHA-256 verification succeeds.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import shutil
from typing import Any, Mapping, Sequence

from demo.data import (
    DEFAULT_MANIFEST,
    DEFAULT_STATISTICS,
    EvidenceBundle,
    EvidenceCell,
    events_for_cell,
    load_evidence,
    load_statistics,
)


WEB_SCHEMA_VERSION = 1
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "demo-web/public/evidence"


def export_web_evidence(
    output_dir: str | Path = DEFAULT_OUTPUT,
    *,
    manifest_path: str | Path = DEFAULT_MANIFEST,
    statistics_path: str | Path = DEFAULT_STATISTICS,
) -> Mapping[str, Any]:
    """Write a deterministic, split-by-cell evidence bundle for the web Demo."""

    bundle = load_evidence(manifest_path, verify_hashes=True)
    statistics = load_statistics(statistics_path)
    destination = Path(output_dir).resolve()
    cells_dir = destination / "cells"

    if destination.exists():
        shutil.rmtree(destination)
    cells_dir.mkdir(parents=True, exist_ok=True)

    index_cells: list[dict[str, Any]] = []
    for cell in sorted(bundle.cells, key=_cell_sort_key):
        relative = f"cells/{cell.cell_id}.json"
        payload = _cell_view_model(cell)
        _write_json(destination / relative, payload)
        index_cells.append(_cell_index_entry(cell, relative))

    index = {
        "schemaVersion": WEB_SCHEMA_VERSION,
        "evidenceId": bundle.evidence_id,
        "verification": {
            "valid": bundle.verification.valid,
            "checkedFiles": bundle.verification.checked,
        },
        "counts": {
            "cells": len(bundle.cells),
            "completePairs": bundle.complete_pair_count,
            "primaryPairs": bundle.primary_pair_count,
        },
        "cells": index_cells,
    }
    _write_json(destination / "index.json", index)
    _write_json(
        destination / "statistics.json",
        {
            "schemaVersion": WEB_SCHEMA_VERSION,
            "evidenceId": bundle.evidence_id,
            "statistics": statistics,
        },
    )
    return index


def _cell_view_model(cell: EvidenceCell) -> dict[str, Any]:
    payload = cell.payload
    return {
        "schemaVersion": WEB_SCHEMA_VERSION,
        "id": cell.cell_id,
        "split": cell.split,
        "scenarioId": str(payload["scenario_id"]),
        "model": str(payload["model"]),
        "seed": int(payload["seed"]),
        "method": cell.method,
        "methodLabel": cell.method_label,
        "days": cell.days,
        "shiftDay": cell.shift_day,
        "endpointApplicable": cell.endpoint_applicable,
        "postShiftRegret30": payload.get("post_shift_cumulative_regret_30"),
        "metrics": payload.get("inventory_metrics", {}),
        "environment": payload.get("environment_records", []),
        "decisions": payload.get("daily_decision_log", []),
        "scheduler": payload.get("scheduler_log", []),
        "reviews": payload.get("review_logs", []),
        "memoryAudit": payload.get("memory_audit") or {},
        "events": [asdict(event) for event in events_for_cell(cell)],
        "provenance": {
            "source": cell.source,
            "complete": bool(payload.get("complete", False)),
            "testOutcomesAccessed": payload.get("test_outcomes_accessed"),
        },
    }


def _cell_index_entry(cell: EvidenceCell, relative_path: str) -> dict[str, Any]:
    payload = cell.payload
    return {
        "id": cell.cell_id,
        "split": cell.split,
        "scenarioId": str(payload["scenario_id"]),
        "model": str(payload["model"]),
        "seed": int(payload["seed"]),
        "method": cell.method,
        "methodLabel": cell.method_label,
        "days": cell.days,
        "shiftDay": cell.shift_day,
        "endpointApplicable": cell.endpoint_applicable,
        "path": relative_path,
    }


def _cell_sort_key(cell: EvidenceCell) -> tuple[str, str, str, int, str]:
    return (
        cell.split,
        str(cell.payload["scenario_id"]),
        str(cell.payload["model"]),
        int(cell.payload["seed"]),
        cell.method,
    )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export verified formal evidence for the TypeScript Demo."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--statistics", type=Path, default=DEFAULT_STATISTICS)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    index = export_web_evidence(
        args.output,
        manifest_path=args.manifest,
        statistics_path=args.statistics,
    )
    print(
        f"exported {index['counts']['cells']} verified cells "
        f"for {index['evidenceId']} to {args.output.resolve()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
