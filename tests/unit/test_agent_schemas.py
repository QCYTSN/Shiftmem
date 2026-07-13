import pytest
from pydantic import ValidationError

from shiftmem.agents.base import AgentDecision
from shiftmem.providers.base import ProviderRequest, ProviderResponse
from shiftmem.providers.local import DeterministicProvider, ScriptedProvider


def test_agent_decision_validates_action_and_confidence() -> None:
    decision = AgentDecision(order_quantity=12, confidence=0.7, reason="test")
    assert decision.to_action() == {"order_quantity": 12, "supplier_id": "standard"}
    with pytest.raises(ValidationError):
        AgentDecision(order_quantity=-1, confidence=0.7, reason="bad")
    with pytest.raises(ValidationError):
        AgentDecision(order_quantity=1, confidence=1.2, reason="bad")


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
