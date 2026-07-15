# Protocol v2 Qualification Conformance Repair Design

Date: 2026-07-15

Status: approved design, pending implementation plan

## Purpose

Repair the protocol-v2 strategy-review and model-qualification paths so they
implement the already documented `2.0-draft` contract. This is a Development/
Validation instrumentation correction, not a relaxation of the qualification
gate and not a change to any paper endpoint.

The repair must preserve the current strict requirement of four monotonicity
passes from four checks. It must not make a provider call, touch Test-ID or
Test-OOD outcomes, alter the v1 freeze, or delete or overwrite unfavorable
qualification evidence.

## Confirmed problems

### Wrong prompt in the strategy qualification runner

`execute_strategy_qualification` currently uses the generic default provider
factory. That factory constructs a `CompatibleAPIProvider` with the archived v1
daily-order prompt and user-message builder. The v2 qualification path therefore
does not reliably send the strategy-review prompt.

The latest artifact contains 24 result rows while the live execution reportedly
made about 48 calls. Together with the one-retry loop, this is consistent with
initial v1-schema outputs being corrected on a second call. Successful retries
discard the earlier parse error, so the summary's zero parse failures does not
mean zero failed attempts.

### Missing protocol inputs

The protocol states that the strategy reviewer receives public history, current
strategy parameters, trigger evidence, and memory context. The runtime agent
accepts a current strategy and trigger reason, but only serializes observation,
memory, and correction into the provider request. Qualification requests have
the same omission.

### Invalid lost-sales fixtures

The current pressured history combines positive lost sales with positive ending
inventory and arrivals equal to full demand. It also leaves `last_sales`
inconsistent with the final history row. These records cannot be emitted by the
project's lost-sales environment and may confuse a model independently of the
behavior the gate intends to measure.

### Incomplete attempt and provenance evidence

The qualification result stores only the final accepted proposal or final
failure. It does not preserve every raw attempt, correction, parse error, prompt
identity, configuration identity, code revision, or an immutable run identity.
The current output writer can replace an earlier run.

## Invariants

- Keep `monotonicity_checks == 4` and `monotonicity_passes == 4` as the
  qualification requirement.
- Keep the two demand checks, two lost-sales checks, dormant-memory rejection,
  invalid-citation rejection, schema validation, and one correction retry.
- Keep RQ1-RQ5, H1-H5, `post_shift_cumulative_regret_30`, paired seeds, memory
  methods, scenario manifests, and Conditional-not-Causal framing unchanged.
- Keep v1/v1.1 code and `configs/frozen/phase4-20260713-b99c0d3e4d27/`
  unchanged.
- Do not access Test-ID or Test-OOD outcomes.
- Do not call a live provider during implementation or verification.
- Preserve the 2026-07-15 qualification artifacts byte-for-byte. Document them
  as `inconclusive_harness_invalid`; do not reinterpret them as passes.

## Request architecture

Add a v2-specific `StrategyProviderRequest` beside the existing
`ProviderRequest`. It extends the common observation, memory, and correction
fields with:

- `current_strategy`: the validated strategy active before the review;
- `trigger_reason`: `periodic`, `event`, or `coalesced`;
- `trigger_evidence`: public detector/scheduler evidence, or an explicit empty
  object for a periodic review without detector evidence.

The archived v1 request remains unchanged. The strategy prompt builder accepts
only `StrategyProviderRequest`, making an incomplete v2 request fail before a
provider call.

`StrategyReviewAgent.review` receives trigger evidence in addition to its
existing inputs and builds this request on every attempt. `run_v2_episode`
passes the scheduler decision's public evidence through unchanged. Qualification
cases construct the same request type, so qualification and runtime exercise the
same model-facing contract.

## Prompt routing

Create a dedicated strategy provider factory for the qualification runner. It
must inject both `STRATEGY_REVIEW_SYSTEM_PROMPT` and
`build_strategy_review_user_message`. The v1 order qualification continues to
use the existing default factory.

An offline regression test must instantiate each factory and assert the exact
system prompt and message builder identities. No network transport is invoked.

The strategy system prompt will describe the controller's protection target
formula at the level necessary to reason about joint parameter effects:

`forecast * (quoted_lead_time + lead_time_buffer + 1) +
safety_stock_multiplier * demand_std * sqrt(protection_periods)`.

This does not reveal hidden information or change the controller; it makes the
already frozen mapping visible to the reviewer that is judged on its combined
effect.

## Qualification fixtures

Keep the existing six case IDs and two repetitions. Replace handwritten
inventory rows with a small deterministic fixture builder that enforces for
every row:

- `sales + lost_sales == demand`;
- `ending_inventory >= 0`;
- positive lost sales imply `ending_inventory == 0`;
- `total_cost` agrees with the public cost fields used by the case;
- observation `last_demand`, `last_sales`, and `inventory` agree with the final
  history row;
