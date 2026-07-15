"""Offline tests for the strategy-schema qualification runner (no network)."""

import json
from pathlib import Path

import pytest

from shiftmem.agents.base import StrategyProposal
from shiftmem.evaluation.qualification_run import build_run_metadata
from shiftmem.evaluation.strategy_qualification import (
    build_strategy_qualification_cases,
)
from shiftmem.providers.inventory_prompt import (
    INVENTORY_DECISION_SYSTEM_PROMPT,
    STRATEGY_REVIEW_SYSTEM_PROMPT,
    build_inventory_user_message,
    build_strategy_review_user_message,
)
from scripts.qualify_models import (
    _default_provider_factory,
    _default_strategy_provider_factory,
    execute_strategy_qualification,
    run_strategy_case,
)


class _FakeProvider:
    """Return a fixed proposal for every request; counts calls."""

    def __init__(self, proposal: StrategyProposal):
        self._text = proposal.model_dump_json()
        self.calls = 0

    def generate(self, request):
        from shiftmem.providers.base import ProviderResponse

        self.calls += 1
        return ProviderResponse(text=self._text, input_tokens=100, output_tokens=30, latency_ms=1.0)


def _good_proposal():
    return StrategyProposal(
        forecast_window=14, safety_stock_multiplier=2.0, lead_time_buffer=1,
        used_memory_ids=[], confidence=0.6, reason="ok",
    )


def test_run_strategy_case_parses_proposal_and_counts_tokens():
    provider = _FakeProvider(_good_proposal())
    case = build_strategy_qualification_cases()[0]
    result = provider, case
    outcome = run_strategy_case(provider, case, repetition=0)
    assert outcome.proposal is not None
    assert outcome.input_tokens == 100
    assert outcome.fallback_used is False
    assert provider.calls == 1


def test_run_strategy_case_falls_back_after_two_bad_outputs():
    from shiftmem.providers.local import ScriptedProvider

    provider = ScriptedProvider(["nonsense", "still bad"])
    case = build_strategy_qualification_cases()[0]
    outcome = run_strategy_case(provider, case, repetition=0)
    assert outcome.fallback_used is True
    assert outcome.proposal is None


def test_corrected_case_preserves_failed_and_successful_attempts():
    from shiftmem.providers.local import ScriptedProvider

    provider = ScriptedProvider(["not-json", _good_proposal().model_dump_json()])
    case = build_strategy_qualification_cases()[0]

    outcome = run_strategy_case(provider, case, repetition=0)

    assert outcome.fallback_used is False
    assert len(outcome.attempts) == 2
    assert outcome.attempts[0].raw_output == "not-json"
    assert outcome.attempts[0].error is not None
    assert outcome.attempts[1].error is None


def test_strategy_factory_uses_strategy_prompt_and_builder():
    provider = _default_strategy_provider_factory(
        "siliconflow", "deepseek-ai/DeepSeek-V3.2"
    )
    assert provider.system_prompt == STRATEGY_REVIEW_SYSTEM_PROMPT
    assert provider.build_user_message is build_strategy_review_user_message


def test_order_factory_remains_on_archived_order_prompt():
    provider = _default_provider_factory("siliconflow", "model")
    assert provider.system_prompt == INVENTORY_DECISION_SYSTEM_PROMPT
    assert provider.build_user_message is build_inventory_user_message


def test_existing_outputs_are_rejected_before_provider_creation(tmp_path: Path):
    raw = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    raw.write_text("existing\n", encoding="utf-8")
    created = 0

    def factory(profile, model_id):
        nonlocal created
        created += 1
        return _FakeProvider(_good_proposal())

    config = {
        "repetitions": 2,
        "models": [
            {
                "label": "fake",
                "profile": "offline",
                "model_id": "fake/model",
            }
        ],
    }

    with pytest.raises(FileExistsError):
        execute_strategy_qualification(config, raw, summary, provider_factory=factory)

    assert created == 0
    assert raw.read_text(encoding="utf-8") == "existing\n"


def test_run_metadata_hashes_config_and_prompt():
    metadata = build_run_metadata(
        run_id="qual-001",
        schema="strategy",
        config_bytes=b"models: []\n",
        system_prompt="strategy prompt",
        builder_name="build_strategy_review_user_message",
    )
    assert metadata.run_id == "qual-001"
    assert len(metadata.config_sha256) == 64
    assert len(metadata.system_prompt_sha256) == 64


def test_execute_writes_run_metadata_and_attempt_evidence(tmp_path: Path):
    raw = tmp_path / "raw.jsonl"
    summary = tmp_path / "summary.json"
    config = {
        "repetitions": 2,
        "models": [
            {
                "label": "fake",
                "profile": "offline",
                "model_id": "fake/model",
            }
        ],
    }

    execute_strategy_qualification(
        config,
        raw,
        summary,
        provider_factory=lambda profile, model_id: _FakeProvider(_good_proposal()),
        run_id="qual-test-001",
    )

    raw_rows = [json.loads(line) for line in raw.read_text(encoding="utf-8").splitlines()]
    aggregate = json.loads(summary.read_text(encoding="utf-8"))
    assert len(raw_rows) == 12
    assert all(row["run_id"] == "qual-test-001" for row in raw_rows)
    assert all(len(row["attempts"]) == 1 for row in raw_rows)
    assert aggregate["run_metadata"]["run_id"] == "qual-test-001"
    assert aggregate["models"][0]["attempt_count"] == 12
