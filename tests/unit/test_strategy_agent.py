"""Tests for the v2 low-frequency strategy-review agent."""

import pytest
from pydantic import ValidationError

from shiftmem.agents.base import StrategyProposal
from shiftmem.agents.strategy_agent import StrategyReviewAgent
from shiftmem.control.controller import StrategyParameters
from shiftmem.memory.store import NoMemory
from shiftmem.providers.base import ProviderResponse, StrategyProviderRequest
from shiftmem.providers.local import DeterministicStrategyProvider, ScriptedProvider


def _observation():
    return {
        "day": 5,
        "inventory": 40,
        "pipeline_inventory": 10,
        "pipeline_orders": [],
        "quoted_lead_time": 2,
        "last_demand": 22,
        "last_sales": 22,
        "costs": {"purchase": 1.0, "holding": 0.1, "stockout": 2.0, "fixed_order": 0.0},
        "recent_history": [
            {"day": d, "demand": 20, "sales": 20, "lost_sales": 0,
             "ending_inventory": 40, "order_quantity": 20, "arrivals": 20,
             "total_cost": 0.0}
            for d in range(5)
        ],
    }


class _CapturingProvider:
    def __init__(self, output: str):
        self.output = output
        self.requests = []

    def generate(self, request):
        self.requests.append(request)
        return ProviderResponse(
            text=self.output,
            input_tokens=10,
            output_tokens=5,
            latency_ms=1.0,
        )


def test_strategy_proposal_forbids_order_quantity():
    with pytest.raises(ValidationError):
        StrategyProposal.model_validate(
            {
                "forecast_window": 14,
                "safety_stock_multiplier": 1.2,
                "lead_time_buffer": 1,
                "order_quantity": 30,
                "used_memory_ids": [],
                "confidence": 0.5,
                "reason": "x",
            }
        )


def test_strategy_proposal_valid_fields():
    proposal = StrategyProposal(
        forecast_window=10,
        safety_stock_multiplier=1.5,
        lead_time_buffer=2,
        used_memory_ids=[],
        confidence=0.6,
        reason="More buffer under rising demand.",
    )
    assert proposal.forecast_window == 10


def test_agent_returns_clamped_strategy_parameters():
    provider = DeterministicStrategyProvider()
    agent = StrategyReviewAgent(provider=provider, memory=NoMemory())
    current = StrategyParameters()
    result = agent.review(_observation(), current, trigger_reason="periodic")
    assert isinstance(result, StrategyParameters)


def test_agent_retains_previous_strategy_after_two_invalid_outputs():
    provider = ScriptedProvider(["not json", "still not json"])
    agent = StrategyReviewAgent(provider=provider, memory=NoMemory())
    current = StrategyParameters(forecast_window=7, safety_stock_multiplier=1.1, lead_time_buffer=0)
    result = agent.review(_observation(), current, trigger_reason="periodic")
    assert result == current
    assert agent.logs[-1].fallback_used is True


def test_agent_rejects_unsupplied_memory_citation():
    payload = StrategyProposal(
        forecast_window=12,
        safety_stock_multiplier=1.3,
        lead_time_buffer=1,
        used_memory_ids=["ghost-memory"],
        confidence=0.5,
        reason="cites a memory that was never supplied",
    ).model_dump_json()
    provider = ScriptedProvider([payload, payload])
    agent = StrategyReviewAgent(provider=provider, memory=NoMemory())
    current = StrategyParameters()
    result = agent.review(_observation(), current, trigger_reason="periodic")
    # Citation of an unsupplied memory is invalid, so the previous strategy stays.
    assert result == current
    assert agent.logs[-1].fallback_used is True


def test_agent_clamps_out_of_bounds_proposal():
    payload = StrategyProposal.model_construct(
        forecast_window=999,
        safety_stock_multiplier=99.0,
        lead_time_buffer=999,
        used_memory_ids=[],
        confidence=0.5,
        reason="extreme proposal",
    ).model_dump_json()
    provider = ScriptedProvider([payload, payload])
    agent = StrategyReviewAgent(provider=provider, memory=NoMemory())
    result = agent.review(
        _observation(),
        StrategyParameters(),
        trigger_reason="event",
        trigger_evidence={"variable": "demand"},
    )
    bounds = StrategyParameters.bounds()
    assert result.forecast_window <= bounds["forecast_window"][1]
    assert result.safety_stock_multiplier <= bounds["safety_stock_multiplier"][1]
    assert result.lead_time_buffer <= bounds["lead_time_buffer"][1]


def test_deterministic_strategy_provider_emits_no_order_quantity():
    provider = DeterministicStrategyProvider()
    response = provider.generate(
        StrategyProviderRequest(
            observation=_observation(),
            memory=[],
            current_strategy=StrategyParameters().model_dump(),
            trigger_reason="periodic",
            trigger_evidence={},
        )
    )
    assert isinstance(response, ProviderResponse)
    proposal = StrategyProposal.model_validate_json(response.text)
    assert not hasattr(proposal, "order_quantity")


def test_agent_forwards_current_strategy_and_trigger_evidence():
    proposal = StrategyProposal(
        forecast_window=7,
        safety_stock_multiplier=1.5,
        lead_time_buffer=2,
        used_memory_ids=[],
        confidence=0.8,
        reason="Respond to lost-sales evidence.",
    )
    provider = _CapturingProvider(proposal.model_dump_json())
    agent = StrategyReviewAgent(provider=provider, memory=NoMemory())
    current = StrategyParameters()
    evidence = {"variable": "lost_sales", "day": 4}

    agent.review(_observation(), current, "event", evidence)

    sent = provider.requests[0]
    assert isinstance(sent, StrategyProviderRequest)
    assert sent.current_strategy == current.model_dump()
    assert sent.trigger_reason == "event"
    assert sent.trigger_evidence == evidence
    assert agent.logs[-1].trigger_evidence == evidence
