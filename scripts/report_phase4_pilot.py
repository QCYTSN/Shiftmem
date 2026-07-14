"""Render the Phase 4 Pilot readiness report from aggregate evidence."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def recommended_seed_count(sd: float, minimum_effect: float) -> int:
    if minimum_effect <= 0:
        raise ValueError("minimum_effect must be positive")
    estimate = math.ceil((1.96 + 0.84) ** 2 * (sd / minimum_effect) ** 2)
    return max(30, estimate)


def render_report(aggregate: dict[str, Any], minimum_effect: float) -> str:
    rows = []
    recommendations = []
    for model in aggregate["models"]:
        n = recommended_seed_count(float(model["regret_sd"]), minimum_effect)
        recommendations.append(n)
        rows.append(
            f"| {str(model['model']).replace('-', ' ').title()} | {model['paired_seeds']} | "
            f"{float(model['mean_regret']):.3f} | {float(model['regret_sd']):.3f} | {n} |"
        )
    recommended = max(recommendations, default=30)
    return f"""# Phase 4 Pilot Report

## Scope and gate

This bounded Pilot used Development/Validation configuration only. Test-ID and Test-OOD outcomes were not generated or read. Matrix completion: {aggregate['completed_runs']}/{aggregate['expected_runs']} runs; complete = `{str(aggregate['complete']).lower()}`.

## Variance and paired endpoint

Negative regret favors ShiftMem over its paired VectorMemory run.

| Core model | Paired seeds | Mean 30-day regret | Regret SD | Recommended seeds |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(rows)}

## Runtime and token usage

- Provider-reported latency: {float(aggregate['total_latency_ms']) / 1000:.1f} seconds.
- Completed-cell provider calls: {int(aggregate.get('total_calls', 0))}.
- Total tokens: {int(aggregate['total_tokens'])}.
- Fallback decisions: {int(aggregate['total_fallbacks'])}.

## Metric completeness

Required per-run metrics complete: `{str(aggregate['metric_completeness']).lower()}`.

## Operational caveats

{chr(10).join(f'- {note}' for note in aggregate.get('operational_notes', [])) or '- None recorded.'}

## Recommended formal seed count

Using a two-sided normal approximation with 5% alpha, 80% power, and minimum relevant paired effect {minimum_effect:.1f}, the conservative recommendation is **{recommended} seeds per formal cell**. With only two Pilot seeds this is a planning estimate, not a precise power analysis.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--minimum-effect", type=float, default=100.0)
    args = parser.parse_args()
    aggregate = json.loads(args.input.read_text(encoding="utf-8"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_report(aggregate, args.minimum_effect), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
