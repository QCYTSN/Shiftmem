from shiftmem.agents.base import AgentDecision
from shiftmem.evaluation.model_qualification import (
    QualificationResult,
    build_qualification_cases,
    summarize_qualification,
)


def decision(quantity: int, memory_ids=None) -> AgentDecision:
    return AgentDecision(
        order_quantity=quantity,
        supplier_id="standard",
        used_memory_ids=memory_ids or [],
        confidence=0.8,
        reason="qualification decision",
    )


def test_cases_are_deterministic_paired_and_hide_oracle_state() -> None:
    cases = build_qualification_cases()
    assert [case.case_id for case in cases] == [
        "demand_low",
        "demand_high",
        "pipeline_empty",
        "pipeline_full",
        "stockout_cost_low",
        "stockout_cost_high",
        "applicable_memory",
        "inapplicable_memory",
    ]
    forbidden = {"demand_mean", "dispersion", "fill_rate", "regime_id", "shift_day"}
    assert all(forbidden.isdisjoint(case.request.observation) for case in cases)
    dormant = cases[-1]
    assert dormant.inapplicable_memory_ids == {"mem-dormant"}
    assert dormant.request.memory[0]["status"] == "dormant"


def test_summary_qualifies_model_that_passes_every_hard_gate() -> None:
    quantities = {
        "demand_low": 10,
        "demand_high": 30,
        "pipeline_empty": 25,
        "pipeline_full": 0,
        "stockout_cost_low": 10,
        "stockout_cost_high": 25,
        "applicable_memory": 30,
        "inapplicable_memory": 15,
    }
    results = []
    for repetition in range(2):
        for case in build_qualification_cases():
            memory_ids = ["mem-active"] if case.case_id == "applicable_memory" else []
            results.append(
                QualificationResult(
                    case_id=case.case_id,
                    repetition=repetition,
                    decision=decision(quantities[case.case_id], memory_ids),
                    supplied_memory_ids=set(memory_ids) | case.inapplicable_memory_ids,
                    inapplicable_memory_ids=case.inapplicable_memory_ids,
                    input_tokens=100,
                    output_tokens=20,
                    latency_ms=5,
                )
            )

    summary = summarize_qualification("model-a", results)

    assert summary.qualifies is True
    assert summary.monotonicity_passes == 6
    assert summary.monotonicity_checks == 6
    assert summary.fallback_count == 0
    assert summary.invalid_memory_citation_count == 0


def test_summary_rejects_fallback_monotonicity_and_dormant_memory_failures() -> None:
    results = []
    for repetition in range(2):
        for case in build_qualification_cases():
            quantity = 10
            cited = ["mem-dormant"] if case.case_id == "inapplicable_memory" else []
            results.append(
                QualificationResult(
                    case_id=case.case_id,
                    repetition=repetition,
                    decision=None if case.case_id == "demand_high" else decision(quantity, cited),
                    fallback_used=case.case_id == "demand_high",
                    supplied_memory_ids=case.inapplicable_memory_ids,
                    inapplicable_memory_ids=case.inapplicable_memory_ids,
                    error="failed" if case.case_id == "demand_high" else None,
                )
            )

    summary = summarize_qualification("model-b", results)

    assert summary.qualifies is False
    assert summary.fallback_count == 2
    assert summary.inapplicable_memory_citation_count == 2
