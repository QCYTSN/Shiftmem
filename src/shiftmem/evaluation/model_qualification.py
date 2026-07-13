"""Deterministic behavioral gates for inventory-model qualification."""

from copy import deepcopy

from pydantic import BaseModel, ConfigDict, Field

from shiftmem.agents.base import AgentDecision
from shiftmem.providers.base import ProviderRequest


class QualificationCase(BaseModel):
    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    case_id: str
    request: ProviderRequest
    inapplicable_memory_ids: set[str] = Field(default_factory=set)


class QualificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    repetition: int = Field(ge=0)
    decision: AgentDecision | None = None
    fallback_used: bool = False
    supplied_memory_ids: set[str] = Field(default_factory=set)
    inapplicable_memory_ids: set[str] = Field(default_factory=set)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0, ge=0)
    error: str | None = None


class QualificationSummary(BaseModel):
    model_id: str
    qualifies: bool
    result_count: int
    fallback_count: int
    parse_failure_count: int
    invalid_memory_citation_count: int
    inapplicable_memory_citation_count: int
    monotonicity_passes: int
    monotonicity_checks: int
    applicable_memory_citation_count: int
    exact_repeat_agreement_count: int
    total_input_tokens: int
    total_output_tokens: int
    total_latency_ms: float


def _history(demand: int, lost_sales: int = 0) -> list[dict]:
    return [
        {
            "day": day,
            "demand": demand,
            "sales": demand - lost_sales,
            "lost_sales": lost_sales,
            "ending_inventory": 20,
            "order_quantity": demand,
            "arrivals": demand,
            "total_cost": float(demand),
        }
        for day in range(1, 8)
    ]


def _observation() -> dict:
    return {
        "day": 8,
        "inventory": 20,
        "pipeline_inventory": 0,
        "pipeline_orders": [],
        "quoted_lead_time": 2,
        "last_demand": 20,
        "last_sales": 20,
        "costs": {
            "purchase": 1.0,
            "holding": 0.2,
            "stockout": 5.0,
            "fixed_order": 0.0,
        },
        "recent_history": _history(20),
    }


def build_qualification_cases() -> list[QualificationCase]:
    """Return the fixed pre-main-experiment behavioral case set."""

    cases: list[QualificationCase] = []

    low = _observation()
    low["last_demand"] = low["last_sales"] = 10
    low["recent_history"] = _history(10)
    high = deepcopy(low)
    high["last_demand"] = high["last_sales"] = 35
    high["recent_history"] = _history(35)
    cases.extend(
        [
            QualificationCase(case_id="demand_low", request=ProviderRequest(observation=low, memory=[])),
            QualificationCase(case_id="demand_high", request=ProviderRequest(observation=high, memory=[])),
        ]
    )

    empty = _observation()
    full = deepcopy(empty)
    full["pipeline_inventory"] = 100
    full["pipeline_orders"] = [{"due_day": 9, "quantity": 100}]
    cases.extend(
        [
            QualificationCase(case_id="pipeline_empty", request=ProviderRequest(observation=empty, memory=[])),
            QualificationCase(case_id="pipeline_full", request=ProviderRequest(observation=full, memory=[])),
        ]
    )

    cheap = _observation()
    cheap["costs"]["stockout"] = 1.0
    expensive = deepcopy(cheap)
    expensive["costs"]["stockout"] = 20.0
    cases.extend(
        [
            QualificationCase(case_id="stockout_cost_low", request=ProviderRequest(observation=cheap, memory=[])),
            QualificationCase(case_id="stockout_cost_high", request=ProviderRequest(observation=expensive, memory=[])),
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
            QualificationCase(
                case_id="applicable_memory",
                request=ProviderRequest(observation=high, memory=[active_memory]),
            ),
            QualificationCase(
                case_id="inapplicable_memory",
                request=ProviderRequest(observation=high, memory=[dormant_memory]),
                inapplicable_memory_ids={"mem-dormant"},
            ),
        ]
    )
    return cases


def summarize_qualification(
    model_id: str, results: list[QualificationResult]
) -> QualificationSummary:
    by_key = {(result.repetition, result.case_id): result for result in results}
    pairs = (
        ("demand_low", "demand_high", lambda low, high: high >= low),
        ("pipeline_empty", "pipeline_full", lambda empty, full: full <= empty),
        ("stockout_cost_low", "stockout_cost_high", lambda low, high: high >= low),
    )
    monotonicity_passes = 0
    monotonicity_checks = 0
    for repetition in range(2):
        for left_id, right_id, predicate in pairs:
            left = by_key.get((repetition, left_id))
            right = by_key.get((repetition, right_id))
            if left and right and left.decision and right.decision:
                monotonicity_checks += 1
                monotonicity_passes += int(
                    predicate(
                        left.decision.order_quantity,
                        right.decision.order_quantity,
                    )
                )

    invalid_citations = 0
    inapplicable_citations = 0
    applicable_citations = 0
    for result in results:
        cited = set(result.decision.used_memory_ids) if result.decision else set()
        invalid_citations += len(cited - result.supplied_memory_ids)
        inapplicable_citations += len(cited & result.inapplicable_memory_ids)
        if result.case_id == "applicable_memory":
            applicable_citations += int("mem-active" in cited)

    exact_agreement = 0
    for case in build_qualification_cases():
        first = by_key.get((0, case.case_id))
        second = by_key.get((1, case.case_id))
        if first and second and first.decision and second.decision:
            exact_agreement += int(
                first.decision.order_quantity == second.decision.order_quantity
            )

    fallback_count = sum(result.fallback_used for result in results)
    parse_failure_count = sum(
        result.decision is None or result.error is not None for result in results
    )
    qualifies = (
        len(results) == 16
        and fallback_count == 0
        and parse_failure_count == 0
        and invalid_citations == 0
        and inapplicable_citations == 0
        and monotonicity_checks == 6
        and monotonicity_passes == 6
    )
    return QualificationSummary(
        model_id=model_id,
        qualifies=qualifies,
        result_count=len(results),
        fallback_count=fallback_count,
        parse_failure_count=parse_failure_count,
        invalid_memory_citation_count=invalid_citations,
        inapplicable_memory_citation_count=inapplicable_citations,
        monotonicity_passes=monotonicity_passes,
        monotonicity_checks=monotonicity_checks,
        applicable_memory_citation_count=applicable_citations,
        exact_repeat_agreement_count=exact_agreement,
        total_input_tokens=sum(result.input_tokens for result in results),
        total_output_tokens=sum(result.output_tokens for result in results),
        total_latency_ms=sum(result.latency_ms for result in results),
    )