- history is chronological and contains only public fields exposed by
  `InventoryEnv`.

The calm and pressured lost-sales cases keep the same realized-demand sequence.
Only feasible inventory availability changes, producing zero versus positive
lost sales. The controller still sees the same demand series for the pair, so
the induced-target comparison continues to isolate the reviewer's protection
response.

The demand-low and demand-high cases retain proportional deterministic demand
variation so the controller's observed standard deviation scales with demand.

## Attempt accounting

Each `StrategyQualificationResult` stores an ordered list of attempt records.
Every record contains:

- attempt number;
- correction sent on that attempt;
- raw model output;
- input and output tokens;
- latency;
- parse, schema, or citation error, if any.

Summary metrics distinguish:

- `attempt_count`: every provider invocation;
- `corrected_case_count`: cases accepted after a failed earlier attempt;
- `attempt_parse_failure_count`: failed individual attempts;
- `unresolved_parse_failure_count`: cases with no accepted proposal after both
  attempts;
- `fallback_count`: cases that exhausted the retry and retained no proposal.

The existing one-retry behavior is unchanged. A corrected case is not silently
reported as having had no parse failure. Qualification continues to require no
unresolved failure or fallback; attempt-level failures remain visible for
stability reporting.

## Immutable run evidence

Every live or offline qualification run receives a caller-supplied or generated
run ID. Its summary records:

- run ID and UTC start time;
- schema name;
- model/profile identifiers;
- configuration SHA-256;
- system-prompt SHA-256;
- user-message-builder identifier;
- Git revision and dirty-worktree flag;
- result, attempt, token, and latency totals.

The CLI refuses to write to an existing raw or summary path unless an explicit
`--overwrite` flag is supplied. Normal documented commands use run-specific
paths and never use that flag. Existing artifacts are not moved or rewritten.

Add a short audit note that identifies the current 2026-07-15 files by path and
SHA-256 and labels their inference status `inconclusive_harness_invalid`, with
the concrete reasons from this design.

## Error handling

- An incomplete strategy request fails locally before provider invocation.
- A wrong strategy prompt factory fails an offline identity test.
- A fixture violating conservation fails construction or validation.
- A parse or citation error is retained in the attempt log before retrying.
- An existing output path causes a clear error before the first provider call.
- Missing Git metadata is recorded as unavailable rather than aborting a run.
- Budget-stop exceptions retain their existing hard-stop behavior.

## Test strategy

Implementation follows red-green-refactor cycles. Required regression coverage:

1. Strategy requests serialize current strategy, trigger reason, and trigger
   evidence; v1 requests remain byte-for-byte compatible.
2. The runtime agent forwards all protocol inputs on first and correction
   attempts.
3. The episode runner forwards scheduler evidence.
4. Strategy qualification uses the v2 prompt factory; order qualification uses
   the v1 factory.
5. Lost-sales fixtures satisfy conservation and final-observation consistency.
6. A first-attempt schema error followed by success produces two preserved
   attempts, one attempt parse failure, one corrected case, and zero unresolved
   failures.
7. Existing output paths are rejected before a provider call.
8. Monotonicity remains a strict four-of-four gate.
9. The full network-free suite, protocol validators, compileall, and
   `git diff --check` pass.
10. The v1 freeze verification remains clean and no Test outcome artifact is
    created or read.

## Direction review

The project purpose is to test whether lifecycle-aware experience memory
improves adaptation and reduces invalid reuse under regime shift. The v2
hierarchical reviewer remains aligned with that purpose because it separates
memory-conditioned strategy revision from deterministic daily execution and
reduces provider-call volume.

The current risk of drift is methodological effort concentrating on repeatedly
tuning model qualification rather than evaluating memory hypotheses. The repair
therefore adopts this stop rule:

1. repair and verify the protocol-conformant harness without provider calls;
2. freeze the qualification prompt, fixtures, gate, and provenance format;
3. perform at most one newly budget-approved qualification run per candidate
   model under that frozen harness;
4. accept the recorded outcome without changing the gate;
5. if fewer than two core models qualify, report the limitation and make a
   separately documented model-selection or scope decision rather than revising
   the observed gate again.

No formal Test execution is authorized by this repair. Protocol finalization,
budget approval, successful qualification, and a clean v2 freeze remain separate
gates.

## Deliverables

- Protocol-conformant v2 provider request and runtime propagation.
- Schema-specific qualification prompt routing.
- Feasible deterministic qualification fixtures.
- Attempt-level qualification evidence and truthful summary metrics.
- Non-overwriting, provenance-rich run outputs.
- Audit note for the existing invalid/inconclusive qualification artifacts.
- Direction-alignment assessment and qualification stop rule in project docs.
- Complete offline regression and verification evidence.
