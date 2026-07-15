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
| Formal v2 execution runner | PASS OFFLINE / LIVE BLOCKED | The CLI now plans both hierarchical tiers, executes complete network-free cells, pairs every cell with Oracle, serializes the primary endpoint and recovery, and rejects held-out manifests before scenario loading. Live provider execution remains deliberately disabled. |
| Formal journaling/replay integration | PARTIAL | Completed cells are schema-validated, fsynced one per JSONL line, resumed without duplication, and checked against the exact plan. Binding every live provider attempt to a verified replacement-freeze identity remains outstanding. |
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

The pre-freeze executor audit found and corrected two comparison defects.
Stochastic supplier fills were previously consumed in policy-dependent order
event sequence; fills are now derived from the master supply stream and
calendar order day. Non-ShiftMem v2 baselines were also not receiving completed
strategy experiences; all six methods now use the same delayed
strategy-revision experience unit. Historical Pilot evidence is not
reinterpreted as final paired business evidence.

## Offline formal rehearsal evidence

The Validation rehearsal completed 48/48 cells: 32 primary cells and 16
secondary cells, covering all six memory methods. The 36 non-stable cells
produced paired 30-day regret and recovery outputs; the 12 stable cells marked
the adaptation endpoint not applicable. There were 1,512 deterministic offline
review attempts, zero parse failures, zero fallbacks, zero external provider
calls, and no Test outcome access. Re-execution left the 48-line raw JSONL hash
unchanged, confirming exact resume and deduplication. The compatible-environment
full suite passed 323 tests.

## Required next work order

1. Bind every provider attempt to the replacement-freeze identity and reuse
   the fsynced replay journal; archive partial batches and enforce paired-cell
   completeness.
2. Add live cost accounting and fail-closed budget enforcement to the completed
   cell executor without enabling held-out execution.
3. Re-run protocol, split, statistics, journal-replay, compile, and full-suite
   checks from a clean commit.
4. Only then request explicit approval of the proposed formal budget.
5. Finalize protocol 2.0 and create/verify a clean replacement freeze.
6. Access Test-ID/Test-OOD only after both budget approval and freeze success.

The next authorized activity is formal live-journal and budget-gate engineering,
not provider spending and not Test execution.
