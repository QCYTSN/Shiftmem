"""Low-frequency strategy-review agent for protocol v2.

The agent runs only on scheduler-approved review days. It retrieves memory,
asks the provider for a bounded ``StrategyProposal``, validates and clamps it,
and returns the active ``StrategyParameters``. It never emits a daily order and
never changes the review schedule or controller formula. On repeated invalid
output it retains the previous validated strategy as the safe fallback.
"""

import json
from typing import Any, Literal, Protocol

from pydantic import ValidationError

from shiftmem.control.controller import StrategyParameters
from shiftmem.memory.store import MemoryStore
from shiftmem.providers.base import ModelProvider, StrategyProviderRequest

from .base import ProviderAttemptLog, StrategyProposal, StrategyReviewLog


class MemoryLike(Protocol):
    def retrieve(self, query: str, step: int, top_k: int) -> list[Any]: ...


class StrategyReviewAgent:
    """Validate a bounded strategy proposal, retry once, then retain previous."""

    def __init__(
        self,
        provider: ModelProvider,
        memory: MemoryStore,
        top_k: int = 5,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.provider = provider
        self.memory = memory
        self.top_k = top_k
        self.logs: list[StrategyReviewLog] = []

    def review(
        self,
        observation: dict[str, Any],
        current_strategy: StrategyParameters,
        trigger_reason: Literal["periodic", "event", "coalesced"],
        trigger_evidence: dict[str, Any] | None = None,
    ) -> StrategyParameters:
        query = json.dumps(observation, sort_keys=True)
        day = int(observation["day"])
        records = self.memory.retrieve(query, day, self.top_k)
        supplied_ids = [record.memory_id for record in records]

        attempts: list[ProviderAttemptLog] = []
        proposal: StrategyProposal | None = None
        cited_ids: list[str] = []
        correction: str | None = None

        for _ in range(2):
            request = StrategyProviderRequest(
                observation=observation,
                memory=[record.model_dump() for record in records],
                correction=correction,
                current_strategy=current_strategy.model_dump(),
                trigger_reason=trigger_reason,
                trigger_evidence=dict(trigger_evidence or {}),
            )
            try:
                response = self.provider.generate(request)
            except Exception as error:
                correction = "The provider failed. Retry the same strategy proposal request."
                attempts.append(
                    ProviderAttemptLog(
                        raw_output="",
                        input_tokens=0,
                        output_tokens=0,
                        latency_ms=0,
                        parse_error=f"provider failure: {type(error).__name__}: {error}",
                    )
                )
                continue

            parse_error: str | None = None
            try:
                candidate = StrategyProposal.model_validate_json(response.text)
                unknown = set(candidate.used_memory_ids) - set(supplied_ids)
                if unknown:
                    raise ValueError(
                        f"proposal referenced unsupplied memories: {sorted(unknown)}"
                    )
                proposal = candidate
                cited_ids = list(candidate.used_memory_ids)
            except (ValidationError, ValueError) as error:
                parse_error = str(error)
                correction = (
                    "Return only valid StrategyProposal JSON with forecast_window, "
                    "safety_stock_multiplier, lead_time_buffer, used_memory_ids, "
                    "confidence, and reason. Do not include order_quantity."
                )
            attempts.append(
                ProviderAttemptLog(
                    raw_output=response.text,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    latency_ms=response.latency_ms,
                    parse_error=parse_error,
                )
            )
            if proposal is not None:
                break

        clamped = False
        if proposal is None:
            active = current_strategy
            fallback_used = True
        else:
            active = StrategyParameters.clamp_revision(
                current_strategy,
                forecast_window=proposal.forecast_window,
                safety_stock_multiplier=proposal.safety_stock_multiplier,
                lead_time_buffer=proposal.lead_time_buffer,
            )
            clamped = (
                active.forecast_window != proposal.forecast_window
                or active.safety_stock_multiplier != proposal.safety_stock_multiplier
                or active.lead_time_buffer != proposal.lead_time_buffer
            )
            fallback_used = False

        self.logs.append(
            StrategyReviewLog(
                day=day,
                trigger_reason=trigger_reason,
                trigger_evidence=dict(trigger_evidence or {}),
                supplied_memory_ids=supplied_ids,
                cited_memory_ids=cited_ids,
                proposal=proposal,
                active_strategy=active.model_dump(),
                clamped=clamped,
                attempts=attempts,
                attempt_count=len(attempts),
                parse_failure_count=sum(
                    attempt.parse_error is not None for attempt in attempts
                ),
                fallback_used=fallback_used,
                total_input_tokens=sum(attempt.input_tokens for attempt in attempts),
                total_output_tokens=sum(attempt.output_tokens for attempt in attempts),
                total_latency_ms=sum(attempt.latency_ms for attempt in attempts),
            )
        )
        return active
