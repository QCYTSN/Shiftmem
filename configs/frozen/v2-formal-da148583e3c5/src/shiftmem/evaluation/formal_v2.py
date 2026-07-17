"""Protocol-v2 offline formal execution and completeness checks."""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from pydantic import BaseModel, ConfigDict, Field

from shiftmem.agents.classical import OraclePolicy
from shiftmem.control.episode import V2EpisodeConfig, run_v2_episode
from shiftmem.envs.inventory_env import InventoryEnv
from shiftmem.envs.shifts import Scenario
from shiftmem.memory.store import make_memory
from shiftmem.providers.local import DeterministicStrategyProvider

from .metrics import (
    post_shift_cumulative_regret,
    recovery_time,
    summarize_episode,
    summarize_strategy_reviews,
)


class FormalV2CellResult(BaseModel):
    """One auditable, replayable formal cell result."""

    model_config = ConfigDict(extra="forbid")

    cell_id: str
    tier: str
    scenario_id: str
    seed: int
    model: str
    method: str
    complete: bool = True
    endpoint_applicable: bool
    shift_day: int | None
    post_shift_cumulative_regret_30: float | None
    recovery: dict[str, int | bool | None] | None
    inventory_metrics: dict[str, float | int]
    review_metrics: dict[str, float | int]
    reuse_metrics: dict[str, int]
    provider_attempts: int = Field(ge=0)
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    parse_failures: int = Field(ge=0)
    fallback_count: int = Field(ge=0)
    environment_records: list[dict[str, Any]]
    review_logs: list[dict[str, Any]]
    scheduler_log: list[dict[str, Any]]
    daily_decision_log: list[dict[str, Any]]
    memory_audit: dict[str, Any] | None = None
    run_identity: dict[str, str] | None = None
    test_outcomes_accessed: bool = False


def scenario_shift_day(scenario: Scenario) -> int | None:
    starts = [shift.start_day for shift in scenario.shifts if shift.type != "stable"]
    return min(starts) if starts else None


def run_oracle_episode(scenario: Scenario, seed: int) -> list[dict[str, Any]]:
    env = InventoryEnv(scenario)
    policy = OraclePolicy()
    observation, _ = env.reset(seed=seed)
    terminated = False
    while not terminated:
        action = policy.act(observation, env.oracle_context())
        observation, _, terminated, _, _ = env.step(action)
    return env.records


def execute_offline_cell(
    row: dict[str, Any],
    scenario: Scenario,
    config: dict[str, Any],
    oracle_records: list[dict[str, Any]],
) -> FormalV2CellResult:
    """Execute one network-free integration cell with the declared profile."""

    return execute_cell(
        row,
        scenario,
        config,
        oracle_records,
        provider=DeterministicStrategyProvider(),
    )


def execute_cell(
    row: dict[str, Any],
    scenario: Scenario,
    config: dict[str, Any],
    oracle_records: list[dict[str, Any]],
    *,
    provider: Any,
    run_identity: dict[str, str] | None = None,
) -> FormalV2CellResult:
    """Execute one formal cell with an injected offline or journaled provider."""

    method = str(row["method"])
    memory = make_memory(
        method, config["shiftmem_profile"] if method == "shiftmem" else None
    )
    episode = run_v2_episode(
        scenario,
        provider,
        memory,
        V2EpisodeConfig(
            seed=int(row["seed"]),
            max_days=scenario.episode_length,
            review_interval=int(config["review_interval"]),
            cooldown=int(config["cooldown"]),
            episode_id=str(row["cell_id"]),
            validation_service_window=int(
                config["shiftmem_profile"]["memory"]["validation_service_window"]
            ),
        ),
    )
    shift_day = scenario_shift_day(scenario)
    endpoint_applicable = shift_day is not None
    regret = None
    recovery = None
    if shift_day is not None:
        regret = post_shift_cumulative_regret(
            episode["environment_records"], oracle_records, shift_day, window=30
        )
        recovery = recovery_time(
            episode["environment_records"], oracle_records, shift_day
        )
    reviews = episode["review_logs"]
    reuse = episode["reuse_attribution"]
    return FormalV2CellResult(
        **row,
        endpoint_applicable=endpoint_applicable,
        shift_day=shift_day,
        post_shift_cumulative_regret_30=regret,
        recovery=recovery,
        inventory_metrics=summarize_episode(
            episode["environment_records"], shift_day
        ),
        review_metrics=summarize_strategy_reviews(
            episode["scheduler_log"], reviews
        ),
        reuse_metrics={
            key: sum(len(item[key]) for item in reuse)
            for key in ("reused", "retrieved_not_cited", "cited_but_rejected")
        },
        provider_attempts=sum(int(log["attempt_count"]) for log in reviews),
        input_tokens=sum(int(log["total_input_tokens"]) for log in reviews),
        output_tokens=sum(int(log["total_output_tokens"]) for log in reviews),
        parse_failures=sum(int(log["parse_failure_count"]) for log in reviews),
        fallback_count=int(episode["fallback_count"]),
        environment_records=episode["environment_records"],
        review_logs=reviews,
        scheduler_log=episode["scheduler_log"],
        daily_decision_log=episode["daily_decision_log"],
        memory_audit=episode.get("memory_audit"),
        run_identity=run_identity,
    )


