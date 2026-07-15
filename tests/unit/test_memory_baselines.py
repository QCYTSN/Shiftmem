from shiftmem.memory.schemas import MemoryRecord
from shiftmem.memory.store import (
    FullHistoryMemory,
    NoMemory,
    SummaryMemory,
    TimeDecayMemory,
    VectorMemory,
    make_memory,
)


def records() -> list[MemoryRecord]:
    return [
        MemoryRecord(memory_id="m1", step=1, text="demand increased sharply", variables=["demand"]),
        MemoryRecord(memory_id="m2", step=5, text="supplier lead time delayed", variables=["lead_time"]),
        MemoryRecord(memory_id="m3", step=9, text="demand returned to normal", variables=["demand"]),
    ]


def fill(store) -> None:
    for record in records():
        store.add(record)


def test_no_memory_never_returns_context() -> None:
    store = NoMemory()
    fill(store)
    assert store.retrieve("demand", step=10, top_k=2) == []


def test_full_history_returns_most_recent_with_budget() -> None:
    store = FullHistoryMemory()
    fill(store)
    assert [item.memory_id for item in store.retrieve("", 10, 2)] == ["m3", "m2"]


def test_summary_returns_one_deterministic_summary() -> None:
    store = SummaryMemory()
    fill(store)
    result = store.retrieve("", step=10, top_k=2)
    assert len(result) == 1
    assert result[0].memory_id == "summary-10"
    assert "3 observations" in result[0].text


def test_vector_memory_prefers_lexical_relevance() -> None:
    store = VectorMemory()
    fill(store)
    result = store.retrieve("supplier delay lead time", step=10, top_k=1)
    assert result[0].memory_id == "m2"


def test_time_decay_prefers_recent_equally_relevant_record() -> None:
    store = TimeDecayMemory(half_life=2)
    store.add(MemoryRecord(memory_id="old", step=1, text="demand high", variables=["demand"]))
    store.add(MemoryRecord(memory_id="new", step=9, text="demand high", variables=["demand"]))
    assert store.retrieve("demand high", step=10, top_k=1)[0].memory_id == "new"


def test_top_k_must_be_positive() -> None:
    store = VectorMemory()
    fill(store)
    try:
        store.retrieve("demand", step=10, top_k=0)
    except ValueError:
        pass
    else:
        raise AssertionError("top_k=0 must be rejected")


def test_make_memory_applies_explicit_shiftmem_profile() -> None:
    memory = make_memory(
        "shiftmem",
        {
            "memory": {
                "detector_min_samples": 10,
                "detector_delta": 0.1,
                "detector_threshold": 48.0,
                "validation_service_window": 3,
                "dormancy_patience": 3,
            },
            "retrieval": {"semantic": 0.75, "recency": 1.0},
        },
    )
    assert memory.config.detector_threshold == 48.0
    assert memory.config.dormancy_patience == 3
    assert memory.retriever.weights.semantic == 0.75
    assert memory.retriever.weights.recency == 1.0
