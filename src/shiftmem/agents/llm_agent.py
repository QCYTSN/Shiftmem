"""Structured provider-backed inventory agent with safe fallback."""

import json
from typing import Any, Protocol

from pydantic import ValidationError

from shiftmem.memory.schemas import MemoryRecord
from shiftmem.memory.store import MemoryStore
from shiftmem.providers.base import ModelProvider, ProviderRequest

from .base import AgentDecision, DecisionLog, ProviderAttemptLog


class FallbackPolicy(Protocol):
    def act(self, observation: dict[str, int]) -> dict[str, int | str]: ...


class StructuredAgent:
    """Validate structured output, retry once, then use a safe policy."""

    def __init__(
        self,
        provider: ModelProvider,
        memory: MemoryStore,
        fallback: FallbackPolicy,
        top_k: int = 5,
    ) -> None:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        self.provider = provider
        self.memory = memory
        self.fallback = fallback
        self.top_k = top_k
        self.logs: list[DecisionLog] = []

    def act(self, observation: dict[str, int]) -> AgentDecision:
        query = json.dumps(observation, sort_keys=True)
        records = self.memory.retrieve(query, observation["day"], self.top_k)
        supplied_ids = [record.memory_id for record in records]
        attempts: list[ProviderAttemptLog] = []
        decision: AgentDecision | None = None
        correction: str | None = None

        for _ in range(2):
            request = ProviderRequest(
                observation=observation,
                memory=[record.model_dump() for record in records],
                correction=correction,
            )
            try:
                response = self.provider.generate(request)
            except Exception as error:
                correction = "The provider failed. Retry the same structured decision request."
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
                candidate = AgentDecision.model_validate_json(response.text)
                unknown = set(candidate.used_memory_ids) - set(supplied_ids)
                if unknown:
                    raise ValueError(f"decision referenced unsupplied memories: {sorted(unknown)}")
                decision = candidate
            except (ValidationError, ValueError) as error:
                parse_error = str(error)
                correction = "Return only valid AgentDecision JSON using supplied memory IDs."
            attempts.append(
                ProviderAttemptLog(
                    raw_output=response.text,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    latency_ms=response.latency_ms,
                    parse_error=parse_error,
                )
            )
            if decision is not None:
                break

        fallback_used = decision is None
        if decision is None:
            action = self.fallback.act(observation)
            decision = AgentDecision(
                order_quantity=int(action["order_quantity"]),
                supplier_id=str(action["supplier_id"]),
                used_memory_ids=[],
                confidence=0,
                reason="Safe fallback after two invalid provider outputs.",
            )

        self.logs.append(
            DecisionLog(
                step=observation["day"],
                supplied_memory_ids=supplied_ids,
                decision=decision,
                attempts=attempts,
                attempt_count=len(attempts),
                parse_failure_count=sum(attempt.parse_error is not None for attempt in attempts),
                fallback_used=fallback_used,
                total_input_tokens=sum(attempt.input_tokens for attempt in attempts),
                total_output_tokens=sum(attempt.output_tokens for attempt in attempts),
                total_latency_ms=sum(attempt.latency_ms for attempt in attempts),
            )
        )
        return decision

    def observe(self, record: dict[str, Any]) -> None:
        step = int(record["day"])
        text = (
            f"Day {step}: demand {record['demand']}, sales {record['sales']}, "
            f"lost sales {record['lost_sales']}, ending inventory "
            f"{record['ending_inventory']}, total cost {record['total_cost']}."
        )
        self.memory.add(
            MemoryRecord(
                memory_id=f"observation-{step}",
                step=step,
                text=text,
                variables=["demand", "sales", "inventory", "cost"],
                payload=record.copy(),
            )
        )
