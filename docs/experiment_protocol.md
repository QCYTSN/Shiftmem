# Experiment Protocol

Protocol version: 2.0

Preparation date: 2026-07-14

Replacement freeze: content-addressed manifest assigned at clean creation

Scope: hierarchical strategy-review ShiftMem experiments in a single-item lost-sales inventory environment

## Status and amendment policy

Protocol v2 replaces the direct-daily-order Agent design before any Test-ID or Test-OOD outcome was generated or read. Version 1.0 remains archived in immutable freeze `phase4-20260713-b99c0d3e4d27`; v1.1 engineering and its Validation-only live dry-run remain historical evidence but were never frozen for held-out execution.

The v2 change is methodological, not a response to Test results. It makes the LLM a low-frequency strategy reviewer and assigns every daily order calculation to a shared deterministic controller. It also retires the v1.1 52-seed, six-method, two-model full factorial plan and its cost projection.

Historical audit record: **Protocol version: 1.1** proposed 168,480 direct daily model decisions under its mistaken nine-scenario count. That proposal was not frozen or executed on Test outcomes. The corrected eight-scenario historical count and cost are preserved in `docs/v1_1_live_validation_report.md`; neither count is a v2 plan.

The bounded live v2 Pilot completed on 2026-07-15 under its separate CNY 6 / 350-attempt authorization. It does not authorize another Pilot. The formal budget was explicitly approved on 2026-07-16 under Amendment 1, but no Test-ID or Test-OOD execution is authorized until the exact approved config is inside a clean verified v2 replacement freeze.

After the v2 freeze, an implementation bug may be corrected only with a failing regression test and rerun of every affected configuration. Changes to the controller formula, parameter bounds, scheduler, cooldown, primary comparison, endpoint, seeds, or budget require a numbered amendment.

### Amendment 1: reduced formal budget and matrix

Approved by the user on 2026-07-16 before any Test outcome access. To keep the
formal API hard cap at CNY 100, the primary tier retains both core models, all
eight held-out scenarios, and the ShiftMem-versus-VectorMemory comparison, but
uses five rather than ten paired seeds. This gives 160 paid primary cells. The
paid secondary four-baseline tier is removed; H2 becomes exploratory and may
use only the already completed network-free rehearsal unless a separate future
budget is approved. The hard limits are 7,000 attempts, 25 million input
tokens, 3.2 million billed output tokens, and CNY 100. The generation cap
remains 512 tokens, while budget reservation independently allows 3,072 billed
output tokens per attempt because the Pilot observed a maximum of 2,352.

This amendment reduces precision and widens confidence intervals relative to
the superseded ten-seed plan. It preserves the primary estimand and cross-model
RQ4 but does not support a confirmatory paid six-method H2 conclusion.

### Amendment 2: balance-bounded continuation after safety stop

On 2026-07-19, before any outcome-based analysis or matrix change, the user
authorized continuation using the reported remaining balance of approximately
CNY 50 and requested a stop near depletion. The first run stopped after 47
Test-ID cells because failed provider attempts retained conservative 3,072-token
reservations and exhausted the 3.2M output-token ledger; official billing was
approximately CNY 26 while successful-call estimation was CNY 27.12.

The 160-cell matrix, models, seeds, controller, endpoints, and analysis remain
unchanged. The continuation freeze binds the immutable 47-cell prefix by hash
and original run identity. A new journal records only remaining calls and caps
successful-call cost at CNY 43, leaving approximately CNY 7 balance reserve.
Separate higher reservation-ledger ceilings preserve failed-call uncertainty
for audit but are not spending authorization. No completed cell is reissued.

### Amendment 3: reservation underestimate reconciliation

The first Amendment 2 continuation stopped after three additional Test-ID
cells when SiliconFlow reported 3,207 billed output tokens for one response,
exceeding the frozen 3,072-token reservation. The response is not reissued: its
open reservation is terminalized as `ReservationUnderestimate` with the known
billed token count. The per-call billed-output reservation increases to 4,096.

