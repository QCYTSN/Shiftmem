# Formal Experiment Readiness Audit

Audit date: 2026-07-14  
Audited freeze: `phase4-20260713-b99c0d3e4d27`  
Verdict: **BLOCKED pending protocol v1.1 and a replacement freeze**

## Scope and evidence rule

This audit reviews repository state, frozen configurations, aggregate Development/Validation evidence, and implementation paths. It does not alter the v1 freeze and does not use held-out outcomes. Test-ID and Test-OOD outcomes must not be generated or read before protocol v1.1 and its replacement freeze verify from a clean commit.

The archived v1 package is an immutable audit snapshot. Later live documentation intentionally adds findings discovered after freeze; that divergence is not a reason to rewrite archived files.

## Readiness matrix

| Area | Status | Evidence and consequence |
| --- | --- | --- |
| Freeze integrity | PASS | The sorted SHA-256 manifest for `phase4-20260713-b99c0d3e4d27` verifies. |
| Automated regression suite | PASS | The pre-audit repository passed 206 tests; the live-document requirement is now regression-tested as well. |
| Phase 1 acceptance | PASS | 2,500 network-free scenario/policy/seed runs passed the declared gates. |
| Core model qualification | PASS | DeepSeek-V3.2 and MiniMax-M2.5 passed the fixed qualification gate; GLM-5.1 remains supplementary. |
| Phase 4 Pilot completion | LIMITATION | Eight unique Validation cells completed, but scope was one demand-jump scenario, two seeds, two methods, fixed-policy warm-up, and pre-seeded memories. |
| Detector alert behavior | LIMITATION | Page-Hinkley threshold 48 had zero misses but 283 repeated false-positive signals across 80 Validation episodes. |
| Detector signal contract | BLOCKED | Supply-change selection used quoted lead time, but production runtime does not route that signal to its detectors. |
| H3 stable coverage | BLOCKED | Frozen Test manifests contain no held-out stable scenario. |
| H4 recurrence coverage | BLOCKED | Frozen Test manifests contain no held-out periodic recurrence scenario. |
| Formal endpoint/statistics implementation | BLOCKED | Recovery metrics, paired inference, Holm correction, and final schemas are not fully implemented and tested. |
| Idempotent logging and budget gates | BLOCKED | Cell-level resume can repeat live calls; per-decision journaling/replay and enforced call/cost ceilings are absent. |
| Six-method formal configuration | BLOCKED | No freeze-bound runner currently executes the complete NoMemory, FullHistory, Summary, VectorMemory, TimeDecay, and ShiftMem matrix. |

## Evidence that remains valid

- The environment acceptance results, model qualification outcomes, split hashes, and frozen Pilot aggregates remain valid for their declared scopes.
- The Pilot establishes operational feasibility and supplies provisional variance, latency, token, fallback, and detector-alert evidence.
- Negative operational evidence remains part of the record: repeated false positives, materially higher MiniMax latency, one retained fallback, and duplicate billed calls caused by interrupted cell-level resume.
- The recommendation of 52 seeds per formal cell is a conservative planning value, not a final power conclusion.

## Detector-selection/runtime mismatch

The Validation selector evaluates supply-only shifts through the public `quoted_lead_time` signal. Production `ShiftMemory.observe_outcome` updates change detectors only with `demand` and `lost_sales`. As a result, the frozen supply-change detector ranking does not validate the signal path actually used by the agent.

Protocol v1.1 must choose and document one production signal contract, add regression tests proving that routing, and rerun every affected Development/Validation detector-selection cell. Previously observed Test outcomes cannot be used to choose the contract.

## Hypothesis coverage gaps

H3 requires held-out stable-environment evidence, but neither frozen Test manifest includes a stable scenario. H4 requires periodic recurrence evidence, but neither includes a periodic scenario that can exercise dormancy/reactivation. These are formal design omissions, not merely reporting omissions.

Stable and periodic held-out configurations must be declared, collision-checked, hashed, and frozen without generating their outcomes. Because this changes the formal package, it requires a numbered protocol amendment and replacement freeze.

## Pilot and execution limitations

The Pilot contains one Validation `demand_jump` scenario, two seeds, 30 post-shift decisions per cell, a fixed-policy pre-shift warm-up, four pre-seeded memories, and only VectorMemory versus ShiftMem. It cannot validate all hypotheses or the six-method execution path.

The existing resume mechanism records completed cells but not an idempotent journal for every model decision. A timeout can therefore repeat provider calls before a cell completes, as occurred during the Pilot. Formal execution also lacks freeze-bound run identity, enforced budget ceilings, complete paired-cell checks, and final statistical/result-schema implementations.

## v1.1 work order

1. Add regression coverage for detector signal routing and choose one production signal contract.
2. Rerun affected detector selection on Development/Validation only.
3. Add held-out stable and periodic scenario definitions without generating their outcomes.
4. Implement formal endpoints, recovery metrics, paired statistics, Holm correction, and machine-readable result schemas.
5. Implement a freeze-bound formal runner with per-decision idempotent journaling, response replay, paired completeness checks, and budget gates.
6. Run offline and live Development/Validation dry-runs only.
7. Estimate the complete API matrix and require explicit budget approval.
8. Issue protocol v1.1 and create a replacement freeze.
9. Begin Test-ID/Test-OOD execution only after the replacement freeze verifies from a clean commit.

## Exit criteria

Formal Test execution may begin only when all of the following are true:

- regression tests prove the selected detector signals reach the same runtime path evaluated during selection;
- every affected Development/Validation selector result has been regenerated and recorded;
- held-out stable and periodic definitions pass split-collision validation and their hashes are frozen without outcome access;
- recovery endpoints, paired statistics, multiplicity control, result schemas, and the complete six-method runner have automated tests;
- interrupted decisions replay from an immutable journal without a second provider call, and incomplete batches remain auditable;
- an explicit maximum call/token/cost budget for the full matrix has been reviewed and approved;
- protocol v1.1 lists every amendment and is committed before affected execution;
- a replacement freeze verifies from a clean commit and all network-free tests pass.

Until every criterion is satisfied, the correct next activity is v1.1 engineering and Development/Validation revalidation, not formal Test execution.
