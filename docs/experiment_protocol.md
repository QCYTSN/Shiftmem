# Experiment Protocol

Protocol version: 1.1
Preparation date: 2026-07-14
Replacement freeze: pending formal API budget approval
Scope: ShiftMem single-item lost-sales inventory experiments

## Status and amendment policy

Version 1.0 remains archived in freeze `phase4-20260713-b99c0d3e4d27`. Version 1.1 is a pre-Test amendment prepared after a repository audit and Development/Validation-only dry-run; no Test-ID or Test-OOD outcome was generated or read. Changed fields are the detector signal contract, Core B identity, held-out H3/H4 coverage, formal statistics implementation, decision journaling, six-method runner, and budget gates. The primary endpoint, primary comparison, exclusion rules, and statistical decision tree are unchanged.

Version 1.1 is not frozen and does not authorize Test execution until the formal API budget is explicitly approved and a replacement freeze verifies from a clean commit.

Implementation bug fixes are permitted after freeze only with a failing regression test and a rerun of every affected configuration. Provider retirement or model unavailability may trigger a model amendment, but the unavailable model and failed attempt remain documented.

## Research questions and hypotheses

- **RQ1:** Does ShiftMem reduce cumulative excess cost after a regime change and shorten recovery?
- **RQ2:** Does ShiftMem reuse fewer invalid experiences than FullHistory, Summary, VectorMemory, and TimeDecay?
- **RQ3:** Are effects consistent across abrupt, gradual, periodic, and combined changes?
- **RQ4:** Do effects transfer across two open model families?
- **RQ5:** Are the gains auditable at acceptable token, latency, failure, and memory-size cost?

The hypotheses are fixed:

- **H1:** ShiftMem has lower post-shift cumulative regret than VectorMemory.
- **H2:** ShiftMem has lower invalid memory reuse rate than other memory baselines.
- **H3:** ShiftMem does not materially degrade stable-environment performance.
- **H4:** Dormancy/reactivation is particularly useful under periodic recurrence.
- **H5:** Statistical detectors are more stable and less costly than LLM-only change judgment.

## Primary estimand and endpoint

The primary comparison is **ShiftMem versus VectorMemory**. The estimand is the mean paired method difference, ShiftMem minus VectorMemory, for post-shift cumulative regret relative to Oracle over the first 30 completed post-shift days. The serialized endpoint name is `post_shift_cumulative_regret_30`; lower values favor ShiftMem.

The confirmatory population consists of non-stable Test-ID and Test-OOD scenario groups, evaluated separately and then in a predeclared equal-weight group summary. Stable scenarios are used for H3 and are not mixed into the primary change-adaptation estimate.

## Secondary metrics

Key secondary metrics are invalid memory reuse rate, total cost, recovery time, applicable memory precision at configured top-k, dormant memory reactivation accuracy, input/output token count, latency, JSON parse failure, and fallback rate.

Descriptive operational metrics are stockout rate, fill rate, holding cost, lost sales, average inventory, detection delay, regret at 7 and 14 days, memory churn, and memory store size. Secondary or descriptive results cannot replace the primary endpoint after outcomes are observed.

Recovery is the first post-shift day after which the rolling seven-day regret rate stays within 10% of the paired Oracle rate for seven consecutive completed days. If recovery does not occur, it is right-censored at the episode end and reported as not recovered.

## Scenario splits and no-test-tuning

- **Development:** existing implementation scenarios and seeds used for debugging.
- **Validation:** new in-domain parameter values used to choose detector, thresholds, dormancy patience, retrieval weights, and formal seed count.
- **Test-ID:** held-out configurations from the declared in-domain ranges and held-out seeds.
- **Test-OOD:** held-out magnitudes, timings, periods, or combined structures outside Validation and Test-ID values.

Test-ID includes a held-out stable configuration for H3. Test-OOD includes a held-out periodic-demand configuration for H4. Their definitions and hashes may be validated before freeze, but their environments must not be executed before the replacement freeze.

Test-ID and Test-OOD are not used for tuning. Scenario identity is the full generating configuration rather than the seed alone. Split validation rejects duplicate scenario IDs, identical configuration hashes across prohibited splits, and prohibited seed overlap. Phase 4 may create and hash test manifests but must not create or inspect test outcome files.

