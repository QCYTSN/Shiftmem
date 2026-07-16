# Protocol-v2 Formal Readiness Audit

Audit date: 2026-07-16

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
| Formal v2 execution runner | PASS ENGINEERING / ACTIVATION BLOCKED | The CLI plans both tiers, executes offline or journal-bound providers, pairs with Oracle, serializes endpoints, and rejects held-out manifests before scenario loading. The checked-in config remains unapproved and no v2 replacement freeze exists, so live activation fails closed. |
| Formal journaling/replay integration | PASS | Every paid attempt is bound to run ID, freeze ID, clean commit, and config hash. A conservative call/token/cost reservation is fsynced before networking and terminalized afterward. Terminal attempts replay without calls; unresolved reservations hard-stop for reconciliation. Completed cells carry and validate the same run identity. |
| Protocol and replacement freeze | TOOLING PASS / ACTIVATION BLOCKED | The v2 builder now creates a deterministic content-addressed candidate covering code, tests, protocol, configs, all split scenario definitions, qualification/Pilot evidence, formal rehearsal evidence, and raw journals. Final directory creation remains blocked while protocol is draft or budget approval is absent. |
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
full suite passed 336 tests after the live-journal and replacement-freeze
builder integration.

## Required next work order

1. Commit and run the protocol-v2 candidate builder from a clean tree; archive
   its content-addressed file list and exact remaining blockers.
2. Request explicit approval of the proposed formal budget; approval must not
   be inferred from earlier Pilot spending.
3. Record that approval in the formal config, finalize protocol 2.0, and
   create/verify a clean replacement freeze containing the exact approved
   config bytes.
4. Access Test-ID/Test-OOD only after both budget approval and freeze success.

The next authorized activity is a clean-tree candidate-freeze rehearsal,
not provider spending and not Test execution.
