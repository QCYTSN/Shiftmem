"""Deterministic memory baselines with a common retrieval interface."""

from collections import Counter
from math import sqrt
import re
from typing import Any, Mapping, Protocol

from .schemas import ExperienceRecord, MemoryRecord


class MemoryStore(Protocol):
    def add(self, record: MemoryRecord) -> None: ...

    def retrieve(self, query: str, step: int, top_k: int) -> list[MemoryRecord]: ...


class ExperienceStore:
    """Replay-safe in-memory storage with defensive reads."""

    def __init__(self) -> None:
        self._records: dict[str, ExperienceRecord] = {}

    def add(self, record: ExperienceRecord) -> None:
        stored = self._records.get(record.memory_id)
        if stored is not None:
            if stored != record:
                raise ValueError(f"duplicate memory_id: {record.memory_id}")
            return
        self._records[record.memory_id] = record.model_copy(deep=True)

    def get(self, memory_id: str) -> ExperienceRecord:
        try:
            return self._records[memory_id].model_copy(deep=True)
        except KeyError as error:
            raise KeyError(f"unknown memory_id: {memory_id}") from error

    def replace(self, record: ExperienceRecord) -> None:
        if record.memory_id not in self._records:
            raise KeyError(f"unknown memory_id: {record.memory_id}")
        self._records[record.memory_id] = record.model_copy(deep=True)

    def all(self) -> list[ExperienceRecord]:
        return [record.model_copy(deep=True) for record in self._records.values()]


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


def lexical_cosine(left: str, right: str) -> float:
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
            key=lambda record: (
                lexical_cosine(query, record.text),
                record.step,
                record.memory_id,
            ),
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
                lexical_cosine(query, record.text)
                * 0.5 ** (max(0, step - record.step) / self.half_life),
                record.step,
                record.memory_id,
            ),
            reverse=True,
        )
        return ranked[:top_k]


def make_memory(
    name: str,
    config: Mapping[str, Any] | None = None,
) -> MemoryStore:
    profile = dict(config or {})
    if name == "shiftmem":
        from .retriever import RetrievalWeights
        from .shiftmem import ShiftMemory, ShiftMemoryConfig

        unknown = set(profile) - {"memory", "retrieval"}
        if unknown:
            raise ValueError(f"unknown ShiftMem profile fields: {sorted(unknown)}")
        return ShiftMemory(
            ShiftMemoryConfig(**dict(profile.get("memory", {}))),
            retrieval_weights=RetrievalWeights(**dict(profile.get("retrieval", {}))),
        )
    if profile:
        raise ValueError(f"memory profile is only supported for shiftmem, got: {name}")
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
