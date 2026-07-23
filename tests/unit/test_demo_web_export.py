from __future__ import annotations

import hashlib
import json
from pathlib import Path

from demo.export_web import export_web_evidence


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_web_export_is_manifest_driven_and_deterministic(tmp_path: Path) -> None:
    output = tmp_path / "evidence"

    first = export_web_evidence(output)
    first_index_hash = _sha256(output / "index.json")
    sample_path = output / first["cells"][0]["path"]
    first_sample_hash = _sha256(sample_path)

    second = export_web_evidence(output)

    assert first["evidenceId"] == "v2-formal-results-f4ab41daacf3"
    assert first["verification"] == {"valid": True, "checkedFiles": 5}
    assert first["counts"] == {
        "cells": 160,
        "completePairs": 80,
        "primaryPairs": 70,
    }
    assert len(first["cells"]) == 160
    assert len(list((output / "cells").glob("*.json"))) == 160
    assert first == second
    assert _sha256(output / "index.json") == first_index_hash
    assert _sha256(sample_path) == first_sample_hash

    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    assert sample["provenance"]["complete"] is True
    assert sample["days"] == len(sample["environment"]) == 150
    assert len(sample["decisions"]) == 150
    assert len(sample["scheduler"]) == 150
    assert [event["day"] for event in sample["events"]] == sorted(
        event["day"] for event in sample["events"]
    )
