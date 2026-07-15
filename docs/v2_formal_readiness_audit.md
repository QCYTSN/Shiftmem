# Protocol-v2 Formal Readiness Audit

Audit date: 2026-07-15

Verdict: **BLOCKED before Test execution**

No Test-ID/Test-OOD outcome was generated or read during this audit.

## Current readiness

| Area | Status | Evidence and consequence |
|---|---|---|
| Core-model strategy qualification | PASS | DeepSeek-V3.2 and MiniMax-M2.5 passed the frozen 4/4 strategy gate with no parse/fallback/applicability failure. |
| Bounded live Pilot | PASS WITH LIMITATION | Eight Validation cells completed under 272/350 attempts and CNY 3.7710 successful-response token estimate; MiniMax recorded 36 provider failures and four fallbacks. The Pilot used old ShiftMem defaults, so its business comparison is not final-profile evidence. |
| Runtime profile | PASS | Future paths require PH 10/0.1/48, validation window 3, dormancy 3, recency-heavy retrieval, explicit controller defaults/bounds, and scheduler 5/3. |
| Per-review strategy caps | PASS | Caps 7/1.0/1 cover all 240 observed valid Pilot revisions and are enforced deterministically without changing recorded Pilot behavior. |
| Offline explicit-profile readiness | PASS | Forty Development/Validation cells completed with zero fallback; baseline cadence was 30.0 reviews and ShiftMem cadence 34.1. |
| Provisional budget model | READY FOR LATER REVIEW | Proposed envelope is 20,000 attempts, 90M input tokens, 7M output tokens, and CNY 360. It is not approved. |
| Formal v2 execution runner | BLOCKED | `run_formal_experiment.py` can validate/build a v2 plan in helper functions, but its CLI still validates the retired v1 six-method shape and deliberately disables live execution. It does not execute the 320-cell primary plus 160-cell secondary v2 matrix. |
| Formal journaling/replay integration | BLOCKED | The live Pilot proves the mechanism, but the complete v2 formal cell runner has not yet bound every review attempt and completed cell to a replacement-freeze identity. |
| Protocol and replacement freeze | BLOCKED | Protocol remains `2.0-draft`; no clean protocol-v2 replacement freeze exists. |
| Formal API budget | BLOCKED | The CNY 360 proposal has not been explicitly approved and must not be inferred from prior Pilot/qualification approvals. |

## Direction assessment

The project remains aligned with its purpose. The LLM changes a low-frequency,
bounded strategy; a shared deterministic controller owns every daily order;
and the primary comparison remains ShiftMem versus VectorMemory under paired
scenarios and seeds. The live Pilot exposed two risks that belong in RQ5 rather
than being hidden: ShiftMem context growth and MiniMax provider unreliability.

The main drift risk is now premature held-out execution. Model qualification
and a successful Pilot do not substitute for a freeze-bound formal runner.

## Required next work order

1. Implement a protocol-v2 formal executor for the declared 320 primary and
   160 secondary cells using the explicit runtime profile.
2. Bind every provider attempt to the replacement-freeze identity and reuse
   the fsynced replay journal; archive partial batches and enforce paired-cell
   completeness.
3. Produce a network-free Development/Validation dry-run that exercises all
   six memory methods, both tiers, endpoints, aggregation, and recovery.
4. Re-run protocol, split, statistics, journal-replay, compile, and full-suite
   checks from a clean commit.
5. Only then request explicit approval of the proposed formal budget.
6. Finalize protocol 2.0 and create/verify a clean replacement freeze.
7. Access Test-ID/Test-OOD only after both budget approval and freeze success.

The next authorized activity is therefore offline formal-runner engineering,
not provider spending and not Test execution.
