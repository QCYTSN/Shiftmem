"""Deterministic memory baselines with a common retrieval interface."""

from collections import Counter
from math import sqrt
import re
from typing import Protocol

from .schemas import MemoryRecord


class MemoryStore(Protocol):
    def add(self, record: MemoryRecord) -> None: ...

    def retrieve(self, query: str, step: int, top_k: int) -> list[MemoryRecord]: ...


def _validate_top_k(top_k: int) -> None:
    if top_k < 1:
        raise ValueError("top_k must be positive")


class NoMemory:
    def add(self, record: MemoryRecord) -> None:
        return None

    def retrieve(self, query: str, step: int, top_k: int) -> list[MemoryRecord]:
        _validate_top_k(top_k)
        return []


class FullHistoryMemory:
    def __init__(self) -> None:
        self.records: list[MemoryRecord] = []

    def add(self, record: MemoryRecord) -> None:
        self.records.append(record)

    def retrieve(self, query: str, step: int, top_k: int) -> list[MemoryRecord]:
        _validate_top_k(top_k)
        return list(reversed(self.records[-top_k:]))


class SummaryMemory(FullHistoryMemory):
    def retrieve(self, query: str, step: int, top_k: int) -> list[MemoryRecord]:
        _validate_top_k(top_k)
        if not self.records:
            return []
        recent = self.records[-top_k:]
        text = (
            f"Summary of {len(self.records)} observations. Recent evidence: "
            + " | ".join(record.text for record in recent)
        )
        return [
            MemoryRecord(
                memory_id=f"summary-{step}",
                step=step,
                text=text,
                variables=sorted({v for record in recent for v in record.variables}),
            )
        ]


def _tokens(text: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9_]+", text.lower()))


def _cosine(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    numerator = sum(value * right_tokens[token] for token, value in left_tokens.items())
    left_norm = sqrt(sum(value * value for value in left_tokens.values()))
    right_norm = sqrt(sum(value * value for value in right_tokens.values()))
    return numerator / (left_norm * right_norm) if left_norm and right_norm else 0.0


class VectorMemory(FullHistoryMemory):
    def retrieve(self, query: str, step: int, top_k: int) -> list[MemoryRecord]:
        _validate_top_k(top_k)
        ranked = sorted(
            self.records,
            key=lambda record: (_cosine(query, record.text), record.step, record.memory_id),
            reverse=True,
        )
        return ranked[:top_k]


class TimeDecayMemory(VectorMemory):
    def __init__(self, half_life: float = 30) -> None:
        super().__init__()
        if half_life <= 0:
            raise ValueError("half_life must be positive")
        self.half_life = half_life

    def retrieve(self, query: str, step: int, top_k: int) -> list[MemoryRecord]:
        _validate_top_k(top_k)
        ranked = sorted(
            self.records,
            key=lambda record: (
                _cosine(query, record.text)
                * 0.5 ** (max(0, step - record.step) / self.half_life),
                record.step,
                record.memory_id,
            ),
            reverse=True,
        )
        return ranked[:top_k]


def make_memory(name: str) -> MemoryStore:
    factories = {
        "none": NoMemory,
        "full_history": FullHistoryMemory,
        "summary": SummaryMemory,
        "vector": VectorMemory,
        "time_decay": TimeDecayMemory,
    }
    try:
        return factories[name]()
    except KeyError as error:
        raise ValueError(f"unknown memory baseline: {name}") from error
