from pathlib import Path
import shutil

import pytest

from demo.data import (
    PairKey,
    cited_memories,
    day_snapshot,
    events_for_cell,
    load_evidence,
    next_event_day,
)


ROOT = Path(__file__).parents[2]
MANIFEST = ROOT / "artifacts/aggregated/v2_formal_evidence_manifest.json"


@pytest.fixture(scope="module")
def evidence():
    return load_evidence(MANIFEST, verify_hashes=True)


def test_manifest_loader_indexes_each_formal_cell_once(evidence) -> None:
    assert len(evidence.cells) == 160
    assert len(evidence.cells_by_id) == 160
    assert evidence.verification.valid
    assert evidence.verification.checked == 5
    assert evidence.evidence_id == "v2-formal-results-f4ab41daacf3"


def test_formal_pairs_are_complete_and_primary_population_is_70(evidence) -> None:
    assert evidence.complete_pair_count == 80
    assert evidence.primary_pair_count == 70
    assert all(set(pair) == {"shiftmem", "vector"} for pair in evidence.pairs.values())


def test_pair_filters_preserve_shared_context(evidence) -> None:
    splits = evidence.available_splits()
    assert splits == ("Test-ID", "Test-OOD")
    scenario = evidence.scenarios("Test-ID")[0]
    model = evidence.models("Test-ID", scenario)[0]
    seed = evidence.seeds("Test-ID", scenario, model)[0]
    key = PairKey("Test-ID", scenario, model, seed)
    pair = evidence.pair(key)
    assert {cell.pair_key for cell in pair.values()} == {key}


def test_episode_events_and_snapshot_trace_to_raw_records(evidence) -> None:
    cell = next(cell for cell in evidence.cells if cell.method == "shiftmem")
    events = events_for_cell(cell)
    assert events
    assert any(event.kind.startswith("review") for event in events)
    snapshot = day_snapshot(cell, 0)
    assert snapshot["environment"]["day"] == 0
    assert snapshot["decision"]["day"] == 0
    assert snapshot["scheduler"]["day"] == 0


def test_event_navigation_is_bounded(evidence) -> None:
    cell = next(cell for cell in evidence.cells if cell.method == "shiftmem")
    events = events_for_cell(cell)
    first = min(event.day for event in events)
    last = max(event.day for event in events)
    assert next_event_day(events, -1, forward=True) == first
    assert next_event_day(events, cell.days + 1, forward=False) == last
    assert next_event_day(events, last, forward=True) == last
    assert next_event_day(events, first, forward=False) == first


def test_cited_memory_records_match_review_ids(evidence) -> None:
    cell = next(
        cell
        for cell in evidence.cells
        if cell.method == "shiftmem"
        and any(row.get("cited_memory_ids") for row in cell.payload["review_logs"])
    )
    review = next(
        row for row in cell.payload["review_logs"] if row.get("cited_memory_ids")
    )
    records = cited_memories(cell, int(review["day"]))
    assert records
    assert {record["memory_id"] for record in records}.issubset(
        set(review["cited_memory_ids"])
    )


def test_clean_clone_loads_cells_from_verified_release_archive(tmp_path: Path) -> None:
    freeze_id = "v2-formal-results-f4ab41daacf3"
    source_release = ROOT / "artifacts/releases"
    clean_root = tmp_path / "clean-clone"
    aggregate_dir = clean_root / "artifacts/aggregated"
    release_dir = clean_root / "artifacts/releases"
    aggregate_dir.mkdir(parents=True)
    release_dir.mkdir(parents=True)
    (clean_root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")

    manifest_copy = aggregate_dir / MANIFEST.name
    shutil.copy2(MANIFEST, manifest_copy)
    for suffix in ("raw-evidence.zip", "raw-evidence.sha256.json"):
        name = f"{freeze_id}-{suffix}"
        shutil.copy2(source_release / name, release_dir / name)

    bundle = load_evidence(manifest_copy, verify_hashes=True)

    assert len(bundle.cells) == 160
    assert bundle.complete_pair_count == 80
    assert bundle.primary_pair_count == 70
    assert bundle.verification.valid
    assert bundle.verification.checked == 5