Both immutable Test-ID prefixes, totaling 50 cells, are independently bound by
hash and original run identity. The matrix and analysis remain unchanged. The
next journal caps additional successful-call cost at CNY 40, preserving roughly
CNY 7 of the user-reported remaining balance after the latest successful spend.

### Amendment 4: Test-OOD balance continuation

On 2026-07-21, without outcome-based comparison or tuning, the user reported
that the previously recommended CNY 50 top-up had arrived. The Amendment 3
journal had stopped before a prospective successful-call cost of CNY 40.0011,
with CNY 39.9178 successful-call cost, no unresolved reservation, all 80
Test-ID cells complete, and 23 of 80 Test-OOD cells complete. The user had
reported CNY 9.4 remaining before the top-up.

The 160-cell matrix, models, methods, scenarios, seeds, controller, endpoint,
and analysis remain unchanged. The continuation binds all immutable Test-ID
prefixes (47, 3, and 30 cells) and the 23-cell Test-OOD prefix by SHA-256 and
original run identity. At execution, only prior sources matching the requested
manifest split are required. The new journal caps additional successful-call
cost at CNY 50, preserving approximately CNY 9.4 if the full cap is consumed.
Conservative failed-attempt ledger ceilings remain audit bounds rather than
spending authority. No completed cell is reissued.

## Research questions and hypotheses

- **RQ1:** Does ShiftMem reduce cumulative excess cost after a regime change and shorten recovery?
- **RQ2:** Does ShiftMem reuse fewer invalid strategy experiences than FullHistory, Summary, VectorMemory, and TimeDecay?
- **RQ3:** Are effects consistent across abrupt, gradual, periodic, supply, and combined changes?
- **RQ4:** Do effects transfer across two open model families?
- **RQ5:** Are the gains auditable at acceptable review, token, latency, failure, and memory-size cost?

The hypotheses remain:

- **H1:** ShiftMem has lower post-shift cumulative regret than VectorMemory.
- **H2 (exploratory under Amendment 1):** ShiftMem has lower invalid strategy-experience reuse rate than other memory baselines.
- **H3:** ShiftMem does not materially degrade stable-environment performance.
- **H4:** Dormancy/reactivation is particularly useful under periodic recurrence.
- **H5:** Statistical detectors are more stable and less costly than LLM-only change judgment.

## Decision architecture

### Daily execution

The environment advances every day. A deterministic order-up-to controller receives public realized history, public quoted lead time, current inventory position, and the current validated strategy parameters. It emits the non-negative integer `order_quantity` used by the environment.

The controller formula, initialization, supplier, parameter bounds, and integer rounding rule are identical across all LLM memory methods. Runtime detection and control use the canonical public fields `demand`, `lost_sales`, and `quoted_lead_time`. The controller never calls a provider and never receives hidden demand parameters, the regime ID, the shift schedule, future demand, realized future fill, or Oracle context.

### Strategy review

The LLM is eligible to run when either condition is true:

1. five completed environment days have elapsed since the periodic schedule origin; or
2. a configured detector raises a related demand or supply change signal outside the frozen cooldown.

Periodic and event triggers on the same day are coalesced into one review. Repeated alerts during cooldown are logged but do not cause a call. Review interval and cooldown are not model-controlled.

The LLM receives public history, current strategy parameters, trigger evidence, and memory context. It proposes only the following candidate strategy fields (the serialized parameter identifiers are `forecast_window`, `safety_stock_multiplier`, and `lead_time_buffer`):

- demand forecast window (`forecast_window`);
- safety-stock multiplier (`safety_stock_multiplier`);
- lead-time buffer (`lead_time_buffer`).

A shared deterministic controller consumes this validated strategy vector to compute every daily order. Same-day periodic and event triggers are coalesced into one review, and repeated detector alerts inside the frozen cooldown are suppressed. The review interval, cooldown, controller formula, and daily order are never model-controlled.

It also returns cited memory IDs, confidence, and one short reason. Exact parameter bounds, defaults, maximum single-review changes, and cooldown are selected using Development/Validation only and become required freeze fields. The LLM cannot emit the daily order, change the controller formula, change the supplier, or change its own review schedule.

