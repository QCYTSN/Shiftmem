# Research Readiness and Phase 4 Freeze Design

## Goal

Close the gap between ShiftMem's implemented Phase 1-3 engineering core and a defensible frozen formal experiment. The work completes research governance, finishes deferred detector and lifecycle behavior, creates non-overlapping scenario splits, performs bounded validation-only selection, qualifies a second core model, and emits a hashed Phase 4 freeze package.

No formal Test-ID or Test-OOD result is run or inspected in this work.

## Work packages

The approved sequence is implemented as three dependent packages.

1. **Research governance:** freeze the experiment protocol and create a primary-source related-work matrix.
2. **Engineering readiness:** complete the 100-seed Phase 1 acceptance, ADWIN, automatic dormancy/reactivation, and scenario split manifests.
3. **Phase 4 selection and freeze:** select detector/retrieval settings on Validation, qualify the second core model, run the bounded Pilot, and hash the frozen test package.

Each package has its own evidence and may block the next. Formal experiments cannot begin merely because code tests pass.

## Frozen research questions and hypotheses

The five RQs and H1-H5 from `ShiftMem_Implementation_Spec.md` are retained without outcome-dependent rewriting.

The primary estimand is the paired difference between ShiftMem and VectorMemory in post-shift cumulative regret relative to Oracle over the first 30 completed post-shift days. Lower is better. The primary confirmatory scope is non-stable Test-ID and Test-OOD scenario groups; stable scenarios support the H3 non-degradation check.

Primary endpoint:

- `post_shift_cumulative_regret_30`.

Key secondary endpoints:

- invalid memory reuse rate;
- total cost;
- recovery time;
- applicable memory precision at configured top-k;
- dormant reactivation accuracy;
- token use, latency, and parse/fallback rate.

All other existing operational metrics are descriptive. The primary endpoint and comparison are not changed after Test-ID or Test-OOD is run.

## Statistical protocol

- All method comparisons are paired on the same scenario, model, and master seed.
- Report mean, sample standard deviation, 95% confidence interval, and paired effect size.
- Use a paired t-test when paired differences pass the predeclared normality diagnostic; otherwise use Wilcoxon signed-rank.
- Apply Holm correction within each declared family of secondary comparisons.
- Two-sided alpha is 0.05.
- Pilot estimates variance and runtime only; it does not provide confirmatory p-values.
- Failed provider runs remain in reliability metrics and are not silently deleted. The existing safe fallback determines the action.
- Formal seed count is selected from Pilot variance with a minimum of 5 and a target power of 0.80 for the smallest effect of interest declared in the protocol.

## Data and scenario separation

All data remain synthetic; no external dataset is required.

Scenario identity is determined by the full generating configuration, not only the random seed.

- **Development:** existing stable, demand jump, gradual demand, periodic/combined, and supply-delay configurations used during implementation.
- **Validation:** new parameter values inside the intended Test-ID domain; used only for detector, lifecycle, retrieval-weight, and seed-count selection.
- **Test-ID:** held-out parameter combinations from the same declared ranges and held-out seeds.
- **Test-OOD:** change magnitudes, timings, periodicities, or combined structures outside Validation/Test-ID values.

Each split receives a manifest listing scenario IDs, source YAML hashes, parameter ranges, and seed lists. Test manifests may be generated and hashed, but their outcome files must not be produced during Phase 4.

## Phase 1 acceptance

The 100-seed acceptance is a network-free diagnostic, not a new hyperparameter search. Run seeds `0..99` for every classical development scenario and classical policy. Verify:

- no run exception or non-finite metric;
- exactly 150 completed days per run;
- paired demand trajectories remain identical across policies sharing scenario and seed;
- Oracle has lower mean total cost than the random policy in every development scenario;
- every configured shift has a valid marker and a renderable diagnostic figure.

Raw run records remain ignored; a compact trackable acceptance JSON records counts, failures, and gate status.

## ADWIN detector

Implement a deterministic ADWIN detector behind the existing `ChangeDetector` protocol. Because episodes are short, use an exact adaptive window rather than approximate bucket compression: evaluate admissible cut points after minimum subwindow sizes and shrink the oldest portion when the Hoeffding-style mean-difference bound is exceeded.

