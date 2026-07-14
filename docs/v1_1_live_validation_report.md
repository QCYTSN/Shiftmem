# Protocol v1.1 Live Validation Report

> **Historical status (2026-07-14):** This direct-daily-order design was retired before Test execution and is not a v2 performance result or budget basis. The archived raw/aggregate evidence remains unchanged.

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

The original report incorrectly counted nine scenarios. The declared Test-ID and Test-OOD manifests contain eight scenarios, so the retired direct-order matrix would contain 8 scenarios × 52 seeds × 2 models × 6 methods = 4,992 cells and 149,760 planned model decisions. Scaling the observed one-scenario/one-seed cost by 416 gives an estimated CNY 1,338.86 and a 20% safety value of CNY 1,606.63.

The following table is retained as the original, now-superseded nine-scenario extrapolation so the historical decision trail remains auditable:

| Quantity | Estimate | 20% safety proposal |
| --- | ---: | ---: |
| Provider attempts | 171,288 | 206,000 cap |
| Input tokens | 289,375,164 | 348,000,000 cap |
| Output tokens | 74,781,252 | 90,000,000 cap |
| Cost | CNY 1,506.22 | CNY 1,810 cap |

This was a planning extrapolation from one Validation scenario and one seed, not a guarantee. Protocol v1.1 was not frozen for Test execution, and neither its original nor corrected projection authorizes v2 calls.

## Evidence files

- Trackable aggregate: `artifacts/aggregated/formal_v1_1_live_validation.json`
- Approved configuration: `configs/experiments/formal_v1_1_live_validation.yaml`
- Raw cell and per-attempt journal files remain ignored under `artifacts/raw_runs/`.
