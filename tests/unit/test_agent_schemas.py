import pytest
from pydantic import ValidationError

from shiftmem.agents.base import AgentDecision
from shiftmem.providers.base import (
    ProviderRequest,
    ProviderResponse,
    StrategyProviderRequest,
)
from shiftmem.providers.local import DeterministicProvider, ScriptedProvider


def test_agent_decision_validates_action_and_confidence() -> None:
    decision = AgentDecision(order_quantity=12, confidence=0.7, reason="test")
    assert decision.to_action() == {"order_quantity": 12, "supplier_id": "standard"}
    with pytest.raises(ValidationError):
        AgentDecision(order_quantity=-1, confidence=0.7, reason="bad")
    with pytest.raises(ValidationError):
        AgentDecision(order_quantity=1, confidence=1.2, reason="bad")


def test_agent_decision_rejects_overlong_reason() -> None:
    with pytest.raises(ValidationError):
        AgentDecision(
            order_quantity=1,
            supplier_id="standard",
            used_memory_ids=[],
            confidence=0.5,
            reason="x" * 201,
        )


def test_provider_response_rejects_negative_usage() -> None:
    with pytest.raises(ValidationError):
        ProviderResponse(text="{}", input_tokens=-1, output_tokens=0, latency_ms=0)


def test_scripted_provider_returns_outputs_in_order() -> None:
    provider = ScriptedProvider(["first", "second"])
    request = ProviderRequest(observation={"inventory": 1}, memory=[])
    assert provider.generate(request).text == "first"
    assert provider.generate(request).text == "second"


def test_deterministic_provider_emits_valid_decision_json() -> None:
    provider = DeterministicProvider(target_inventory=30)
    response = provider.generate(
        ProviderRequest(
            observation={"inventory": 10, "pipeline_inventory": 5}, memory=[]
        )
    )
    decision = AgentDecision.model_validate_json(response.text)
    assert decision.order_quantity == 15


def test_strategy_review_prompt_asks_for_parameters_not_daily_order() -> None:
    from shiftmem.providers.inventory_prompt import (
        STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_strategy_review_user_message,
    )

    prompt = STRATEGY_REVIEW_SYSTEM_PROMPT
    assert "forecast_window" in prompt
    assert "safety_stock_multiplier" in prompt
    assert "lead_time_buffer" in prompt
    # The reviewer must be told never to emit a daily order.
    assert "order_quantity" in prompt and "Never return order_quantity" in prompt
    message = build_strategy_review_user_message(
        StrategyProviderRequest(
            observation={"day": 5},
            memory=[],
            current_strategy={
                "forecast_window": 14,
                "safety_stock_multiplier": 1.2,
                "lead_time_buffer": 1,
            },
            trigger_reason="event",
            trigger_evidence={"variable": "lost_sales", "day": 4},
        )
    )
    assert "strategy parameters" in message
    assert '"current_strategy"' in message
    assert '"trigger_reason": "event"' in message
    assert '"variable": "lost_sales"' in message


def test_archived_provider_request_shape_is_unchanged() -> None:
    request = ProviderRequest(observation={"day": 1}, memory=[])
    assert request.model_dump() == {
        "observation": {"day": 1},
        "memory": [],
        "correction": None,
    }


def test_strategy_request_requires_protocol_inputs() -> None:
    with pytest.raises(ValidationError):
        StrategyProviderRequest(observation={"day": 5}, memory=[])

    with pytest.raises(ValidationError):
        StrategyProviderRequest(
            observation={"day": 5},
            memory=[],
            current_strategy={"forecast_window": 14},
            trigger_reason="periodic",
            trigger_evidence={},
        )

    with pytest.raises(ValidationError):
        StrategyProviderRequest(
            observation={"day": 5},
            memory=[],
            current_strategy={
                "forecast_window": 14,
                "safety_stock_multiplier": 1.2,
                "lead_time_buffer": 1,
            },
            trigger_reason="event",
            trigger_evidence={},
        )


def test_strategy_prompt_discloses_joint_controller_target() -> None:
    from shiftmem.providers.inventory_prompt import STRATEGY_REVIEW_SYSTEM_PROMPT

    assert "quoted_lead_time + lead_time_buffer + 1" in STRATEGY_REVIEW_SYSTEM_PROMPT
    assert "sqrt(protection_periods)" in STRATEGY_REVIEW_SYSTEM_PROMPT
