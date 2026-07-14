# Post-Freeze Audit Documentation and v1.1 Readiness Design

## Objective

Preserve `phase4-20260713-b99c0d3e4d27` as an immutable, verified v1 audit snapshot while correcting the live repository documentation and defining the engineering work required before any Test-ID or Test-OOD outcome is generated.

This change does not start formal experiments, alter frozen files, inspect Test outcomes, or claim that v1 is ready for confirmatory execution.

## Confirmed v1 state

- Freeze ID `phase4-20260713-b99c0d3e4d27` verifies against its sorted SHA-256 manifest.
- The repository passes 206 tests.
- Phase 1 completed 2,500 network-free runs and all acceptance gates.
- DeepSeek-V3.2 and MiniMax-M2.5 qualified as the two core models; GLM-5.1 remains supplementary.
- Validation selected Page-Hinkley threshold 48, dormancy patience 3, and recency-heavy retrieval.
- The Phase 4 Pilot completed eight unique cells without reading Test-ID or Test-OOD outcomes.

## Blocking findings

### 1. Detector-selection/runtime mismatch

The Validation selector evaluates supply-only changes through the public `quoted_lead_time` signal. The production `ShiftMemory.observe_outcome` path updates detectors only with `demand` and `lost_sales`. Therefore the frozen supply-change detector evidence does not test the signal path used by the runtime.

This is an implementation-validation mismatch, not merely a documentation issue. It must be corrected with regression tests and affected Validation selection rerun before a replacement freeze.

### 2. Hypothesis coverage gaps

The frozen Test-ID and Test-OOD manifests contain no stable scenario. H3 therefore lacks a held-out stable evaluation cell. They also contain no periodic recurrence scenario, so H4 lacks a held-out recurrence cell.

Held-out stable and periodic scenarios must be specified before any Test outcome is generated. Adding them changes the formal package and requires a versioned protocol amendment and replacement freeze.

### 3. Missing formal execution infrastructure

`src/shiftmem/evaluation/statistics.py` and `src/shiftmem/logging/run_logger.py` remain placeholders. There is no formal six-method experiment configuration or runner. The current Pilot resumes only at completed-cell granularity; an interrupted cell can repeat provider calls.

Formal execution requires freeze verification, immutable run identity, per-decision journaling, idempotent provider-response replay, paired completeness checks, cost/call ceilings, and explicit incomplete-run retention.

### 4. Pilot scope limits

The Pilot used one Validation demand-jump scenario, two seeds, a fixed-policy pre-shift warm-up, and pre-seeded memories. Its 52-seed recommendation is a conservative planning estimate based on two paired observations per model, not a final power determination for the complete formal matrix.

The Pilot remains valid as bounded operational evidence, but its report must state these limitations explicitly.

### 5. Detector and provider operational risks

The selected detector had zero misses but 283 repeated false-positive signals across 80 Validation episodes. MiniMax-M2.5 also showed materially higher latency than DeepSeek-V3.2, and the Pilot retained one fallback. These are reportable limitations rather than grounds for deleting unfavorable results.

## Documentation changes

The implementation phase will update only live, non-frozen documentation:

1. `README.md`
   - replace the obsolete pre-freeze qualification state;
   - add the verified freeze ID and current readiness status;
   - state that formal execution is blocked pending v1.1;
   - link the audit and Pilot report.
2. `docs/implementation_log.md`
   - append Phase 4 selection, second-core qualification, Pilot, freeze, and post-freeze audit entries;
   - record the detector mismatch and hypothesis-coverage gaps as deviations requiring correction.
3. `docs/phase4_pilot_report.md`
   - disclose fixed-policy warm-up, pre-seeded memories, one-scenario/two-seed scope, and provisional power estimate;
   - preserve all existing measured values and caveats.
4. `docs/formal_experiment_readiness_audit.md`
   - provide a single pass/blocked matrix;
   - identify v1 evidence that remains valid;
   - define exit criteria for v1.1 and prohibit Test outcome access before the new freeze.

No file under `configs/frozen/phase4-20260713-b99c0d3e4d27/` will be edited. The divergence between the archived v1 documents and later live documentation is intentional and will be explained in the audit.

## v1.1 work order

The next implementation plan will use this order:

1. Add regression coverage for detector signal routing and choose one production signal contract.
2. Rerun affected detector selection on Development/Validation only.
3. Add held-out stable and periodic scenario definitions without generating their outcomes.
4. Implement formal endpoints, recovery metrics, paired statistics, multiplicity control, and machine-readable result schemas.
5. Implement a freeze-bound formal runner with per-decision idempotent journaling and budget gates.
6. Run offline and live Development/Validation dry-runs only.
7. Estimate the complete API matrix and require explicit budget approval.
8. Issue protocol v1.1 and create a replacement freeze.
9. Begin Test-ID/Test-OOD execution only after the replacement freeze verifies from a clean commit.

## Verification and acceptance

The documentation update is complete when:

- all four live documents agree on v1 status and v1.1 blockers;
- no placeholder or unsupported readiness claim remains;
- the archived v1 freeze still verifies byte-for-byte;
- protocol and split validators still pass;
- the full test suite passes;
- Git shows only the intended documentation changes.

