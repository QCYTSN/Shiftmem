from pathlib import Path

import pytest

from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import BudgetLimits, RunIdentity
from shiftmem.providers.base import ProviderRequest, ProviderResponse
from shiftmem.providers.compatible_api import ProviderError
from shiftmem.providers.journaled import JournaledProvider


class FakeProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        return ProviderResponse(
            text='{"order_quantity": 1}', input_tokens=100, output_tokens=20, latency_ms=5
        )


class FailingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        raise ProviderError("sanitized failure")


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
