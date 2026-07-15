"""Run the bounded pre-experiment inventory model qualification suite."""

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

import yaml

from shiftmem.agents.base import AgentDecision, StrategyProposal
from shiftmem.evaluation.model_qualification import (
    QualificationCase,
    QualificationResult,
    build_qualification_cases,
    summarize_qualification,
)
from shiftmem.evaluation.strategy_qualification import (
    QualificationAttempt,
    StrategyQualificationCase,
    StrategyQualificationResult,
    build_strategy_qualification_cases,
    summarize_strategy_qualification,
)
from shiftmem.evaluation.qualification_run import (
    build_run_metadata,
    ensure_output_paths_available,
)
from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig
from shiftmem.providers.inventory_prompt import (
    STRATEGY_REVIEW_SYSTEM_PROMPT,
    build_strategy_review_user_message,
)


def run_strategy_case(
    provider: Any, case: StrategyQualificationCase, repetition: int
) -> StrategyQualificationResult:
    """Run one strategy-schema qualification case with one correction retry."""

    supplied_ids = {
        str(item["memory_id"]) for item in case.request.memory if "memory_id" in item
    }
    request = case.request
    total_input = 0
    total_output = 0
    total_latency = 0.0
    error_text: str | None = None
    attempts: list[QualificationAttempt] = []
    for attempt_number in range(1, 3):
        correction = request.correction
        raw_output = ""
        attempt_input = 0
        attempt_output = 0
        attempt_latency = 0.0
        try:
            response = provider.generate(request)
            raw_output = response.text
            attempt_input = response.input_tokens
            attempt_output = response.output_tokens
            attempt_latency = response.latency_ms
            total_input += response.input_tokens
            total_output += response.output_tokens
            total_latency += response.latency_ms
            proposal = StrategyProposal.model_validate_json(response.text)
            unknown = set(proposal.used_memory_ids) - supplied_ids
            if unknown:
                raise ValueError(f"unsupplied memory IDs: {sorted(unknown)}")
            attempts.append(
                QualificationAttempt(
                    attempt=attempt_number,
                    correction=correction,
                    raw_output=raw_output,
                    input_tokens=attempt_input,
                    output_tokens=attempt_output,
                    latency_ms=attempt_latency,
                )
            )
            return StrategyQualificationResult(
                case_id=case.case_id,
                repetition=repetition,
                proposal=proposal,
                supplied_memory_ids=supplied_ids,
                inapplicable_memory_ids=case.inapplicable_memory_ids,
                input_tokens=total_input,
                output_tokens=total_output,
                latency_ms=total_latency,
                attempts=attempts,
            )
        except Exception as error:
            error_text = f"{type(error).__name__}: {error}"
            attempts.append(
                QualificationAttempt(
                    attempt=attempt_number,
                    correction=correction,
                    raw_output=raw_output,
                    input_tokens=attempt_input,
                    output_tokens=attempt_output,
                    latency_ms=attempt_latency,
                    error=error_text,
                )
            )
            request = request.model_copy(
                update={
                    "correction": (
                        "Return a valid StrategyProposal JSON object with only "
                        "forecast_window, safety_stock_multiplier, lead_time_buffer, "
                        "used_memory_ids, confidence, and reason. Never return order_quantity."
                    )
                }
            )
    return StrategyQualificationResult(
        case_id=case.case_id,
        repetition=repetition,
        fallback_used=True,
        supplied_memory_ids=supplied_ids,
        inapplicable_memory_ids=case.inapplicable_memory_ids,
        input_tokens=total_input,
        output_tokens=total_output,
        latency_ms=total_latency,
        error=error_text,
        attempts=attempts,
    )


ProviderFactory = Callable[[str, str], Any]


def _default_provider_factory(profile: str, model_id: str):
    return CompatibleAPIProvider(
        ProviderConfig.from_env(profile, model_override=model_id)
    )


def _default_strategy_provider_factory(profile: str, model_id: str):
    return CompatibleAPIProvider(
        ProviderConfig.from_env(profile, model_override=model_id),
        system_prompt=STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_user_message=build_strategy_review_user_message,
    )


def _run_case(provider: Any, case: QualificationCase, repetition: int) -> QualificationResult:
    supplied_ids = {
        str(item["memory_id"])
        for item in case.request.memory
        if "memory_id" in item
    }
    request = case.request
    total_input = 0
    total_output = 0
    total_latency = 0.0
    error_text: str | None = None
    for _ in range(2):
        try:
            response = provider.generate(request)
            total_input += response.input_tokens
            total_output += response.output_tokens
            total_latency += response.latency_ms
            decision = AgentDecision.model_validate_json(response.text)
            unknown = set(decision.used_memory_ids) - supplied_ids
            if unknown:
                raise ValueError(f"unsupplied memory IDs: {sorted(unknown)}")
            return QualificationResult(
                case_id=case.case_id,
                repetition=repetition,
                decision=decision,
                supplied_memory_ids=supplied_ids,
                inapplicable_memory_ids=case.inapplicable_memory_ids,
                input_tokens=total_input,
                output_tokens=total_output,
                latency_ms=total_latency,
            )
        except Exception as error:
            error_text = f"{type(error).__name__}: {error}"
            request = request.model_copy(
                update={
                    "correction": (
                        "Return a valid inventory AgentDecision JSON object using only "
                        "supplied memory IDs. Preserve the same public-state objective."
                    )
                }
            )
    return QualificationResult(
        case_id=case.case_id,
        repetition=repetition,
        fallback_used=True,
        supplied_memory_ids=supplied_ids,
        inapplicable_memory_ids=case.inapplicable_memory_ids,
        input_tokens=total_input,
        output_tokens=total_output,
        latency_ms=total_latency,
        error=error_text,
    )


