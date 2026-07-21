"""Tests for the v2 strategy-schema model qualification suite."""

from shiftmem.evaluation.strategy_qualification import (
    QualificationAttempt,
    StrategyQualificationResult,
    build_strategy_qualification_cases,
    summarize_strategy_qualification,
)
from shiftmem.agents.base import StrategyProposal
from shiftmem.providers.base import StrategyProviderRequest


def _proposal(multiplier=1.2, window=14, buffer=1, used=None):
    return StrategyProposal(
        forecast_window=window,
        safety_stock_multiplier=multiplier,
        lead_time_buffer=buffer,
        used_memory_ids=used or [],
        confidence=0.6,
        reason="test",
    )


def _results_from(mapping):
    """Build two identical repetitions of results from a case_id->proposal map."""
    results = []
    cases = build_strategy_qualification_cases()
    for repetition in range(2):
        for case in cases:
            proposal = mapping[case.case_id]
            supplied = {m["memory_id"] for m in case.request.memory}
            results.append(
                StrategyQualificationResult(
                    case_id=case.case_id,
                    repetition=repetition,
                    proposal=proposal,
                    supplied_memory_ids=supplied,
                    inapplicable_memory_ids=case.inapplicable_memory_ids,
                )
            )
    return results


def test_cases_cover_demand_and_applicability():
    cases = build_strategy_qualification_cases()
    ids = {case.case_id for case in cases}
    assert {"demand_low", "demand_high", "applicable_memory", "inapplicable_memory"}.issubset(ids)


def test_cases_use_complete_strategy_requests():
    for case in build_strategy_qualification_cases():
        assert isinstance(case.request, StrategyProviderRequest)
        assert case.request.current_strategy == {
            "forecast_window": 7,
            "safety_stock_multiplier": 1.5,
            "lead_time_buffer": 2,
        }
        assert case.request.trigger_reason in {"periodic", "event"}


def test_all_qualification_histories_are_public_and_consistent():
    allowed = {
        "day",
        "demand",
        "sales",
        "lost_sales",
        "ending_inventory",
        "order_quantity",
        "arrivals",
        "total_cost",
    }
    for case in build_strategy_qualification_cases():
        observation = case.request.observation
        history = observation["recent_history"]
        assert [row["day"] for row in history] == sorted(
            row["day"] for row in history
        )
        assert all(set(row) == allowed for row in history)
        assert all(
            row["sales"] + row["lost_sales"] == row["demand"]
            for row in history
        )
        assert all(row["ending_inventory"] >= 0 for row in history)
        assert all(
            row["lost_sales"] == 0 or row["ending_inventory"] == 0
            for row in history
        )
        final = history[-1]
        assert observation["last_demand"] == final["demand"]
        assert observation["last_sales"] == final["sales"]
        assert observation["inventory"] == final["ending_inventory"]


def test_lost_sales_pair_keeps_identical_realized_demand():
    cases = {case.case_id: case for case in build_strategy_qualification_cases()}
    calm = cases["lost_sales_none"].request.observation["recent_history"]
    pressured = cases["lost_sales_high"].request.observation["recent_history"]
    assert [row["demand"] for row in calm] == [
        row["demand"] for row in pressured
    ]


def test_qualifying_model_passes_all_gates():
    # Higher-protection proposal under high demand; cites only applicable memory.
    mapping = {
        "demand_low": _proposal(multiplier=1.0),
        "demand_high": _proposal(multiplier=2.0),
        "lost_sales_none": _proposal(buffer=0),
        "lost_sales_high": _proposal(buffer=3),
        "applicable_memory": _proposal(multiplier=2.0, used=["mem-active"]),
        "inapplicable_memory": _proposal(multiplier=2.0, used=[]),
    }
    summary = summarize_strategy_qualification("good-model", _results_from(mapping))
    assert summary.qualifies is True
    assert summary.monotonicity_passes == summary.monotonicity_checks


def test_model_citing_dormant_memory_fails_applicability_gate():
    mapping = {
        "demand_low": _proposal(multiplier=1.0),
        "demand_high": _proposal(multiplier=2.0),
        "lost_sales_none": _proposal(buffer=0),
        "lost_sales_high": _proposal(buffer=3),
        "applicable_memory": _proposal(multiplier=2.0, used=["mem-active"]),
        "inapplicable_memory": _proposal(multiplier=2.0, used=["mem-dormant"]),
    }
    summary = summarize_strategy_qualification("citing-model", _results_from(mapping))
    assert summary.inapplicable_memory_citation_count > 0
    assert summary.qualifies is False


def test_non_monotonic_model_fails():
    # A genuinely non-monotone model collapses protection so far at high demand
    # that even the larger high-demand sigma cannot compensate: induced safety
    # stock actually falls. A mere multiplier drop that still raises absolute
    # protection is NOT a failure under the induced-safety-stock gate.
    # The lost_sales pair holds demand fixed, so lowering protection there
    # genuinely lowers the induced target. A model that cuts protection under
    # higher lost-sales pressure fails.
    mapping = {
        "demand_low": _proposal(multiplier=1.0),
        "demand_high": _proposal(multiplier=1.5),
        "lost_sales_none": _proposal(multiplier=3.0, buffer=5),   # heavy when calm
        "lost_sales_high": _proposal(multiplier=0.0, buffer=0),   # nothing under pressure
        "applicable_memory": _proposal(multiplier=1.5, used=["mem-active"]),
        "inapplicable_memory": _proposal(multiplier=1.5, used=[]),
    }
    summary = summarize_strategy_qualification("bad-model", _results_from(mapping))
    assert summary.monotonicity_passes < summary.monotonicity_checks
    assert summary.qualifies is False


def test_lower_multiplier_at_higher_demand_can_still_pass():
    # Regression guard for the gate-design fix: DeepSeek-style behavior
    # (multiplier 1.5 at low demand, 1.0 at high) passes because the larger
    # high-demand sigma yields more absolute protection despite the lower coeff.
    mapping = {
        "demand_low": _proposal(multiplier=1.5),
        "demand_high": _proposal(multiplier=1.0),
        "lost_sales_none": _proposal(buffer=0),
        "lost_sales_high": _proposal(buffer=3),
        "applicable_memory": _proposal(multiplier=1.0, used=["mem-active"]),
        "inapplicable_memory": _proposal(multiplier=1.0, used=[]),
    }
    summary = summarize_strategy_qualification("reasonable-model", _results_from(mapping))
    assert summary.monotonicity_passes == summary.monotonicity_checks
    assert summary.qualifies is True


def test_summary_reports_corrected_attempt_without_unresolved_failure():
    mapping = {
        "demand_low": _proposal(multiplier=1.0),
        "demand_high": _proposal(multiplier=2.0),
        "lost_sales_none": _proposal(buffer=0),
        "lost_sales_high": _proposal(buffer=3),
        "applicable_memory": _proposal(multiplier=2.0, used=["mem-active"]),
        "inapplicable_memory": _proposal(multiplier=2.0, used=[]),
    }
    results = _results_from(mapping)
    results[0].attempts = [
        QualificationAttempt(
            attempt=1,
            raw_output="not-json",
            error="ValidationError: invalid JSON",
        ),
        QualificationAttempt(attempt=2, raw_output=mapping["demand_low"].model_dump_json()),
    ]

    summary = summarize_strategy_qualification("corrected-model", results)

    assert summary.attempt_count == 2
    assert summary.corrected_case_count == 1
    assert summary.attempt_parse_failure_count == 1
    assert summary.unresolved_parse_failure_count == 0
    assert summary.qualifies is True