Invalid output receives one schema-correction retry. If the retry fails, the previous validated strategy remains active. The environment continues, and all attempts and fallback retention are logged.

### Experience and memory

A strategy experience records the public context, trigger, previous and proposed parameters, cited memories, and later realized outcome evidence. Delayed validation waits for a complete frozen observation window and deterministically emits support, failure, or inconclusive.

All memory methods receive this same delayed strategy-revision experience
unit. Non-lifecycle baselines append the completed public experience after the
same lead-time plus validation window; ShiftMem additionally applies its
declared confidence and lifecycle transitions.

An invalid experience is counted as reused only if it was supplied to the reviewer, cited in a valid proposal, and the proposal was accepted by the schema/bounds validator. Retrieval without citation and citation in a rejected proposal are reported separately.

Change signals place only related experiences into probation. Confidence and lifecycle states remain deterministic and auditable; an LLM cannot freely assign memory validity. Dormant experience may re-enter probation when a matching context recurs.

### Candidate runtime profile before the replacement freeze

The runtime configuration must be explicit; production runners may not silently
instantiate library defaults. The current Development/Validation candidate is:

- review interval 5 days and cooldown 3 days;
- strategy defaults: forecast window 14, safety-stock multiplier 1.2, and
  lead-time buffer 1;
- absolute strategy bounds: forecast window 1--60, safety-stock multiplier
  0--5, and lead-time buffer 0--14;
- Page-Hinkley minimum samples 10, delta 0.1, and threshold 48;
- delayed-validation service window 3 and dormancy patience 3;
- recency-heavy retrieval weights: semantic 0.75, confidence 0.5, recency 1.0,
  utility 0.25, probation penalty 0.25, changed-variable penalty 0.5, and
  recency half-life 30.

The detector, dormancy, and retrieval values transfer the prior
Development/Validation selection because the public detector signal path is
unchanged. The transfer is an explicit pre-Test design assumption; it is not a
claim that the v1 direct-order outcomes validate v2 strategy experiences. The
2026-07-15 live v2 Pilot used old library defaults and therefore remains valid
only for its recorded cost/reliability envelope, not final ShiftMem performance.

The maximum permitted single-review changes are forecast window 7,
safety-stock multiplier 1.0, and lead-time buffer 1. These values equal the
largest respective changes observed across the 240 valid live-Pilot reviews
(7, 1.0, and 1), so deterministic enforcement would not alter any recorded
Pilot active strategy or require a post-hoc rerun. Future proposals beyond a
cap are projected to the cap and logged as clamped. This selection uses
Validation evidence only and was made before Test access.

## Primary estimand and endpoint

The primary comparison remains **ShiftMem versus VectorMemory**. The estimand is the mean paired method difference, ShiftMem minus VectorMemory, for post-shift cumulative regret relative to Oracle over the first 30 completed post-shift days. The serialized endpoint is `post_shift_cumulative_regret_30`; lower values favor ShiftMem.

The confirmatory change-adaptation population contains the declared non-stable Test-ID and Test-OOD scenario groups. Groups are evaluated separately and then summarized with equal group weight. Stable scenarios are reserved for H3 and are not mixed into the primary adaptation estimate.

Although the LLM acts only on review days, cost, regret, service, inventory, and recovery are calculated from every completed environment day.

## Secondary metrics

Key secondary metrics are invalid strategy-experience reuse rate, total cost, recovery time, applicable memory precision at configured top-k, dormant reactivation accuracy, input/output token count, latency, JSON failure, retained-strategy fallback rate, and memory-store size.

Additional v2 operational metrics are:

- scheduled, event-triggered, coalesced, and cooldown-suppressed review counts;
- detector delay and false-alert count;
- parameter change magnitude and strategy churn;
- rejected or clamped proposal count;
- days between successful strategy revisions;
- provider cost per successful revision.

Descriptive inventory metrics remain stockout rate, fill rate, holding cost, lost sales, average inventory, regret at 7 and 14 days, and memory churn. Secondary results cannot replace the primary endpoint after outcomes are observed.