The detector exposes variable, delta, minimum window, clock, maximum window, and reset. It accepts finite public realized signals at increasing steps and returns the same `ChangeSignal` schema as Page-Hinkley. Tests cover stationary false-alarm behavior, upward/downward shifts, window shrinkage, reset/replay, and invalid input.

The exact-window implementation is intentionally computationally acceptable for 120-180 day episodes and avoids adding a new dependency. It must be described as exact-window ADWIN in reports.

## Automatic dormancy and reactivation

`ShiftMemory` evaluates applicability for every non-invalid experience on each retrieval.

- An active or probation experience becomes dormant after a configurable number of consecutive completed decision steps in which its conditions do not match.
- A dormant experience returns to probation on the first later matching observation.
- Experiences with no applicability predicates are never automatically dormant.
- The absence counter resets after a match.
- All transitions use the lifecycle manager and append audit events.

The patience value is a Validation-selected development hyperparameter. Test outcomes cannot influence it.

## Validation-only selection

Detector and retrieval selection are separate to limit the search.

1. Compare Page-Hinkley and exact-window ADWIN on Validation public signal traces using false positives, detection delay, missed changes, and repeatability. Select the detector/configuration lexicographically: minimize missed changes, then false positives, then mean delay.
2. With the selected detector fixed, compare a small predeclared grid of retrieval weights using the current qualified core model, DeepSeek-V3.2. Select by mean paired primary endpoint, breaking ties with invalid memory reuse rate and then input tokens.
3. Select dormancy patience in the same bounded retrieval grid.

No continuous optimization, post-hoc grid expansion, or Test-ID/Test-OOD inspection is allowed.

## Second core model qualification

Retain DeepSeek-V3.2 as core model A and GLM-5.1 as supplementary. Query the configured Chinese provider accounts for currently available structured-output-capable open models. Predeclare one replacement core candidate before calling the qualification suite.

The candidate receives the existing fixed 8-case, 2-repetition qualification suite with the same prompt, schema, temperature, and hard gates. A failure is recorded; another candidate requires an explicit protocol amendment and a new qualification date. Commercial models remain optional upper bounds and cannot fill the required second open core role.

## Pilot and freeze package

The bounded Phase 4 Pilot uses Development and Validation only. It estimates variance, runtime, token cost, failure rate, and metric computability across the six memory methods and selected core candidates without running the full Cartesian product.

The Pilot report records:

- exact Git commit and dirty-state check;
- Python/dependency versions and device summary;
- provider/model IDs;
- scenario and seed manifests;
- selected detector/lifecycle/retrieval settings and selection evidence;
- variance/runtime/cost estimates;
- metric completeness and observed failures;
- recommended formal seed count;
- explicit statement that no test outcomes were inspected.

The freeze command copies canonical Test-ID/Test-OOD manifests and formal experiment configuration into a freeze directory, computes SHA-256 for every frozen file, and writes a sorted manifest. Freeze fails on a dirty repository, missing second core model, unresolved selection, or incomplete protocol.

## Related-work matrix

The matrix uses primary papers and official project sources only. It covers:

- LLM/agent long-term memory and reflection;
- experience retrieval and skill libraries;
- concept-drift detection, Page-Hinkley, and ADWIN;
- inventory control under nonstationarity;
- LLM or autonomous agents in business/simulation evaluation.

Columns record problem, memory unit, change assumption, retrieval, validation, lifecycle, environment, metrics, limitations, and the precise ShiftMem distinction. Literature claims receive direct links or bibliographic identifiers and avoid unsupported novelty claims.

## Testing and completion gates

- All existing and new offline tests pass.
- The 100-seed classical acceptance passes all declared gates.
- ADWIN and automatic dormancy/reactivation pass deterministic unit and integration tests.
- Split manifests have no scenario ID, configuration hash, or seed overlap where prohibited.
- Selection scripts reject Test-ID/Test-OOD inputs.
- The second model qualification has a trackable aggregate and ignored raw output.
- The Pilot report is generated from logs, not manually edited result tables.
- The freeze manifest is reproducible and verifies successfully.
- API keys and authorization data never enter tracked files or reports.
