# ShiftMem Evaluation Model Card

## Purpose

ShiftMem is a research system, not a released foundation model. This card
documents the provider-hosted language models used inside the bounded strategy
review layer of the completed Protocol-v2 inventory experiment.

## Evaluated models

| Label | Provider | Model identifier | Formal role |
| --- | --- | --- | --- |
| DeepSeek | SiliconFlow | `deepseek-ai/DeepSeek-V3.2` | Core model A |
| MiniMax | SiliconFlow | `MiniMaxAI/MiniMax-M2.5` | Core model B |

The identifiers reproduce the provider configuration used during the July 2026
experiment. Provider-side implementations may change without a new repository
commit, so future runs should not assume byte-identical model behavior from the
name alone.

## Agent role

The model receives public realized inventory history, the active bounded
strategy, trigger evidence, and method-specific memory context. It may propose
only `forecast_window`, `safety_stock_multiplier`, and `lead_time_buffer`, plus
cited memory IDs, confidence, and a short reason.

The model cannot:

- issue the daily inventory order;
- change the deterministic controller or supplier;
- change its review interval or cooldown;
- access hidden regime identity, future outcomes, or Oracle context;
- directly assign memory validity or lifecycle state.

Schema-invalid output receives one correction attempt. A second failure keeps
the previous valid strategy and is included in both reliability and business
outcomes.

## Formal evaluation

The completed held-out matrix contains 160 cells across two methods, two models,
eight scenarios, and five paired environment seeds. The primary non-stable
population contains 70 ShiftMem-versus-VectorMemory pairs.

The predeclared overall result does not support ShiftMem superiority: the mean
30-day oracle-relative cost-gap difference is +45.44, with 95% interval
[-2.72, 93.60] and Wilcoxon p=0.203. Positive values are unfavorable to
ShiftMem. A post-hoc clustered mean sensitivity is also unfavorable, while the
two models show materially different method-effect directions.

## Reliability

Across the complete matrix, 27.1% of cell-recorded attempts had a parse failure
and 12.9% of reviews retained the prior strategy through fallback. Failure rates
were not balanced across the two models. The evaluation therefore measures the
deployed combination of memory, model compliance, provider behavior, and
fallback logic—not an isolated memory algorithm.

## Intended use

- controlled research on conditional agent memory;
- reproducibility and auditability studies;
- analysis of model-dependent behavior under synthetic nonstationarity;
- testing bounded LLM strategy-review architectures.

## Out-of-scope use

- autonomous production inventory control;
- claims of model or memory superiority outside the tested matrix;
- safety-critical or financially consequential deployment;
- evaluation of general reasoning ability;
- inference about provider models not explicitly tested here.

## Limitations

The experiment uses synthetic single-item environments, one provider, fixed
method order, five environment seeds per scenario, and no independent LLM-output
replications. The so-called Oracle is a parameter-aware base-stock heuristic,
not a proof of globally optimal control. See the
[post-Test audit](v2_formal_post_test_audit.md) for the complete claim scope.

## Reproducibility

Exact provider/model IDs, dependency versions, source commits, configuration
hashes, and evidence hashes are recorded in the three derived Protocol-v2 JSON
artifacts. Network-free verification uses:

```powershell
.venv\Scripts\python.exe scripts/finalize_formal_results.py --verify
```
