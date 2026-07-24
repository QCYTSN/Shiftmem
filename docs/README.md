# ShiftMem Documentation

This index separates the completed Protocol-v2 evidence from historical design
and engineering records.

## Start here

1. [Manuscript source and build guide](../paper/README.md) — complete paper,
   publication figures, source tables, references, and compilation steps.
2. [Formal post-Test audit](v2_formal_post_test_audit.md) — final results,
   sensitivity analyses, reliability, execution order, and permitted claims.
3. [Experiment protocol](experiment_protocol.md) — research questions,
   architecture, frozen estimand, amendments, and analysis rules.
4. [Model card](model_card.md) — evaluated models, intended use, reliability,
   and limits.
5. [Evidence manifest](../artifacts/aggregated/v2_formal_evidence_manifest.json)
   — authoritative source hashes and closure identity.
6. [Demo design specification](demo_design_spec.md) — evidence-first product
   scope, interaction model, visual system, and implementation acceptance
   criteria for ShiftMem Evidence Lab.

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
.venv\Scripts\python.exe scripts/verify_release_archive.py
```

The current closure identity is `v2-formal-results-f4ab41daacf3`. Verification
is deterministic and network-free. The public command verifies the release
archive and every manifest-declared raw source. In the original workspace,
where ignored raw sources remain at their declared paths, run
`.venv\Scripts\python.exe scripts/finalize_formal_results.py --verify` to
reconstruct and compare all aggregate outputs as well.

## Local evidence Demo

```powershell
.venv\Scripts\python.exe -m demo.export_web
cd demo-web
pnpm install
pnpm dev
```

Then open `http://127.0.0.1:5173`. Python verifies and exports the frozen
evidence package; the TypeScript client is a read-only browser over that
derived contract and does not make model-provider calls. A clean clone uses
the tracked, checksummed release archive when local raw-run files are absent.
See the [browser guide](../demo-web/README.md) and
[Python evidence adapter](../demo/README.md).

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
