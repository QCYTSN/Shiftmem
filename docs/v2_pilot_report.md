# Protocol-v2 Pilot Report

Date: 2026-07-15

Protocol: v2 (`2.0-draft`)

Split: Development/Validation only

Test-ID/Test-OOD outcomes accessed: false

## Decision summary

The bounded live Pilot completed all eight declared cells. It is valid evidence
for provider reliability, review-level token growth, the execution budget, and
journal/replay behavior under the observed Pilot settings. It is not a formal
memory-effect experiment and does not yet satisfy the protocol-2.0 freeze gate,
because the Pilot instantiated ShiftMem defaults rather than the previously
Validation-selected detector, dormancy, and retrieval profile.

No rerun is authorized by this report. The unfavorable provider failures and
fallbacks are retained.

## Offline cadence stage

The network-free stage used four Validation scenarios, VectorMemory and
ShiftMem, five paired seeds, and 150-day episodes. Its 40 episodes averaged
30.8 reviews per episode (0.205/day), compared with 1.0 call/day in the retired
v1 direct-order design. This established the frequency basis for the live
Pilot but did not measure model behavior or billed token usage.

## Live Pilot design

- Run ID: `v2-live-pilot-20260715-a148a81`
- Freeze: `v2-pilot-live-20260715-a148a81`
- Scenario: Validation demand jump only
- Models: DeepSeek-V3.2 and MiniMax-M2.5
- Methods: VectorMemory and ShiftMem
- Paired seeds: 1000 and 1001
- Episode length: 150 days; review interval 5; cooldown 3
- Declared cells: 8; completed cells: 8
- Every provider attempt was fsynced before execution continued.

## Budget and usage

| Metric | Used | Hard limit | Utilization |
|---|---:|---:|---:|
| Provider attempts | 272 | 350 | 77.7% |
| Input tokens | 915,521 | 1,500,000 | 61.0% |
| Output tokens | 114,303 | 500,000 | 22.9% |
| Successful-response token estimate | CNY 3.7710 | CNY 6.00 | 62.8% |

The older CNY-per-call anchor produces CNY 2.4317 for 272 attempts, but it is
below the token-priced estimate and must not be used as the final budget basis.
The CNY 3.7710 estimate covers responses with reported token usage. The 36
failed provider attempts reported no tokens, so the exact account charge for
those failures is not observable from the API records; the approved CNY 6 cap
remains the governing upper bound.

## Reliability and token profile

| Model | Method | Reviews | Attempts | Provider failures | Fallbacks | Input tokens | Output tokens | Estimated CNY |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DeepSeek | VectorMemory | 60 | 60 | 0 | 0 | 83,979 | 4,239 | 0.3614 |
| DeepSeek | ShiftMem | 60 | 60 | 0 | 0 | 396,917 | 6,364 | 1.6259 |
| MiniMax | VectorMemory | 60 | 83 | 24 | 1 | 79,765 | 56,974 | 0.6461 |
| MiniMax | ShiftMem | 60 | 69 | 12 | 3 | 354,860 | 46,726 | 1.1377 |

All 36 attempt errors were provider failures; there were zero JSON/schema parse
errors. The aggregate field `total_parse_failures` is therefore interpreted as
the broader attempt-error count for this frozen run. MiniMax had 36 failures in
152 attempts (23.7%) and four fallbacks in 120 reviews (3.3%). DeepSeek had no
provider failure or fallback in 120 reviews.

ShiftMem used 751,777 input tokens versus VectorMemory's 163,744, a 4.59x
increase under this implementation. Its token-priced cost was CNY 2.7636
versus CNY 1.0075 for VectorMemory. Context growth, not review frequency, is
therefore the main v2 cost risk.

## Exploratory business outcomes

These two-seed, one-scenario results are descriptive engineering evidence only.
They are not used for confirmatory hypotheses, model selection, or Test tuning.

| Model | Vector mean cost | ShiftMem mean cost | Paired mean difference | Vector mean fill | ShiftMem mean fill |
|---|---:|---:|---:|---:|---:|
| DeepSeek | 4,609.0 | 4,929.1 | +320.1 | 0.9980 | 0.9992 |
| MiniMax | 5,048.0 | 5,615.5 | +567.5 | 0.9992 | 0.9992 |

## Conformance limitation

The live runner called `make_memory("shiftmem")`, which instantiated the
current default ShiftMemory profile: Page-Hinkley threshold 5, dormancy
patience 7, and default retrieval weights. The recorded prior Validation
selection uses Page-Hinkley threshold 48, dormancy patience 3, and recency-heavy
retrieval. The formal-v2 controller bounds, cooldown, validation window,
detector, and retrieval fields are also still marked provisional.

Consequently:

- the cost/reliability envelope and the raw provider evidence remain valid;
- the exploratory VectorMemory/ShiftMem business comparison cannot validate
  the final ShiftMem configuration;
- protocol 2.0 finalization and a formal v2 freeze remain blocked until one
  explicit runtime profile is selected, passed through the runner, and verified
  offline on Development/Validation only.

## Provisional formal planning envelope

After explicit profile injection, a new network-free 40-cell readiness run
measured 30.0 reviews per baseline cell and 34.1 per ShiftMem cell (32.05
overall). Extrapolating the live per-review model/method token rates to the
declared 320-cell primary tier, and conservatively applying the highest
observed DeepSeek ShiftMem rate to all 160 secondary cells, gives a base
estimate near CNY 296. Applying the method-specific cadence and a 20% reserve
yields a rounded planning envelope of:

- 20,000 provider attempts;
- 90 million input tokens;
- 7 million output tokens;
- CNY 360.

This is a proposal for review, not an approved formal budget. It must be
recomputed after the runtime profile is frozen, and Test execution remains
unauthorized.

## Evidence

- Raw cells: `artifacts/raw_runs/v2-live-pilot-20260715-a148a81_cells.jsonl`
- Attempt journal: `artifacts/raw_runs/v2-live-pilot-20260715-a148a81_journal.jsonl`
- Aggregate: `artifacts/aggregated/v2-live-pilot-20260715-a148a81_summary.json`
- Derived analysis: `artifacts/aggregated/v2-live-pilot-20260715-a148a81_analysis.json`
- Explicit-profile offline readiness: `artifacts/aggregated/v2_pilot_selected_profile_readiness.json`
