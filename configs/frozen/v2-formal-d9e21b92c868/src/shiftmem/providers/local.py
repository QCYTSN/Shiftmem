"""Offline providers for deterministic development and tests."""

from collections.abc import Iterable
from time import perf_counter

from shiftmem.agents.base import AgentDecision, StrategyProposal

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


class DeterministicStrategyProvider:
    """Offline strategy-review provider used only for integration checks.

    It emits a valid ``StrategyProposal`` (never an ``order_quantity``) using a
    transparent heuristic over recent public demand. Like the direct-order
    deterministic provider, it deliberately ignores memory content, so its runs
    verify integration and auditability only and are not a memory-method result.
    """

    def __init__(
        self,
        forecast_window: int = 14,
        safety_stock_multiplier: float = 1.2,
        lead_time_buffer: int = 1,
    ) -> None:
        self.forecast_window = forecast_window
        self.safety_stock_multiplier = safety_stock_multiplier
        self.lead_time_buffer = lead_time_buffer

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()
        history = request.observation.get("recent_history") or []
        lost = sum(float(record.get("lost_sales", 0)) for record in history)
        # Transparent rule: raise the buffer when recent lost sales appear.
        multiplier = self.safety_stock_multiplier + (0.3 if lost > 0 else 0.0)
        proposal = StrategyProposal(
            forecast_window=self.forecast_window,
            safety_stock_multiplier=multiplier,
            lead_time_buffer=self.lead_time_buffer,
            used_memory_ids=[],
            confidence=1.0,
            reason="Deterministic offline strategy heuristic.",
        )
        text = proposal.model_dump_json()
        return ProviderResponse(
            text=text,
            input_tokens=len(request.model_dump_json().split()),
            output_tokens=len(text.split()),
            latency_ms=(perf_counter() - started) * 1000,
        )