def load_completed_cells(path: str | Path) -> dict[str, FormalV2CellResult]:
    completed: dict[str, FormalV2CellResult] = {}
    target = Path(path)
    if not target.exists():
        return completed
    for line_number, line in enumerate(target.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        result = FormalV2CellResult.model_validate_json(line)
        if result.cell_id in completed:
            raise ValueError(f"duplicate completed cell at line {line_number}: {result.cell_id}")
        completed[result.cell_id] = result
    return completed


def append_completed_cell(path: str | Path, result: FormalV2CellResult) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(result.model_dump_json() + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def validate_plan_completeness(
    plan: Iterable[dict[str, Any]], results: Iterable[FormalV2CellResult]
) -> None:
    expected = list(plan)
    actual = list(results)
    expected_ids = [str(row["cell_id"]) for row in expected]
    actual_ids = [row.cell_id for row in actual]
    duplicate_expected = [key for key, count in Counter(expected_ids).items() if count > 1]
    duplicate_actual = [key for key, count in Counter(actual_ids).items() if count > 1]
    if duplicate_expected or duplicate_actual:
        raise ValueError(
            f"duplicate cells: expected={duplicate_expected}, actual={duplicate_actual}"
        )
    missing = sorted(set(expected_ids) - set(actual_ids))
    unexpected = sorted(set(actual_ids) - set(expected_ids))
    incomplete = sorted(row.cell_id for row in actual if not row.complete)
    expected_by_id = {str(row["cell_id"]): row for row in expected}
    mismatched = []
    for result in actual:
        planned = expected_by_id.get(result.cell_id)
        if planned is None:
            continue
        identity = ("tier", "scenario_id", "seed", "model", "method")
        if any(getattr(result, key) != planned[key] for key in identity):
            mismatched.append(result.cell_id)
    if missing or unexpected or incomplete or mismatched:
        raise ValueError(
            "cell matrix incomplete: "
            f"missing={missing}, unexpected={unexpected}, incomplete={incomplete}, "
            f"mismatched={sorted(mismatched)}"
        )


def aggregate_results(
    plan: list[dict[str, Any]],
    results: list[FormalV2CellResult],
    *,
    journal_totals: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    validate_plan_completeness(plan, results)
    return {
        "complete": True,
        "test_outcomes_accessed": False,
        "cells": len(results),
        "tiers": dict(Counter(row.tier for row in results)),
        "methods": dict(Counter(row.method for row in results)),
        "models": dict(Counter(row.model for row in results)),
        "provider_calls": int((journal_totals or {}).get("calls", 0)),
        "offline_provider_attempts": sum(row.provider_attempts for row in results),
        "input_tokens": sum(row.input_tokens for row in results),
        "output_tokens": sum(row.output_tokens for row in results),
        "parse_failures": sum(row.parse_failures for row in results),
        "fallback_count": sum(row.fallback_count for row in results),
        "applicable_endpoint_cells": sum(row.endpoint_applicable for row in results),
        "journal_totals": journal_totals,
    }
