# Phase 4 Pilot Report

## Scope and gate

This bounded Pilot used Development/Validation configuration only. Test-ID and Test-OOD outcomes were not generated or read. Matrix completion: 8/8 runs; complete = `true`.

## Pilot design boundary

The Pilot covered one Validation `demand_jump` scenario, two seeds, and only VectorMemory versus ShiftMem for Core A and Core B. Each cell used a fixed-policy pre-shift warm-up, four pre-seeded memories, and 30 post-shift model decisions. It did not exercise the complete six-method formal matrix, held-out scenarios, stable-environment non-degradation, or periodic dormancy/reactivation.

The recommended 52 seeds is therefore a provisional planning value based on only two paired observations per model, not a frozen power determination for the complete formal matrix. The live report adds this interpretation after the v1 freeze; the archived copy inside `configs/frozen/phase4-20260713-b99c0d3e4d27/` remains unchanged as an audit snapshot.

## Variance and paired endpoint

Negative regret favors ShiftMem over its paired VectorMemory run.

| Core model | Paired seeds | Mean 30-day regret | Regret SD | Recommended seeds |
| --- | ---: | ---: | ---: | ---: |
| Deepseek_V3_2 | 2 | -54.800 | 213.546 | 36 |
| Minimax_M2_5 | 2 | -56.600 | 256.538 | 52 |

## Runtime and token usage

- Provider-reported latency: 3017.7 seconds.
- Completed-cell provider calls: 241.
- Total tokens: 638629.
- Fallback decisions: 1.

## Metric completeness

Required per-run metrics complete: `true`.

## Operational caveats

- Validation selected Page-Hinkley threshold 48 by the frozen misses/false-positives/delay ordering: 0 misses but 283 repeated false-positive signals across 80 episodes. Formal interpretation must treat this alert rate as a material detector limitation.
- An outer command timeout left the original provider process running while a resume began, producing duplicate completed MiniMax cells and some extra billed calls. Final evidence retains the first complete result for each model/method/seed key; duplicate results were discarded without outcome-based selection.
- The retained eight-cell matrix contains one fallback decision; matrix and metric completeness remain intact, but model reliability is not perfect.

## Recommended formal seed count

Using a two-sided normal approximation with 5% alpha, 80% power, and minimum relevant paired effect 100.0, the conservative recommendation is **52 seeds per formal cell**. With only two Pilot seeds this is a planning estimate, not a precise power analysis.
