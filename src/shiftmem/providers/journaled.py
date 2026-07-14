"""Idempotent provider wrapper backed by the formal decision journal."""

from __future__ import annotations

import hashlib
import json

from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import DecisionJournalEntry

from .base import ModelProvider, ProviderRequest, ProviderResponse


class JournaledProvider:
    def __init__(
        self,
        delegate: ModelProvider,
        journal: JsonlRunJournal,
        input_cny_per_million: float,
        output_cny_per_million: float,
    ) -> None:
        self.delegate = delegate
        self.journal = journal
        self.input_rate = float(input_cny_per_million)
        self.output_rate = float(output_cny_per_million)
        self._cell_id: str | None = None
        self._day: int | None = None
        self._attempt = 0

    def set_decision(self, cell_id: str, day: int) -> None:
        self._cell_id = cell_id
        self._day = int(day)
        self._attempt = 0

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if self._cell_id is None or self._day is None:
            raise RuntimeError("set_decision must be called before generate")
        decision_id = f"{self._cell_id}:day-{self._day}:attempt-{self._attempt}"
        self._attempt += 1
        serialized = json.dumps(
            request.model_dump(mode="json"),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        request_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        replay = self.journal.lookup(decision_id)
        if replay is not None:
            if replay.request_hash != request_hash:
                raise ValueError("journaled request hash does not match replay request")
            return ProviderResponse.model_validate(replay.provider_response)
        response = self.delegate.generate(request)
        cost = (
            response.input_tokens * self.input_rate
            + response.output_tokens * self.output_rate
        ) / 1_000_000
        self.journal.append(
            DecisionJournalEntry(
                identity=self.journal.identity,
                cell_id=self._cell_id,
                decision_id=decision_id,
                request_hash=request_hash,
                provider_response=response.model_dump(mode="json"),
                calls=1,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                estimated_cost_cny=cost,
            )
        )
        return response
