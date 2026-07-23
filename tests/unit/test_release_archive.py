from pathlib import Path

from scripts.verify_release_archive import verify_release_archive


ROOT = Path(__file__).parents[2]


def test_tracked_release_archive_matches_the_evidence_manifest() -> None:
    result = verify_release_archive(ROOT)

    assert result["valid"] is True
    assert result["evidence_freeze_id"] == "v2-formal-results-f4ab41daacf3"
    assert result["declared_files"] == 11
    assert result["errors"] == []
