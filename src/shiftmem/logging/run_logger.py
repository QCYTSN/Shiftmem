"""Append-only, per-decision journal with replay and fail-closed budgets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .schemas import BudgetLimits, DecisionJournalEntry, RunIdentity


_SECRET_FIELDS = {"api_key", "authorization", "password", "secret"}


def _secret_field(value: Any) -> str | None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in _SECRET_FIELDS:
                return str(key)
            found = _secret_field(nested)
            if found:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = _secret_field(nested)
            if found:
                return found
    return None


class JsonlRunJournal:
    """Durably store exactly one completed response per decision identity."""

    def __init__(
        self,
        path: str | Path,
        identity: RunIdentity,
        limits: BudgetLimits,
    ) -> None:
        self.path = Path(path)
        self.identity = identity
        self.limits = limits
        self._entries: dict[str, DecisionJournalEntry] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        lines = self.path.read_text(encoding="utf-8").splitlines()
        rewrite = False
        for index, line in enumerate(lines):
            if not line.strip():
                continue
            try:
                entry = DecisionJournalEntry.model_validate_json(line)
            except (ValidationError, ValueError):
                if index != len(lines) - 1:
                    raise ValueError("journal contains malformed non-final line")
                rewrite = True
                break
            self._accept_loaded(entry)
        self._check_budget(None)
        if rewrite:
            self.path.write_text(
                "".join(
                    entry.model_dump_json() + "\n"
                    for entry in self._entries.values()
                ),
                encoding="utf-8",
            )

    def _accept_loaded(self, entry: DecisionJournalEntry) -> None:
        if entry.identity != self.identity:
            raise ValueError("journal identity does not match requested run identity")
        if entry.decision_id in self._entries:
            raise ValueError(f"decision already journaled: {entry.decision_id}")
        self._entries[entry.decision_id] = entry

    def lookup(self, decision_id: str) -> DecisionJournalEntry | None:
        return self._entries.get(decision_id)

    def _totals(self) -> dict[str, float | int]:
        return {
            "calls": sum(entry.calls for entry in self._entries.values()),
            "input_tokens": sum(
                entry.input_tokens for entry in self._entries.values()
            ),
            "output_tokens": sum(
                entry.output_tokens for entry in self._entries.values()
            ),
            "cost_usd": sum(
                entry.estimated_cost_usd for entry in self._entries.values()
            ),
        }

    def _check_budget(self, prospective: DecisionJournalEntry | None) -> None:
        totals = self._totals()
        if prospective is not None:
            totals["calls"] += prospective.calls
            totals["input_tokens"] += prospective.input_tokens
            totals["output_tokens"] += prospective.output_tokens
            totals["cost_usd"] += prospective.estimated_cost_usd
        checks = {
            "max_calls": (totals["calls"], self.limits.max_calls),
            "max_input_tokens": (
                totals["input_tokens"],
                self.limits.max_input_tokens,
            ),
            "max_output_tokens": (
                totals["output_tokens"],
                self.limits.max_output_tokens,
            ),
            "max_cost_usd": (totals["cost_usd"], self.limits.max_cost_usd),
        }
        for field, (actual, limit) in checks.items():
            if actual > limit:
                raise ValueError(f"journal would exceed {field}: {actual} > {limit}")

    def append(self, entry: DecisionJournalEntry) -> None:
        if entry.identity != self.identity:
            raise ValueError("entry identity does not match journal identity")
        if entry.decision_id in self._entries:
            raise ValueError(f"decision already journaled: {entry.decision_id}")
        secret = _secret_field(entry.provider_response)
        if secret:
            raise ValueError(f"provider response contains secret field: {secret}")
        self._check_budget(entry)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(entry.model_dump_json() + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._entries[entry.decision_id] = entry

    def totals(self) -> dict[str, float | int]:
        return self._totals().copy()