def execute_qualification(
    config: dict[str, Any],
    raw_output: Path,
    summary_output: Path,
    provider_factory: ProviderFactory = _default_provider_factory,
    merge_existing: bool = False,
) -> list[dict[str, Any]]:
    repetitions = int(config.get("repetitions", 2))
    if repetitions != 2:
        raise ValueError("qualification requires exactly two repetitions")
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    raw_lines: list[str] = []
    for candidate in config["models"]:
        profile = str(candidate["profile"])
        model_id = str(candidate["model_id"])
        provider = provider_factory(profile, model_id)
        results = [
            _run_case(provider, case, repetition)
            for repetition in range(repetitions)
            for case in build_qualification_cases()
        ]
        for result in results:
            raw_lines.append(
                json.dumps(
                    {
                        "label": candidate["label"],
                        "profile": profile,
                        "model_id": model_id,
                        "role": candidate["role"],
                        **result.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        summary = summarize_qualification(model_id, results).model_dump(mode="json")
        summaries.append(
            {
                "label": candidate["label"],
                "profile": profile,
                "model_id": model_id,
                "role": candidate["role"],
                **summary,
            }
        )
    raw_output.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    merged = summaries
    if merge_existing and summary_output.exists():
        previous = json.loads(summary_output.read_text(encoding="utf-8"))
        replacement_labels = {row["label"] for row in summaries}
        merged = [
            row for row in previous.get("models", [])
            if row.get("label") not in replacement_labels
        ] + summaries
    summary_output.write_text(
        json.dumps(
            {"qualification_date": date.today().isoformat(), "models": merged},
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return summaries


def execute_strategy_qualification(
    config: dict[str, Any],
    raw_output: Path,
    summary_output: Path,
    provider_factory: ProviderFactory = _default_strategy_provider_factory,
    *,
    run_id: str | None = None,
    overwrite: bool = False,
) -> list[dict[str, Any]]:
    """Run the v2 strategy-schema qualification suite (two repetitions)."""

    ensure_output_paths_available(
        (raw_output, summary_output), overwrite=overwrite
    )
    repetitions = int(config.get("repetitions", 2))
    if repetitions != 2:
        raise ValueError("strategy qualification requires exactly two repetitions")
    canonical_config = json.dumps(
        config, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    metadata = build_run_metadata(
        run_id=run_id or f"strategy-{date.today().isoformat()}-{uuid4().hex[:8]}",
        schema="strategy",
        config_bytes=canonical_config,
        system_prompt=STRATEGY_REVIEW_SYSTEM_PROMPT,
        builder_name=build_strategy_review_user_message.__name__,
    )
    raw_output.parent.mkdir(parents=True, exist_ok=True)
    summary_output.parent.mkdir(parents=True, exist_ok=True)
    summaries: list[dict[str, Any]] = []
    raw_lines: list[str] = []
    for candidate in config["models"]:
        profile = str(candidate["profile"])
        model_id = str(candidate["model_id"])
        provider = provider_factory(profile, model_id)
        results = [
            run_strategy_case(provider, case, repetition)
            for repetition in range(repetitions)
            for case in build_strategy_qualification_cases()
        ]
        for result in results:
            raw_lines.append(
                json.dumps(
                    {
                        "label": candidate["label"],
                        "profile": profile,
                        "model_id": model_id,
                        "schema": "strategy",
                        "run_id": metadata.run_id,
                        **result.model_dump(mode="json"),
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
        summary = summarize_strategy_qualification(model_id, results).model_dump(mode="json")
        summaries.append(
            {"label": candidate["label"], "profile": profile, "model_id": model_id, **summary}
        )
    raw_output.write_text("\n".join(raw_lines) + "\n", encoding="utf-8")
    summary_output.write_text(
        json.dumps(
            {
                "qualification_date": date.today().isoformat(),
                "schema": "strategy",
                "run_metadata": metadata.model_dump(mode="json"),
                "models": summaries,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return summaries


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--label", action="append")
    parser.add_argument("--merge-summary", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="allow replacing existing output files (never use for formal evidence)",
    )
    parser.add_argument(
        "--schema",
        choices=("order", "strategy"),
        default="order",
        help="order = v1 direct-order gates (archived); strategy = v2 strategy-review gates",
    )
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if args.label:
        selected = set(args.label)
        config["models"] = [row for row in config["models"] if row["label"] in selected]
        missing = selected - {row["label"] for row in config["models"]}
        if missing:
            raise ValueError(f"unknown qualification labels: {sorted(missing)}")
    if args.schema == "strategy":
        summaries = execute_strategy_qualification(
            config,
            args.raw_output,
            args.summary_output,
            run_id=args.run_id,
            overwrite=args.overwrite,
        )
    else:
        summaries = execute_qualification(
            config, args.raw_output, args.summary_output, merge_existing=args.merge_summary
        )
    print(json.dumps(summaries, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
