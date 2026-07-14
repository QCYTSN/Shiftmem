import json
from pathlib import Path

import pytest

from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, DecisionJournalEntry, RunIdentity


def identity(run_id: str = "run-1") -> RunIdentity:
    return RunIdentity(
        run_id=run_id,
        freeze_id="phase4-v1-1-deadbeef",
        git_commit="a" * 40,
        config_hash="b" * 64,
    )


def entry(decision_id: str = "cell-1-day-0", **changes) -> DecisionJournalEntry:
    values = {
        "identity": identity(),
        "cell_id": "cell-1",
        "decision_id": decision_id,
        "request_hash": "c" * 64,
        "provider_response": {"text": "{}"},
        "calls": 1,
        "input_tokens": 10,
        "output_tokens": 2,
        "estimated_cost_cny": 0.01,
    }
    values.update(changes)
    return DecisionJournalEntry(**values)


def limits(**changes) -> BudgetLimits:
    values = {
        "max_calls": 2,
        "max_input_tokens": 100,
        "max_output_tokens": 50,
        "max_cost_cny": 1.0,
    }
    values.update(changes)
    return BudgetLimits(**values)


def test_journal_replays_completed_decision_and_rejects_duplicate(tmp_path: Path) -> None:
    journal = JsonlRunJournal(tmp_path / "run.jsonl", identity(), limits())
    journal.append(entry())

    assert journal.lookup("cell-1-day-0").provider_response == {"text": "{}"}
    with pytest.raises(ValueError, match="already journaled"):
        journal.append(entry())


def test_journal_rejects_identity_mismatch(tmp_path: Path) -> None:
    journal = JsonlRunJournal(tmp_path / "run.jsonl", identity(), limits())

    with pytest.raises(ValueError, match="identity"):
        journal.append(entry(identity=identity("other")))


def test_journal_recovers_only_a_truncated_final_line(tmp_path: Path) -> None:
    path = tmp_path / "run.jsonl"
    path.write_text(entry().model_dump_json() + "\n" + '{"truncated"', encoding="utf-8")

    journal = JsonlRunJournal(path, identity(), limits())
    journal.append(entry("cell-1-day-1"))

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2


def test_journal_fails_closed_before_budget_is_exceeded(tmp_path: Path) -> None:
    journal = JsonlRunJournal(tmp_path / "run.jsonl", identity(), limits(max_calls=1))
    journal.append(entry())

    with pytest.raises(ValueError, match="max_calls"):
        journal.append(entry("cell-1-day-1"))


def test_journal_rejects_secret_shaped_response_fields(tmp_path: Path) -> None:
    journal = JsonlRunJournal(tmp_path / "run.jsonl", identity(), limits())

    with pytest.raises(ValueError, match="secret field"):
        journal.append(entry(provider_response={"api_key": "must-not-persist"}))
