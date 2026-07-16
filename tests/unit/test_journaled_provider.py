from pathlib import Path

import pytest

from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, RunIdentity
from shiftmem.providers.base import ProviderRequest, ProviderResponse
from shiftmem.providers.compatible_api import ProviderError
from shiftmem.providers.journaled import JournaledProvider, JournalSafetyStop


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        return ProviderResponse(
            text='{"order_quantity": 1}', input_tokens=100, output_tokens=20, latency_ms=5
        )

    def token_budget_upper_bounds(self, request: ProviderRequest) -> tuple[int, int]:
        return 200, 50


class FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        raise ProviderError("sanitized failure")

    def token_budget_upper_bounds(self, request: ProviderRequest) -> tuple[int, int]:
        return 200, 50


def journal(path: Path) -> JsonlRunJournal:
    return JsonlRunJournal(
        path,
        RunIdentity(run_id="dry-run", freeze_id="freeze", git_commit="a" * 40, config_hash="b" * 64),
        BudgetLimits(max_calls=10, max_input_tokens=1000, max_output_tokens=1000, max_cost_cny=1),
    )


def test_journaled_provider_replays_without_second_live_call(tmp_path: Path) -> None:
    delegate = FakeProvider()
    request = ProviderRequest(observation={"day": 4}, memory=[])
    first = JournaledProvider(delegate, journal(tmp_path / "journal.jsonl"), 4.0, 6.0)
    first.set_decision("cell", 4)
    response = first.generate(request)

    resumed = JournaledProvider(delegate, journal(tmp_path / "journal.jsonl"), 4.0, 6.0)
    resumed.set_decision("cell", 4)
    replay = resumed.generate(request)

    assert response == replay
    assert delegate.calls == 1
    assert resumed.journal.totals()["cost_cny"] == pytest.approx(0.00052)


def test_journaled_provider_rejects_changed_request_for_replay(tmp_path: Path) -> None:
    delegate = FakeProvider()
    wrapped = JournaledProvider(delegate, journal(tmp_path / "journal.jsonl"), 4.0, 6.0)
    wrapped.set_decision("cell", 4)
    wrapped.generate(ProviderRequest(observation={"day": 4}, memory=[]))

    resumed = JournaledProvider(delegate, journal(tmp_path / "journal.jsonl"), 4.0, 6.0)
    resumed.set_decision("cell", 4)
    with pytest.raises(ValueError, match="request hash"):
        resumed.generate(ProviderRequest(observation={"day": 4, "inventory": 1}, memory=[]))


def test_failed_attempt_is_counted_and_replayed_without_new_call(tmp_path: Path) -> None:
    delegate = FailingProvider()
    request = ProviderRequest(observation={"day": 4}, memory=[])
    first = JournaledProvider(delegate, journal(tmp_path / "journal.jsonl"), 4.0, 6.0)
    first.set_decision("cell", 4)
    with pytest.raises(ProviderError, match="sanitized failure"):
        first.generate(request)

    resumed = JournaledProvider(delegate, journal(tmp_path / "journal.jsonl"), 4.0, 6.0)
    resumed.set_decision("cell", 4)
    with pytest.raises(ProviderError, match="journaled provider failure"):
        resumed.generate(request)

    assert delegate.calls == 1
    assert resumed.journal.totals()["calls"] == 1


def test_preflight_reservation_is_fsynced_then_replaced_by_actuals(tmp_path: Path) -> None:
    delegate = FakeProvider()
    wrapped = JournaledProvider(
        delegate,
        journal(tmp_path / "journal.jsonl"),
        4.0,
        6.0,
        require_preflight_reservation=True,
    )
    wrapped.set_decision("cell", 4)
    wrapped.generate(ProviderRequest(observation={"day": 4}, memory=[]))

    lines = (tmp_path / "journal.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert '"status":"reserved"' in lines[0]
    assert '"status":"complete"' in lines[1]
    assert wrapped.journal.totals()["input_tokens"] == 100


def test_preflight_stops_before_delegate_when_reservation_exceeds_budget(
    tmp_path: Path,
) -> None:
    delegate = FakeProvider()
    limited = JsonlRunJournal(
        tmp_path / "journal.jsonl",
        RunIdentity(
            run_id="dry-run",
            freeze_id="freeze",
            git_commit="a" * 40,
            config_hash="b" * 64,
        ),
        BudgetLimits(
            max_calls=10,
            max_input_tokens=199,
            max_output_tokens=1000,
            max_cost_cny=1,
        ),
    )
    wrapped = JournaledProvider(
        delegate, limited, 4.0, 6.0, require_preflight_reservation=True
    )
    wrapped.set_decision("cell", 4)

    with pytest.raises(JournalSafetyStop, match="max_input_tokens"):
        wrapped.generate(ProviderRequest(observation={"day": 4}, memory=[]))
    assert delegate.calls == 0
    assert not (tmp_path / "journal.jsonl").exists()


def test_unresolved_reservation_never_reissues_external_call(tmp_path: Path) -> None:
    target = journal(tmp_path / "journal.jsonl")
    request = ProviderRequest(observation={"day": 4}, memory=[])
    import hashlib
    import json

    request_hash = hashlib.sha256(
        json.dumps(
            request.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    from shiftmem.logging.schemas import DecisionJournalEntry

    target.reserve(
        DecisionJournalEntry(
            identity=target.identity,
            cell_id="cell",
            decision_id="cell:day-4:attempt-0",
            request_hash=request_hash,
            status="reserved",
            calls=1,
            input_tokens=200,
            output_tokens=50,
            estimated_cost_cny=0.0011,
        )
    )
    delegate = FakeProvider()
    resumed = JournaledProvider(
        delegate, target, 4.0, 6.0, require_preflight_reservation=True
    )
    resumed.set_decision("cell", 4)

    with pytest.raises(JournalSafetyStop, match="reconciliation"):
        resumed.generate(request)
    assert delegate.calls == 0


def test_preflight_failure_retains_conservative_reserved_cost(tmp_path: Path) -> None:
    delegate = FailingProvider()
    target = journal(tmp_path / "journal.jsonl")
    wrapped = JournaledProvider(
        delegate, target, 4.0, 6.0, require_preflight_reservation=True
    )
    wrapped.set_decision("cell", 4)
    with pytest.raises(ProviderError):
        wrapped.generate(ProviderRequest(observation={"day": 4}, memory=[]))

    totals = target.totals()
    assert totals["failed_attempts"] == 1
    assert totals["input_tokens"] == 200
    assert totals["output_tokens"] == 50
    assert totals["cost_cny"] == pytest.approx(0.0011)