Recovery is the first post-shift day after which the rolling seven-day regret rate stays within 10% of the paired Oracle rate for seven consecutive completed days. If recovery does not occur, it is right-censored at the episode end and reported as not recovered.

## Scenario splits and no-test-tuning

- **Development:** existing implementation scenarios and seeds used for debugging and controller development.
- **Validation:** disjoint in-domain parameters used to select detector settings, retrieval weights, strategy bounds, cooldown, delayed-validation window, and the final v2 budget.
- **Test-ID:** four held-out configurations: stable, demand jump, gradual demand, and supply delay.
- **Test-OOD:** four held-out configurations: periodic recurrence, Poisson demand jump, false alarm, and early combined shift.

The formal held-out design therefore contains eight scenarios, not the nine mistakenly reported in the v1.1 cost extrapolation. Scenario identity is the complete generating configuration rather than the seed alone. Split validation rejects prohibited seed overlap and configuration collisions.

Test manifests and hashes may be validated before freeze. Their environments and outcomes may not be generated, opened, summarized, or used for tuning before the v2 freeze.

## Models and method matrix

Core model A remains `deepseek-ai/DeepSeek-V3.2`; Core model B remains `MiniMaxAI/MiniMax-M2.5`. Both must pass a new bounded qualification suite for the v2 strategy schema before the Pilot. `Pro/zai-org/GLM-5.1` remains supplementary and is not required for a core conclusion.

### Primary tier

- eight held-out scenarios;
- five paired seeds per scenario;
- two core models;
- VectorMemory and ShiftMem;
- 160 model-method-scenario-seed cells.

The five-seed Amendment 1 design is a budget-bounded undergraduate-study choice. Results emphasize paired effects and confidence intervals, explicitly report low precision, and must not claim the power associated with either the superseded ten-seed plan or the retired 52-seed planning value.

### Secondary memory tier

NoMemory, FullHistory, Summary, and TimeDecay remain implemented and were exercised in the 48-cell network-free Development/Validation rehearsal. Amendment 1 removes their paid held-out tier. They provide engineering context only and cannot support a confirmatory H2 claim without a separately approved future budget and numbered amendment.

### Targeted ablations and non-LLM context

- H3 uses stable held-out evidence.
- H4 compares full ShiftMem with a no-dormancy/reactivation variant on periodic recurrence.
- H5 compares the statistical trigger with a predeclared LLM-only change-judgment variant on change scenarios.
- A fixed-parameter shared controller, a deterministic rule-adaptation controller, classical policies, and Oracle run without provider calls.

Any third-model, multi-item, additional seed, or broad ablation experiment is optional appendix work and requires its own budget before execution.

## Seeds, pairing, and failed runs

Comparisons are paired by scenario and master seed and, where applicable, model. Demand and supply random streams use deterministic derivation independent of policy and provider calls.

The supply stream is derived from the master supply seed and calendar order
day, rather than advanced by the number of orders a policy happened to place.
Policies placing different earlier orders therefore receive the same fill
shock for an order placed on the same day. This pre-freeze correction does not
rewrite the historical live Pilot as final paired business evidence.

Provider and parse failures are retained. After the declared retry, the previous valid strategy remains active. Its daily outcomes stay in business metrics, and the failure contributes to reliability metrics. A run is excluded only for a reproducible infrastructure failure that prevents the environment from completing and affects all compared methods for the paired unit; exclusions retain reason and rerun status.

Logs distinguish detector signal, scheduler decision, retrieved memory, cited memory, proposal, validation/clamping, active strategy, deterministic order, and delayed outcome. This separation is required to attribute failures to detection, memory, strategy review, or execution.

Every paid provider attempt uses a two-phase append-only journal bound to the
run ID, replacement-freeze ID, clean git commit, and exact formal-config hash.
Before the network call, the runner conservatively reserves one call, a UTF-8
byte upper bound plus a fixed 1,024-token provider-template margin for input,
the frozen provider completion cap, and their maximum token-priced cost, then
fsyncs that reservation. A terminal response or
failure replaces the reservation in budget totals. An unresolved reservation
after interruption is never retried automatically; execution stops for manual
provider-side reconciliation. Replayed terminal attempts never spend budget or
issue another request.

