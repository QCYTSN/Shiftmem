"""Deterministic behavioral gates for v2 strategy-schema qualification.

Unlike the v1 direct-order qualification, monotonicity here is expressed over
the bounded strategy vector: under higher demand or higher lost-sales pressure
a qualifying reviewer must not lower protection (it should raise the
safety-stock multiplier or the lead-time buffer). Applicability gates are
unchanged: a model must not cite an explicitly dormant, mismatched memory.

The cases run offline against any provider. Live execution against a real model
is gated behind explicit API-budget approval elsewhere.
"""

from pydantic import BaseModel, ConfigDict, Field

from shiftmem.agents.base import StrategyProposal
from shiftmem.control.controller import DeterministicController, StrategyParameters
from shiftmem.providers.base import StrategyProviderRequest


class StrategyQualificationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    case_id: str
    request: StrategyProviderRequest
    inapplicable_memory_ids: set[str] = Field(default_factory=set)


class StrategyQualificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    repetition: int = Field(ge=0)
    proposal: StrategyProposal | None = None
    fallback_used: bool = False
    supplied_memory_ids: set[str] = Field(default_factory=set)
    inapplicable_memory_ids: set[str] = Field(default_factory=set)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0, ge=0)
    error: str | None = None
    attempts: list["QualificationAttempt"] = Field(default_factory=list)


class QualificationAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt: int = Field(ge=1, le=2)
    correction: str | None = None
    raw_output: str = ""
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0, ge=0)
    error: str | None = None


class StrategyQualificationSummary(BaseModel):
    model_id: str
    qualifies: bool
    result_count: int
    fallback_count: int
    parse_failure_count: int
    attempt_count: int
    corrected_case_count: int
    attempt_parse_failure_count: int
    unresolved_parse_failure_count: int
    invalid_memory_citation_count: int
    inapplicable_memory_citation_count: int
    monotonicity_passes: int
    monotonicity_checks: int
    applicable_memory_citation_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_latency_ms: float


# Deterministic *proportional* variability so demand variance scales with the
# demand level, as real (e.g. negative-binomial) demand does. This is what makes
# the induced-safety-stock gate meaningful: at a higher level sigma is larger,
# so a model may lower the multiplier and still raise absolute protection.
_VARIATION_FRAC = (-0.20, 0.15, -0.10, 0.25, -0.15, 0.10, -0.05)
_PUBLIC_HISTORY_FIELDS = {
    "day",
    "demand",
    "sales",
    "lost_sales",
    "ending_inventory",
    "order_quantity",
    "arrivals",
    "total_cost",
}
_CURRENT_STRATEGY = {
    "forecast_window": 7,
    "safety_stock_multiplier": 1.5,
    "lead_time_buffer": 2,
}


def _validate_public_history_row(row: dict) -> None:
    if set(row) != _PUBLIC_HISTORY_FIELDS:
        raise ValueError("qualification history contains non-public fields")
    if row["sales"] + row["lost_sales"] != row["demand"]:
        raise ValueError("qualification history violates demand conservation")
    if row["ending_inventory"] < 0:
        raise ValueError("qualification history has negative inventory")
    if row["lost_sales"] > 0 and row["ending_inventory"] != 0:
        raise ValueError("lost sales require zero ending inventory")


def _history(demand: int, lost_sales: int = 0) -> list[dict]:
    rows = []
    for frac, day in zip(_VARIATION_FRAC, range(1, 8), strict=True):
        realized = max(0, round(demand * (1 + frac)))
        lost = min(lost_sales, realized)
        sales = realized - lost
        ending_inventory = 0 if lost else demand
        order_quantity = realized
        row = {
            "day": day,
            "demand": realized,
            "sales": sales,
            "lost_sales": lost,
            "ending_inventory": ending_inventory,
            "order_quantity": order_quantity,
            "arrivals": sales,
            "total_cost": float(
                order_quantity + 0.2 * ending_inventory + 5.0 * lost
            ),
        }
        _validate_public_history_row(row)
        rows.append(row)
    return rows


def _observation(demand: int = 20, lost_sales: int = 0) -> dict:
    history = _history(demand, lost_sales=lost_sales)
    final = history[-1]
    return {
        "day": 8,
        "inventory": final["ending_inventory"],
        "pipeline_inventory": 0,
        "pipeline_orders": [],
        "quoted_lead_time": 2,
        "last_demand": final["demand"],
        "last_sales": final["sales"],
        "costs": {"purchase": 1.0, "holding": 0.2, "stockout": 5.0, "fixed_order": 0.0},
        "recent_history": history,
    }


def _request(
    observation: dict,
    *,
    memory: list[dict] | None = None,
    trigger_reason: str = "periodic",
    trigger_evidence: dict | None = None,
) -> StrategyProviderRequest:
    return StrategyProviderRequest(
        observation=observation,
        memory=memory or [],
        current_strategy=dict(_CURRENT_STRATEGY),
        trigger_reason=trigger_reason,
        trigger_evidence=trigger_evidence or {},
    )


