"""Idempotent provider wrapper backed by the formal decision journal."""

from __future__ import annotations

import hashlib
import json

from shiftmem.logging.run_logger import JsonlRunJournal
from shiftmem.logging.schemas import DecisionJournalEntry

from .base import ModelProvider, ProviderRequest, ProviderResponse
from .compatible_api import ProviderError


class JournaledProvider:
    def __init__(
        self,
        delegate: ModelProvider,
        journal: JsonlRunJournal,
        input_cny_per_million: float,
        output_cny_per_million: float,
        *,
        require_preflight_reservation: bool = False,
        output_token_reservation_per_call: int | None = None,
    ) -> None:
        self.delegate = delegate
        self.journal = journal
        self.input_rate = float(input_cny_per_million)
        self.output_rate = float(output_cny_per_million)
        self.require_preflight_reservation = require_preflight_reservation
        if (
            output_token_reservation_per_call is not None
            and output_token_reservation_per_call < 1
        ):
            raise ValueError("output token reservation must be positive")
        self.output_token_reservation_per_call = output_token_reservation_per_call
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
            if replay.status == "failed":
                raise ProviderError(
                    f"journaled provider failure: {replay.error_type}"
                )
            if replay.status == "reserved":
                raise JournalSafetyStop(
                    f"unresolved provider reservation requires reconciliation: {decision_id}"
                )
            return ProviderResponse.model_validate(replay.provider_response)
        reservation: DecisionJournalEntry | None = None
        if self.require_preflight_reservation:
            bounds = getattr(self.delegate, "token_budget_upper_bounds", None)
            if not callable(bounds):
                raise JournalSafetyStop(
                    "live provider lacks token_budget_upper_bounds preflight"
                )
            max_input_tokens, max_output_tokens = bounds(request)
            if self.output_token_reservation_per_call is not None:
                max_output_tokens = max(
                    max_output_tokens, self.output_token_reservation_per_call
                )
            max_cost = (
                max_input_tokens * self.input_rate
                + max_output_tokens * self.output_rate
            ) / 1_000_000
            reservation = DecisionJournalEntry(
                identity=self.journal.identity,
                cell_id=self._cell_id,
                decision_id=decision_id,
                request_hash=request_hash,
                status="reserved",
                calls=1,
                input_tokens=max_input_tokens,
                output_tokens=max_output_tokens,
                estimated_cost_cny=max_cost,
            )
            try:
                self.journal.reserve(reservation)
            except ValueError as error:
                raise JournalSafetyStop(str(error)) from None
        try:
            response = self.delegate.generate(request)
        except Exception as error:
            failed = DecisionJournalEntry(
                identity=self.journal.identity,
                cell_id=self._cell_id,
                decision_id=decision_id,
                request_hash=request_hash,
                status="failed",
                error_type=type(error).__name__,
                calls=1,
                # A transport/provider exception may happen after the paid
                # response exists but before usage is parseable. Retain the
                # conservative reservation rather than undercounting spend.
                input_tokens=reservation.input_tokens if reservation else 0,
                output_tokens=reservation.output_tokens if reservation else 0,
                estimated_cost_cny=(
                    reservation.estimated_cost_cny if reservation else 0
                ),
            )
            if reservation is None:
                self.journal.append(failed)
            else:
                self.journal.finalize(failed)
            raise
        cost = (
            response.input_tokens * self.input_rate
            + response.output_tokens * self.output_rate
        ) / 1_000_000
        complete = DecisionJournalEntry(
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
        if reservation is None:
            self.journal.append(complete)
        else:
            try:
                self.journal.finalize(complete)
            except ValueError as error:
                raise JournalSafetyStop(str(error)) from None
        return response


class JournalSafetyStop(BaseException):
    """Fail closed across agent retry handlers after a journal safety event."""
