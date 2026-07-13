import json

from shiftmem.agents.classical import FixedOrderPolicy
from shiftmem.agents.llm_agent import StructuredAgent
from shiftmem.memory.schemas import MemoryRecord
from shiftmem.memory.store import FullHistoryMemory, NoMemory
from shiftmem.providers.local import ScriptedProvider


OBSERVATION = {
    "day": 2,
    "inventory": 10,
    "pipeline_inventory": 5,
    "last_demand": 12,
    "last_sales": 10,
}


def raw_decision(quantity: int, memory_ids: list[str] | None = None) -> str:
    return json.dumps(
        {
            "order_quantity": quantity,
            "supplier_id": "standard",
            "used_memory_ids": memory_ids or [],
            "confidence": 0.8,
            "reason": "structured test decision",
        }
    )


def test_valid_provider_output_is_returned_and_logged() -> None:
    agent = StructuredAgent(
        ScriptedProvider([raw_decision(9)]), NoMemory(), FixedOrderPolicy(3)
    )
    decision = agent.act(OBSERVATION)
    assert decision.order_quantity == 9
    assert agent.logs[-1].attempt_count == 1
    assert agent.logs[-1].fallback_used is False


def test_invalid_json_retries_once_then_succeeds() -> None:
    agent = StructuredAgent(
        ScriptedProvider(["not-json", raw_decision(8)]),
        NoMemory(),
        FixedOrderPolicy(3),
    )
    assert agent.act(OBSERVATION).order_quantity == 8
    log = agent.logs[-1]
    assert log.attempt_count == 2
    assert log.parse_failure_count == 1
    assert log.fallback_used is False


def test_second_parse_failure_uses_safe_fallback() -> None:
    agent = StructuredAgent(
        ScriptedProvider(["bad", "still bad"]), NoMemory(), FixedOrderPolicy(7)
    )
    decision = agent.act(OBSERVATION)
    assert decision.order_quantity == 7
    assert decision.confidence == 0
    assert agent.logs[-1].attempt_count == 2
    assert agent.logs[-1].fallback_used is True


def test_unsupplied_memory_id_is_rejected() -> None:
    memory = FullHistoryMemory()
    memory.add(MemoryRecord(memory_id="real", step=1, text="demand high"))
    agent = StructuredAgent(
        ScriptedProvider([raw_decision(4, ["invented"]), raw_decision(5, ["real"])]),
        memory,
        FixedOrderPolicy(3),
    )
    assert agent.act(OBSERVATION).used_memory_ids == ["real"]
    assert agent.logs[-1].parse_failure_count == 1


def test_observe_adds_auditable_memory_record() -> None:
    memory = FullHistoryMemory()
    agent = StructuredAgent(
        ScriptedProvider([raw_decision(1)]), memory, FixedOrderPolicy(0)
    )
    agent.observe(
        {
            "day": 2,
            "demand": 12,
            "sales": 10,
            "lost_sales": 2,
            "ending_inventory": 0,
            "total_cost": 10.0,
        }
    )
    assert memory.records[0].memory_id == "observation-2"
    assert memory.records[0].payload["lost_sales"] == 2