## Statistical analysis

For each declared contrast, calculate paired differences on matching scenario/model/seed units. Report mean, sample standard deviation, 95% confidence interval, paired effect size, and raw sample count.

Use a paired t-test when the paired-difference normality diagnostic does not reject at 0.05 and no severe outlier pattern is present; otherwise use the Wilcoxon signed-rank test. Tests are two-sided with alpha 0.05. Apply Holm correction within each declared secondary contrast family; Amendment 1 declares no paid secondary method-contrast family. Report adjusted and unadjusted p-values and do not equate non-significance with equivalence.

H3 remains descriptive until Validation fixes a smallest acceptable cost margin before the v2 freeze. The selected margin and its rationale become frozen protocol fields; held-out stable outcomes cannot influence it.

The v2 Pilot reports variance, review counts, runtime, token use, failures, parameter behavior, and cost but no confirmatory held-out p-values.

## Exclusion and stopping rules

The v1.1 live Validation dry-run cost CNY 3.2184 and its projected full-matrix cost are historical direct-order evidence only. The reported v1.1 matrix also contained an arithmetic scope error: the declared Test manifests contain eight, not nine, scenarios. Neither the CNY 1,506.22 estimate nor the CNY 1,810 cap is proposed for v2.

The completed Development/Validation Pilot measured scheduled and event review frequency, attempts, input/output tokens, latency, and provider cost. Amendment 1 uses that evidence to set the explicitly approved CNY 100 ceiling and reduced 160-cell matrix. Formal execution remains blocked until these exact fields are copied into and verified by the v2 replacement freeze.

The 2026-07-15 strategy qualification evidence is classified as `inconclusive_harness_invalid` because the runner used the archived daily-order prompt, omitted current-strategy and trigger inputs, did not preserve corrected attempts, and used inconsistent lost-sales fixtures. The raw and aggregate files remain immutable engineering evidence and cannot qualify or disqualify a model. The repaired qualification keeps the predeclared strict condition `monotonicity_checks == 4` and `monotonicity_passes == 4`.

After the repaired prompt, fixtures, gate, and provenance format pass offline verification, they are frozen before any further provider call. Each candidate model may receive at most one newly budget-approved qualification run under that harness. The recorded outcome is accepted without another gate revision. If fewer than two core models qualify, the limitation is reported and any model-selection or scope decision is issued separately rather than changing the observed gate.

Simulation, detection, memory, aggregation, and remote-API orchestration are CPU-capable. A rented GPU is optional and may only be charged to a separately configured local-model experiment. At the user-provided CNY 3/hour rate, records include billed GPU hours, CNY cost, setup time, inference time, and idle time. API and local-inference charges are never counted twice for the same cell.

Live execution stops before another external call when any frozen call/token/cost/GPU-hour cap would be exceeded, provider quota prevents paired completion, credentials fail, or the repository/configuration hash differs from the v2 freeze. Partial batches remain archived and incomplete.

## Reproducibility and freeze requirements

Every aggregate records Git commit and dirty state, Python and dependency versions, provider/model ID, device class, scenario ID, master seed, controller configuration, scheduler configuration, strategy bounds, memory configuration, and configuration hash. Raw records are immutable inputs to scripted aggregation and figures.

Every provider attempt is identified by freeze, commit, configuration hash, cell, review day, trigger, and attempt number. Successes and sanitized failures are appended and fsynced before execution continues so recovery cannot repeat a billed call.

A v2 freeze requires:

- a clean repository and passing network-free tests;
- complete v2 implementation and protocol validation;
- passing split validation without held-out execution;
- two core models qualified on the strategy schema;
- Development/Validation selection of controller bounds, cooldown, validation window, detector, and retrieval settings;
- a completed bounded v2 Pilot report;
- explicit API and, if applicable, GPU budgets;
- a sorted SHA-256 manifest covering every frozen file.

Until all conditions pass, the only authorized work is documentation, implementation, testing, and Development/Validation revalidation.