## Models and method matrix

Core model A is `deepseek-ai/DeepSeek-V3.2`. Core model B is `MiniMaxAI/MiniMax-M2.5`, which passed the unchanged qualification gate. `Pro/zai-org/GLM-5.1` remains supplementary. Commercial models may be reported as optional upper bounds but cannot replace either open core model.

The six main memory methods are NoMemory, FullHistory, Summary, VectorMemory, TimeDecay, and ShiftMem. They use the same model, public observation, prompt objective, structured action schema, top-k budget, retry/fallback policy, and paired scenario/seed trajectory. Classical policies and Oracle are contextual baselines, not members of the six-method model comparison.

## Seeds, pairing, and failed runs

Every method comparison is paired by scenario, model, and master seed. Demand and supply random streams use the repository's deterministic derivation and remain independent of policy/provider calls. Formal configurations use 52 seeds per cell, the conservative Pilot planning value for target power 0.80. The complete matrix has 9 scenarios, 52 seeds, 2 core models, 6 methods, and 30 scored model decisions per cell: 5,616 cells and 168,480 planned decisions.

Failed provider runs are retained. A transport or parsing failure follows the declared single retry and safe fallback. Its operational outcome remains in cost metrics, and the failure contributes to reliability metrics. Runs are excluded only for a reproducible infrastructure failure that prevents the environment from completing and affects all compared methods for the paired unit; exclusions are listed with reason and rerun status.

## Statistical analysis

For each method contrast, calculate paired differences on matching scenario/model/seed units. Report mean, sample standard deviation, 95% confidence interval, paired effect size, and raw sample count.

Use a paired t-test when the paired-difference normality diagnostic does not reject at 0.05 and no severe outlier pattern is present; otherwise use the Wilcoxon signed-rank test. Tests are two-sided with alpha 0.05. Apply Holm correction within each declared family of secondary contrasts. Report adjusted and unadjusted p-values and do not equate non-significance with equivalence.

H3 stable non-degradation is descriptive until a smallest acceptable cost margin is fixed from Validation before formal tests. Pilot reports variance and runtime but no confirmatory p-values.

## Exclusion and stopping rules

No failed run, fallback action, high-cost episode, or unfavorable model/method result is silently deleted. Duplicate records caused by an interrupted resumable job are de-duplicated by the complete configuration key and recorded. Predeclared diagnostics may identify causes but cannot change the endpoint.

Live execution stops before additional calls when the estimated remaining cost exceeds the recorded Pilot budget, provider quota prevents paired completion, credentials become invalid, or the repository/configuration hash differs from the frozen package. Partial batches remain archived and are marked incomplete.

The v1.1 Validation live dry-run used a user-approved CNY 30 cap and cost CNY 3.2184. Its 366 provider attempts included six failed attempts that the initial journal counted only at cell level. The corrected journal now persists both successful and failed attempts. Extrapolation gives 171,288 expected formal attempts, 289,375,164 input tokens, 74,781,252 output tokens, and estimated cost CNY 1,506.22. The proposed 20% safety cap is CNY 1,810 and remains unapproved.

The following are valid negative findings: ShiftMem adds stable-environment cost, classical policies outperform all LLM agents, detector false alarms cause churn, gains occur for only one model, or inference cost dominates the benefit.

## Reproducibility and freeze

Every aggregate records the Git commit, dirty state, Python and dependency versions, provider and model ID, device class, scenario ID, master seed, configuration copy, and configuration hash. Raw records are immutable inputs to aggregation; tables and figures are generated by scripts.

Runtime detectors consume the canonical public daily fields `demand`, `lost_sales`, and `quoted_lead_time`; Validation selection uses `quoted_lead_time` for supply-only shifts. Every live provider attempt is identified by freeze, commit, configuration hash, cell, day, and attempt number. Completed responses and sanitized failures are appended and fsynced before execution continues, allowing deterministic replay without a second call.

The Phase 4 freeze requires a clean repository, passing tests, a complete protocol, passing split validation, selected Validation settings, and two qualified open core models. Canonical formal configurations and split manifests are copied into a versioned freeze directory. A sorted `SHA-256` manifest covers every frozen file and is verified before formal execution.
