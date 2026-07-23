# Protocol-v2 Formal Post-Test Audit

## Status

The paid Protocol-v2 held-out experiment completed on 2026-07-22. The exact
matrix contains 160 unique complete cells: 80 Test-ID and 80 Test-OOD. The
confirmatory non-stable population contains 70 paired ShiftMem-versus-
VectorMemory units. No exclusion or rerun was introduced during closure.

The current evidence-closure identity is `v2-formal-results-b70e28f0fa8c`. The
five cell files, four journals, and two summaries are byte-identical to the
first closure; the identity changed because the manifest also binds the
post-Test analysis code, which now includes the sensitivity analyses below. Run
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

## Endpoint terminology

The serialized field remains `post_shift_cumulative_regret_30` so that the
predeclared protocol and raw records are not rewritten. `OraclePolicy` is a
parameter-aware base-stock heuristic, not a proof of the globally optimal
policy, and negative raw values occur. Paper-facing reporting therefore calls
this endpoint the **30-day oracle-relative cost gap**. The shared Oracle term
cancels exactly from the paired ShiftMem-minus-VectorMemory difference, so this
terminology correction does not change the primary numeric contrast.

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

## Mean-aligned clustered sensitivity

The frozen confirmatory calculation above is retained unchanged. A post-hoc
sensitivity analysis addresses two inferential limitations: Wilcoxon does not
directly test the declared mean estimand, and the DeepSeek and MiniMax cells for
the same scenario and environment seed share deterministic demand and supply
streams. It therefore averages the two model-specific method differences into
35 scenario-seed clusters, bootstraps the five environment seeds within each of
the seven fixed scenario strata, and applies equal scenario weight.

The resulting mean remains +45.4429. The 50,000-resample cluster-bootstrap 95%
interval is [11.2600, 79.0859], and the two-sided cluster sign-flip p-value for
the equal-scenario mean is 0.0414. This post-hoc result points in the
**unfavorable** direction for ShiftMem; it does not convert H1 into a supported
hypothesis and must not replace or be presented as the predeclared test.

The exploratory DeepSeek-minus-MiniMax method-effect contrast is +124.5771,
with cluster-bootstrap interval [38.5934, 216.0517] and unadjusted sign-flip
p=0.0154. This supports reporting model heterogeneity as a post-hoc diagnostic,
not claiming a general model interaction without replication or multiplicity
control.

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

## Execution-order audit

The append-only journals do not contain wall-clock timestamps, so the audit
uses terminal-record append order and does not claim a timestamp analysis. All
70 applicable pairs executed VectorMemory before ShiftMem; the design was not
randomized or counterbalanced. The early 35 pairs have a mean method difference
of +58.5829 and the late 35 have +32.3029. Pearson and Spearman associations
between pair position and outcome difference are 0.1593 and 0.1753. Run-segment
means vary from -8.3800 in the original run to +107.6000 in one continuation,
with +42.1571 in the final continuation.

These diagnostics do not show a monotonic late-run deterioration that simply
explains the unfavorable overall direction, but the fixed method order remains
an unresolved design limitation. No post-hoc adjustment can establish the
counterfactual result under randomized order.

## Claim scope

| Claim | Current status | Permitted interpretation |
| --- | --- | --- |
| H1: ShiftMem lowers the 30-day gap | Confirmatory test complete | Not supported; the point estimate is unfavorable |
| Mean-effect robustness | Post-hoc sensitivity complete | Clustered mean inference is also unfavorable; label as sensitivity only |
| RQ3/RQ4 scenario/model consistency | Descriptive and post-hoc | Strong heterogeneity signal; no universal transfer claim |
| H2: less invalid reuse than all baselines | Paid held-out tier not run | Not tested formally |
| H3: no stable degradation | No frozen non-inferiority margin | Descriptive only; no equivalence claim |
| H4: dormancy/reactivation mechanism | Required ablation not run | Not tested |
| H5: statistical versus LLM-only trigger | Required ablation not run | Not tested |
| Reliability caused the outcome | Observational audit only | No simple association found; causality not established |

The defensible paper scope is therefore a preregistered negative-result and
systems-diagnostic study of conditional change-aware memory under the tested
inventory simulator, two provider-hosted models, and observed reliability
conditions. It does not establish general superiority, equivalence, or a
specific lifecycle mechanism.

## Machine-readable outputs

- `artifacts/aggregated/v2_formal_evidence_manifest.json`
- `artifacts/aggregated/v2_formal_statistical_analysis.json`
- `artifacts/aggregated/v2_formal_reliability_audit.json`

The 11 immutable raw evidence files also have a read-only convenience archive
at `artifacts/releases/v2-formal-results-b70e28f0fa8c-raw-evidence.zip` (2,735,947
bytes; SHA-256
`3f462721f6bc025043ac262c0e06724ac6b1a5479372ddc54a006834fa94e49f`).
The archive does not replace the authoritative per-file hashes in the evidence
manifest.

Paper prose, formatted tables, and visual figures are intentionally outside
this closure task.
