# Inventory Model Qualification Report

> **v2 note (2026-07-14):** The results below qualify models for the historical direct-order schema. DeepSeek-V3.2 and MiniMax-M2.5 remain candidates, but both must pass a new bounded qualification suite for strategy-parameter output before any v2 Pilot or freeze.

## Protocol-v2 strategy-schema result

The repaired and frozen v2 harness was executed once on 2026-07-15 under run ID
`v2-qual-live-20260715-739bc99`. DeepSeek-V3.2 and MiniMax-M2.5 each passed all
4/4 strict strategy-monotonicity checks. Across 24 result rows there were 24
provider attempts, zero retries, zero parse failures, zero fallbacks, and zero
invalid or explicitly inapplicable memory citations. Estimated spend was CNY
0.2146 under the approved CNY 0.50 / 48-call ceiling.

This qualifies both models for the bounded v2 strategy-review interface only;
it does not evaluate ShiftMem effectiveness and does not unlock held-out Test
execution by itself.

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

## Second-core amendment (predeclared 2026-07-13)

The live SiliconFlow `/models` endpoint was queried without logging credentials. It listed `MiniMaxAI/MiniMax-M2.5`, `Pro/moonshotai/Kimi-K2.6`, `zai-org/GLM-5.2`, and newer Qwen/DeepSeek variants among the available chat models. Exactly one new candidate is predeclared for the unchanged qualification gate: `MiniMaxAI/MiniMax-M2.5` as `second_core_candidate`.

This choice adds a model family independent of DeepSeek and the supplementary GLM model. MiniMax publishes the weights and inference instructions, while the weights are governed by the MiniMax Model License (described by the publisher as Modified MIT), not the repository's MIT code license. The fixed qualification temperature remains zero for equal-condition comparison even though the publisher recommends different general-purpose inference settings. No substitute will be tried if this candidate fails; a failure requires a new documented amendment.

The bounded run is 16 cases (eight cases twice), with at most 32 provider requests if every case needs its one permitted correction retry. Based on previous qualification token counts, expected usage is roughly 14,000 input and 1,200 output tokens.

### Second-core result

`MiniMaxAI/MiniMax-M2.5` passed the unchanged suite: 16/16 results were parseable, all 6/6 monotonicity checks passed, no fallback occurred, and it cited neither invalid nor explicitly inapplicable memory. It is therefore qualified as Core B alongside DeepSeek-V3.2 (Core A). Measured usage was 12,974 input tokens and 11,021 output tokens with 252.9 seconds aggregate latency. The output usage was substantially above the pre-run estimate and must be used in Pilot cost planning.
