# ShiftMem Documentation

This index separates the completed Protocol-v2 evidence from historical design
and engineering records.

## Start here

1. [Formal post-Test audit](v2_formal_post_test_audit.md) — final results,
   sensitivity analyses, reliability, execution order, and permitted claims.
2. [Experiment protocol](experiment_protocol.md) — research questions,
   architecture, frozen estimand, amendments, and analysis rules.
3. [Model card](model_card.md) — evaluated models, intended use, reliability,
   and limits.
4. [Evidence manifest](../artifacts/aggregated/v2_formal_evidence_manifest.json)
   — authoritative source hashes and closure identity.

## Current Protocol-v2 reports

- [Formal post-Test audit](v2_formal_post_test_audit.md)
- [Formal readiness audit](v2_formal_readiness_audit.md)
- [Model qualification](model_qualification.md)
- [V2 qualification audit](v2_qualification_audit.md)
- [V2 pilot report](v2_pilot_report.md)
- [Memory schema](memory_schema.md)
- [Related-work matrix](related_work_matrix.md)

## Reproducibility

From the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts/finalize_formal_results.py --verify
```

The current closure identity is `v2-formal-results-f4ab41daacf3`. Verification
is deterministic and network-free.

## Historical records

These files remain available for provenance but do not define the final formal
claim set:

- [Original implementation specification](../ShiftMem_Implementation_Spec.md)
- [Formal v1 readiness audit](formal_experiment_readiness_audit.md)
- [Phase 4 pilot report](phase4_pilot_report.md)
- [Protocol v1.1 live Validation report](v1_1_live_validation_report.md)
- [Implementation log](implementation_log.md)

Historical frozen directories under `configs/frozen/` are intentionally kept
byte-stable. Apparent duplication there is part of the audit trail, not an
active source tree to edit or deduplicate.
