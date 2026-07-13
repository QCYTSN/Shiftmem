"""Run the bounded pre-experiment inventory model qualification suite."""

import argparse
from datetime import date
import json
from pathlib import Path
from typing import Any, Callable

import yaml

from shiftmem.agents.base import AgentDecision
from shiftmem.evaluation.model_qualification import (
    QualificationCase,
    QualificationResult,
    build_qualification_cases,
    summarize_qualification,
)
from shiftmem.providers.compatible_api import CompatibleAPIProvider, ProviderConfig


ProviderFactory = Callable[[str, str], Any]


def _default_provider_factory(profile: str, model_id: str):
    return CompatibleAPIProvider(
        ProviderConfig.from_env(profile, model_override=model_id)
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
    summary_output.write_text(
        json.dumps(
            {"qualification_date": date.today().isoformat(), "models": summaries},
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
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    summaries = execute_qualification(config, args.raw_output, args.summary_output)
    print(json.dumps(summaries, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
