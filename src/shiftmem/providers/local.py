"""Offline providers for deterministic development and tests."""

from collections.abc import Iterable
from time import perf_counter

from shiftmem.agents.base import AgentDecision

from .base import ProviderRequest, ProviderResponse


class ScriptedProvider:
    """Return preconfigured raw outputs for parsing and retry tests."""

    def __init__(self, outputs: Iterable[str]) -> None:
        self._outputs = iter(outputs)

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        text = next(self._outputs)
        return ProviderResponse(
            text=text,
            input_tokens=len(request.model_dump_json().split()),
            output_tokens=len(text.split()),
            latency_ms=0,
        )


class DeterministicProvider:
    """Transparent heuristic provider used only for offline integration."""

    def __init__(self, target_inventory: int = 60) -> None:
        if target_inventory < 0:
            raise ValueError("target_inventory must be non-negative")
        self.target_inventory = target_inventory

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()
        inventory = int(request.observation["inventory"])
        pipeline = int(request.observation.get("pipeline_inventory", 0))
        quantity = max(0, self.target_inventory - inventory - pipeline)
        decision = AgentDecision(
            order_quantity=quantity,
            used_memory_ids=[],
            confidence=1.0,
            reason="Deterministic offline base-stock heuristic.",
        )
        text = decision.model_dump_json()
        return ProviderResponse(
            text=text,
            input_tokens=len(request.model_dump_json().split()),
            output_tokens=len(text.split()),
            latency_ms=(perf_counter() - started) * 1000,
        )
