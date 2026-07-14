# Protocol v1.1 Live Validation Report

Date: 2026-07-14  
Scope: one Validation `demand_jump` scenario, seed 1000, two core models, six memory methods, 30 post-shift decisions per cell  
Authorization: user-approved maximum CNY 30  
Test outcomes accessed: **false**

## Completion and cost

- Cells: 12/12 complete.
- Provider attempts reported by cell logs: 366.
- Successful responses in the initial journal: 360.
- Input tokens: 618,323.
- Output tokens: 159,789.
- Estimated cost: CNY 3.2184.
- Fallback decisions: 0.
- Historical unjournaled failed attempts: 6.

All 12 cells are retained. MiniMax required additional attempts in Summary, VectorMemory, TimeDecay, and ShiftMem; no cell or unfavorable inventory outcome was deleted.

## Journal deviation and correction

The first v1.1 journal implementation persisted successful provider responses but not provider exceptions. Cell logs therefore counted 366 attempts while the journal counted 360, exceeding the configured 360-call cap by six attempts even though the CNY 30 cost cap was not approached.

This is retained as an operational deviation. The corrected journal persists a sanitized failed entry before re-raising the provider error, counts it against every budget, and replays the failure during recovery without another call. The six historical failures cannot be reconstructed at per-attempt detail and are explicitly reported instead of fabricated.

## Formal matrix projection

The formal matrix contains 9 scenarios × 52 seeds × 2 models × 6 methods = 5,616 cells and 168,480 planned model decisions. Scaling the observed attempt and token ratios by 468 gives:

| Quantity | Estimate | 20% safety proposal |
| --- | ---: | ---: |
| Provider attempts | 171,288 | 206,000 cap |
| Input tokens | 289,375,164 | 348,000,000 cap |
| Output tokens | 74,781,252 | 90,000,000 cap |
| Cost | CNY 1,506.22 | CNY 1,810 cap |

This is a planning extrapolation from one Validation scenario and one seed, not a guarantee. Formal API budget approval remains required before protocol v1.1 can be frozen or Test execution can begin.

## Evidence files

- Trackable aggregate: `artifacts/aggregated/formal_v1_1_live_validation.json`
- Approved configuration: `configs/experiments/formal_v1_1_live_validation.yaml`
- Raw cell and per-attempt journal files remain ignored under `artifacts/raw_runs/`.
