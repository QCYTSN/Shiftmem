# Inventory Model Qualification Report

Date: 2026-07-13

## Purpose

This bounded pre-experiment check evaluates whether candidate models can follow ShiftMem's public inventory objective and memory-use rules. It is an interface and task-suitability gate, not evidence that any memory method improves inventory performance.

Each model received the same eight synthetic cases twice at temperature 0 in non-thinking JSON mode. The hard gates require 16 parseable decisions, no fallback, no invalid or explicitly inapplicable memory citation, and all six paired demand, pipeline, and stockout-cost monotonicity checks.

## Corrected qualification result

| Model | Intended role | Parse / fallback | Monotonicity | Inapplicable citations | Result |
| --- | --- | ---: | ---: | ---: | --- |
| `qwen3.5-flash-2026-02-23` | Development control | 0 / 0 | 6 / 6 | 2 | Fail |
| `Qwen/Qwen3.5-35B-A3B` | Formal open-weight candidate | 0 / 0 | 6 / 6 | 2 | Fail |
| `deepseek-ai/DeepSeek-V3.2` | Formal open-weight candidate | 0 / 0 | 6 / 6 | 0 | Pass |
| `Pro/zai-org/GLM-5.1` | Supplementary candidate | 0 / 0 | 6 / 6 | 0 | Pass |

Both Qwen models cited `mem-dormant` in both repetitions even though its metadata marked it dormant and its text explicitly said the rule belonged to a mismatched old regime and was not applicable. This violates the predeclared hard gate. DeepSeek and GLM did not cite it.

## Controlled prompt correction

The initial run used the same 512-token cap but allowed an unbounded `reason`. Both Qwen models sometimes generated long reasoning strings that were truncated inside the JSON object. This was a measurement defect rather than sufficient evidence of poor inventory reasoning.

One provider-independent correction was therefore applied equally to all candidates: `reason` became one short sentence of at most 200 characters, enforced in the prompt and `AgentDecision` schema. The entire four-model matrix was rerun. The corrected run had zero parse failures and zero fallbacks for every model; only the predeclared memory-applicability gate separated the results.

## Decision

- Use DeepSeek-V3.2 as the current core experiment candidate.
- Keep GLM-5.1 as a supplementary confirmatory model, as fixed before qualification.
- Keep Qwen Flash for low-cost development smoke tests only.
- Do not use Qwen3.5-35B-A3B for formal ShiftMem conclusions under the current prompt and gate.
- Do not freeze the planned two-core-model design yet. A second eligible core model must pass the same fixed suite; replacing Qwen or changing the applicability protocol requires a documented design decision and a fresh equal-condition qualification.

## Reproduction

```powershell
.venv\Scripts\python.exe scripts/qualify_models.py --config configs/experiments/model_qualification.yaml --raw-output artifacts/raw_runs/model_qualification.jsonl --summary-output artifacts/aggregated/model_qualification_summary.json
```

Raw per-request records remain ignored. The committed aggregate is `artifacts/aggregated/model_qualification_summary.json`; it records model IDs, date, gates, token counts, and measured latency without credentials.
