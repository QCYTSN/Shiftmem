# Protocol-v2 Formal Post-Test Audit

## Status

The paid Protocol-v2 held-out experiment completed on 2026-07-22. The exact
matrix contains 160 unique complete cells: 80 Test-ID and 80 Test-OOD. The
confirmatory non-stable population contains 70 paired ShiftMem-versus-
VectorMemory units. No exclusion or rerun was introduced during closure.

The immutable evidence identity is `v2-formal-results-bf7b57070da2`. Run
`.venv\Scripts\python.exe scripts/finalize_formal_results.py --verify` to
recompute all integrity checks and compare the three derived JSON outputs.
This command is network-free.

## Evidence integrity

The closure specification binds five cell JSONL prefixes, four append-only
journals, two split summaries, and the four source freeze directories. Hash,
record-count, run-plan, split, model, method, endpoint-applicability, and paired
unit checks pass. All source freezes verify and all journals contain zero
unresolved reservations.

No raw file was rewritten. The cell serializer used a false default for
`test_outcomes_accessed` in all 160 held-out cells, and the earlier Test-ID
summary also reports false. The derived evidence manifest records these 161
metadata defects, declares their corrected interpretation as true, and records
that they do not alter numeric outcomes. The final Test-OOD summary already
reports true. Future held-out serialization sets the per-cell field explicitly.

## Confirmatory endpoint

The primary difference is ShiftMem minus VectorMemory for
`post_shift_cumulative_regret_30`; negative values favor ShiftMem. Across 70
paired non-stable units, the mean difference is 45.4429, the 95% interval is
[-2.7193, 93.6050], and paired effect size dz is 0.2210. The predeclared
normality/outlier rule selects the Wilcoxon signed-rank approximation, with
two-sided p=0.2034. ShiftMem wins 25 pairs, ties 11, and loses 34. H1 is not
supported by the overall confirmatory result.

The Test-ID mean difference is -2.6733 with p=0.9249. The Test-OOD mean
difference is 81.5300 with p=0.0932. DeepSeek and MiniMax show different
directions; these model and scenario decompositions are retained in the
machine-readable output and require cautious multiplicity-aware interpretation.
Stable-environment total cost is descriptive only, as required by the protocol.

## Reliability and cost

The 160 cells contain 5,176 strategy reviews and 6,189 attempts recorded at the
cell level. They record 1,680 parse failures and 667 retained-strategy
fallbacks. Parse failures per recorded attempt are 0.2714; fallbacks per review
are 0.1289. Recovery is observed in 61 of 140 applicable cells. Reliability is
reported by split, model, method, and their joint groups in the derived audit;
provider and parse failures remain in the business outcomes as predeclared.

The four journals contain 4,558 successful responses and 1,705 terminal failed
attempts. Estimated successful-response cost is CNY 108.4874. The failed
reservation ledger is CNY 93.8759 and is not an estimate of official charges.
The official provider-billing field remains null until a provider statement is
supplied; this is an administrative reconciliation item rather than an
experimental rerun.

## Reliability-outcome sensitivity

This layer is post-hoc and descriptive; it does not alter or replace the
confirmatory 70-pair analysis. For every paired unit, the audit calculates the
ShiftMem-minus-VectorMemory difference in parse-failure rate, fallback rate,
and provider-failure rate, then relates each burden difference to the paired
regret difference. Pearson correlations are -0.0700, -0.0551, and -0.0722;
Spearman correlations are -0.1045, -0.0751, and -0.1340, respectively. These
weak associations provide no simple evidence that higher relative failure
burden explains the unfavorable overall ShiftMem direction.

The audit also recomputes descriptive results for pairs in which neither
method experienced the event. The mean ShiftMem-minus-VectorMemory differences
are +134.5280 for 25 zero-parse-failure pairs, +91.8875 for 32 zero-fallback
pairs, and +125.0000 for 26 zero-provider-failure pairs. These subsets are
post-hoc and model-imbalanced--notably, the zero-parse and zero-provider subsets
contain no MiniMax pairs--so they cannot establish robustness or causality.
They do show that the primary direction is not removed merely by selecting
observed zero-event pairs. Split- and model-specific associations, empirical
median burden strata, and all subset sample counts are preserved in the
machine-readable reliability audit.

## Machine-readable outputs

- `artifacts/aggregated/v2_formal_evidence_manifest.json`
- `artifacts/aggregated/v2_formal_statistical_analysis.json`
- `artifacts/aggregated/v2_formal_reliability_audit.json`

Paper prose, formatted tables, and visual figures are intentionally outside
this closure task.
