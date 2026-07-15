# Protocol v2 Qualification Harness Audit

Date: 2026-07-15

Status: `inconclusive_harness_invalid`

## Decision

The two 2026-07-15 strategy-qualification executions are preserved as
Development/Validation engineering evidence, but they cannot qualify or
disqualify DeepSeek-V3.2 or MiniMax-M2.5. This status is caused by the harness,
not by reinterpretation of either model's unfavorable monotonicity result.

The strict gate remains unchanged:

```text
monotonicity_checks == 4
monotonicity_passes == 4
```

## Preserved evidence

| Artifact | SHA-256 |
|---|---|
| `artifacts/raw_runs/model_qualification_v2.jsonl` | `AC43899348BDA28CF8870F7F27A9DC6160C8B4DA776B23C824C27A3A844C95C9` |
| `artifacts/aggregated/model_qualification_v2_summary.json` | `ECFA8ED57A2F4D2B11F5E6FD10189021706515A8A7E1237B9724A18EBD58AC35` |

The raw artifact contains 24 result rows. Approximately 48 provider calls were
reported for the latest execution. Because the old result schema did not retain
attempts, the exact first-attempt outputs cannot be reconstructed. The two-to-one
call/result ratio is consistent with one hidden correction retry per case, but
this remains an inference rather than recoverable raw evidence.

These files must not be deleted, edited, or overwritten. Future qualification
runs use new run-specific paths and run IDs.

## Harness defects

1. The standard strategy qualification path constructed its provider with the
   archived v1 daily-order system prompt and user-message builder. The v2
   correction text was only added after a failed attempt.
2. A successful retry discarded the earlier parse/schema error, so
   `parse_failure_count: 0` meant zero unresolved cases rather than zero failed
   attempts.
3. Runtime and qualification requests omitted the protocol-required current
   strategy and trigger evidence.
4. The pressured lost-sales history combined positive lost sales with positive
   ending inventory and left final observation fields inconsistent with recent
   history.
5. Output files lacked a run ID, prompt/config hashes, per-attempt evidence, and
   default overwrite protection.

## Repair boundary

The conformance repair changes only the model-facing v2 request contract, prompt
routing, qualification fixtures, attempt accounting, and run provenance. It
does not change the controller formula, strategy bounds, four-of-four gate,
formal endpoint, memory algorithms, scenarios, paired seeds, or statistical
analysis.

No provider call and no Test-ID/Test-OOD access is part of the repair.

## Project-direction assessment

The hierarchical v2 direction remains aligned with the project purpose: it
tests memory-conditioned strategy revision while a shared deterministic
controller isolates daily execution. This supports the main question of whether
lifecycle-aware memory improves adaptation and reduces invalid reuse under
regime shift.

The current drift risk is spending repeated cycles optimizing model eligibility
instead of evaluating ShiftMem's memory hypotheses. After the repaired harness
passes offline verification, the prompt, fixtures, gate, and provenance format
must be frozen. Each candidate may then receive at most one newly
budget-approved qualification run. Its outcome is accepted without another gate
revision. If fewer than two core models qualify, the project records the
limitation and makes a separately documented model-selection or scope decision.

Formal Test execution remains blocked until model qualification, protocol
finalization, budget approval, and a clean v2 freeze all succeed.
