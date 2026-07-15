# v2 Pilot Report (Development/Validation, offline)

Date: 2026-07-14

Protocol: v2 (`docs/experiment_protocol.md`, draft 2.0)

Test-ID/Test-OOD outcomes accessed: false

Provider: deterministic offline (`DeterministicStrategyProvider`)

## Purpose

Protocol v2 blocks any formal budget until a Development/Validation Pilot
measures strategy-review frequency and cost. This is the **offline** stage of
that Pilot. It establishes the review cadence and operational behavior of the
v2 loop with a network-free provider. It does **not** measure live token cost
or model behavior; those require a separately approved live Pilot.

## Setup

- 4 Validation scenarios: stable, demand jump, gradual demand, supply delay.
- 2 memory methods: VectorMemory and ShiftMem.
- 5 paired seeds (1000–1004).
- 150-day episodes, review interval 5, cooldown 3.
- 40 episodes total, 0 provider fallbacks, no Test scenario touched.

## Key measurement: review frequency

| Metric | Mean per 150-day episode |
|---|---|
| Total reviews | 30.8 |
| Scheduled (periodic) | 23.2 |
| Event-triggered | 0.8 |
| Coalesced (same-day periodic+event) | 6.8 |
| Cooldown-suppressed | 0.5 |
| Parameter churn (changes across reviews) | 4.6 |

Reviews per day: **0.205**, versus **1.0/day** for the retired v1 direct-order
design. On these Validation scenarios the v2 low-frequency reviewer issues
roughly **one fifth** the provider calls of v1 for the same episode length.
Coalescing folded ~6.8 same-day periodic+event triggers into single calls per
episode, and the frozen cooldown suppressed ~0.5 repeated alerts per episode.

## Interpretation and limits

- The **~5× call reduction** is the core cost rationale for v2, now measured
  rather than asserted. It is the frequency component of the budget only.
- The deterministic provider ignores memory content, so these runs are an
  **integration and cadence** result, not a memory-method performance result.
  VectorMemory and ShiftMem produce the same cadence here by construction.
- **Token cost per review is not measured.** A bounded live Development/
  Validation Pilot on the two core models must record input/output tokens,
  latency, and CNY per review before any formal ceiling is proposed.
- Event-trigger frequency depends on detector thresholds, which remain
  Validation-selected and frozen later; the 0.8 event / 0.5 suppressed values
  are provisional under the current provisional thresholds.

## Gate status

- Offline v2 loop, scheduler cadence, and metrics: verified.
- Live token/cost measurement: **pending explicit API-budget approval.**
- v2 freeze: **blocked** until the live Pilot, an approved budget, and a clean
  freeze manifest exist. No Test-ID/Test-OOD execution is authorized.

Raw per-cell data: `artifacts/aggregated/v2_pilot_readiness.json` (trackable).