def build_strategy_qualification_cases() -> list[StrategyQualificationCase]:
    cases: list[StrategyQualificationCase] = []

    low = _observation(10)
    high = _observation(35)
    cases.extend(
        [
            StrategyQualificationCase(
                case_id="demand_low",
                request=_request(low),
            ),
            StrategyQualificationCase(
                case_id="demand_high",
                request=_request(
                    high,
                    trigger_reason="event",
                    trigger_evidence={"variable": "demand", "direction": "increase"},
                ),
            ),
        ]
    )

    calm = _observation(20, lost_sales=0)
    pressured = _observation(20, lost_sales=8)
    cases.extend(
        [
            StrategyQualificationCase(
                case_id="lost_sales_none",
                request=_request(calm),
            ),
            StrategyQualificationCase(
                case_id="lost_sales_high",
                request=_request(
                    pressured,
                    trigger_reason="event",
                    trigger_evidence={
                        "variable": "lost_sales",
                        "direction": "increase",
                    },
                ),
            ),
        ]
    )

    active_memory = {
        "memory_id": "mem-active",
        "status": "active",
        "text": "Demand has persistently increased in conditions matching the current state.",
    }
    dormant_memory = {
        "memory_id": "mem-dormant",
        "status": "dormant",
        "text": "This low-demand rule belongs to a mismatched old regime and is not applicable.",
    }
    cases.extend(
        [
            StrategyQualificationCase(
                case_id="applicable_memory",
                request=_request(high, memory=[active_memory]),
            ),
            StrategyQualificationCase(
                case_id="inapplicable_memory",
                request=_request(high, memory=[dormant_memory]),
                inapplicable_memory_ids={"mem-dormant"},
            ),
        ]
    )
    return cases


def _induced_target(observation: dict, proposal: StrategyProposal) -> float:
    """Order-up-to target the proposal induces under the controller.

    This is the actual decision quantity the strategy controls. Judging
    monotonicity on it (rather than on any single parameter) is the fix for the
    first live gate: forecast_window, safety_stock_multiplier, and
    lead_time_buffer feed the target jointly, so only their combined effect is
    behaviorally meaningful. A lower multiplier or buffer can still raise the
    target when observed demand or its variability rose.
    """

    strategy = StrategyParameters(
        forecast_window=proposal.forecast_window,
        safety_stock_multiplier=proposal.safety_stock_multiplier,
        lead_time_buffer=proposal.lead_time_buffer,
    )
    return DeterministicController().order_up_to_target(observation, strategy)


def summarize_strategy_qualification(
    model_id: str, results: list[StrategyQualificationResult]
) -> StrategyQualificationSummary:
    by_key = {(result.repetition, result.case_id): result for result in results}
    observations = {
        case.case_id: case.request.observation
        for case in build_strategy_qualification_cases()
    }

    # Higher demand or higher lost-sales pressure must not lower the induced
    # order-up-to target. The lost_sales pair holds demand fixed, so it purely
    # tests the model's protection response; the demand pair is a weaker sanity
    # check because base stock scales with demand regardless of strategy.
    def not_lower(
        left: StrategyQualificationResult, right: StrategyQualificationResult
    ) -> bool:
        left_target = _induced_target(observations[left.case_id], left.proposal)
        right_target = _induced_target(observations[right.case_id], right.proposal)
        return right_target >= left_target - 1e-9

    pairs = (
        ("demand_low", "demand_high", not_lower),
        ("lost_sales_none", "lost_sales_high", not_lower),
    )
    monotonicity_passes = 0
    monotonicity_checks = 0
    for repetition in range(2):
        for left_id, right_id, predicate in pairs:
            left = by_key.get((repetition, left_id))
            right = by_key.get((repetition, right_id))
            if left and right and left.proposal and right.proposal:
                monotonicity_checks += 1
                monotonicity_passes += int(predicate(left, right))

    invalid_citations = 0
    inapplicable_citations = 0
    applicable_citations = 0
    for result in results:
        cited = set(result.proposal.used_memory_ids) if result.proposal else set()
        invalid_citations += len(cited - result.supplied_memory_ids)
        inapplicable_citations += len(cited & result.inapplicable_memory_ids)
        if result.case_id == "applicable_memory":
            applicable_citations += int("mem-active" in cited)

    fallback_count = sum(result.fallback_used for result in results)
    unresolved_parse_failure_count = sum(
        result.proposal is None or result.error is not None for result in results
    )
    attempt_count = sum(len(result.attempts) for result in results)
    attempt_parse_failure_count = sum(
        attempt.error is not None
        for result in results
        for attempt in result.attempts
    )
    corrected_case_count = sum(
        result.proposal is not None
        and any(attempt.error is not None for attempt in result.attempts)
        for result in results
    )
    qualifies = (
        len(results) == 12
        and fallback_count == 0
        and unresolved_parse_failure_count == 0
        and invalid_citations == 0
        and inapplicable_citations == 0
        and monotonicity_checks == 4
        and monotonicity_passes == 4
    )
    return StrategyQualificationSummary(
        model_id=model_id,
        qualifies=qualifies,
        result_count=len(results),
        fallback_count=fallback_count,
        parse_failure_count=unresolved_parse_failure_count,
        attempt_count=attempt_count,
        corrected_case_count=corrected_case_count,
        attempt_parse_failure_count=attempt_parse_failure_count,
        unresolved_parse_failure_count=unresolved_parse_failure_count,
        invalid_memory_citation_count=invalid_citations,
        inapplicable_memory_citation_count=inapplicable_citations,
        monotonicity_passes=monotonicity_passes,
        monotonicity_checks=monotonicity_checks,
        applicable_memory_citation_count=applicable_citations,
        total_input_tokens=sum(result.input_tokens for result in results),
        total_output_tokens=sum(result.output_tokens for result in results),
        total_latency_ms=sum(result.latency_ms for result in results),
    )
