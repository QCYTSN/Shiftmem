# Phase 3 ShiftMem Core Design

## Goal

Implement the first complete, deterministic ShiftMem memory loop: extract auditable experiences, detect changes in public realized signals, move only related experiences through an explicit lifecycle, update confidence from delayed outcomes, and retrieve conditionally applicable experiences for the existing structured Agent.

This phase is an offline engineering and method-validation phase. It does not run the formal experiment matrix, tune against test scenarios, use remote embeddings, or ask an LLM to judge memory validity.

## Scope

The implementation includes:

- a structured experience schema and immutable audit events;
- deterministic experience extraction from completed decisions and realized outcomes;
- a Page-Hinkley detector over public realized time series;
- lifecycle transitions among `probation`, `active`, `dormant`, and `invalid`;
- Beta-Bernoulli confidence updates with configurable post-change failure weight;
- delayed deterministic validation after a complete observation window;
- two-stage conditional retrieval with hard eligibility filters and soft ranking;
- a `ShiftMemory` facade compatible with the current Agent memory interface;
- unit and offline integration tests.

ADWIN, remote embedding APIs, database persistence, LLM-based experience scoring, and formal hyperparameter selection are deferred to Pilot and design-freeze work.

## Experience model

`ExperienceRecord` is the canonical stored object. It contains:

- stable `memory_id`, creation step, and human-readable text;
- `variables` affected by the experience;
- public applicability conditions expressed as typed numeric or categorical predicates;
- lifecycle `status`;
- Beta-Bernoulli `alpha` and `beta` evidence counts;
- support/failure counters and last validation step;
- last applicable step and optional dormant reason;
- structured payload for the source decision and realized public evidence;
- append-only audit events describing every state or confidence change.

Confidence is derived as `alpha / (alpha + beta)` and is never freely assigned by an LLM. Records are retained when invalidated; no lifecycle operation permanently deletes audit history.

The existing lightweight `MemoryRecord` remains the Agent-facing representation. `ExperienceRecord` converts to it only after retrieval eligibility and ranking are resolved.

## Extraction

`ExperienceExtractor` consumes a completed decision record plus a realized validation window. It creates one deterministic experience only when the window is complete and contains enough public evidence to describe the relationship between observation, action, and outcome.

The first version uses templates rather than an LLM. It records the action, relevant demand/inventory/pipeline summary, and realized service/cost evidence. Stable IDs are derived from the episode identifier and decision step so replay does not create duplicates.

Extraction never receives Oracle demand parameters, future demand, future fill, hidden regime identifiers, or shift schedules.

## Change detection

`PageHinkleyDetector` implements the shared detector protocol. A detector instance monitors one named public realized signal, such as demand, lost sales, or realized lead time. It returns a structured `ChangeSignal` containing:

- detection step;
- variable name;
- signed direction when identifiable;
- Page-Hinkley statistic;
- configured threshold;
- suspected change start when estimable.

Warm-up samples cannot trigger a signal. Invalid numeric input is rejected. Detector state is deterministic and resettable.

A signal is evidence about one variable, not proof that all memories are invalid. The lifecycle manager only places records whose `variables` overlap the signal into probation.

## Lifecycle and confidence

`LifecycleManager` owns legal transitions:

- new records begin in `probation`;
- repeated support promotes `probation` to `active`;
- repeated failure moves `probation` to `invalid`;
- related change moves `active` to `probation`;
- sustained non-applicability moves `active` or `probation` to `dormant`;
- renewed applicability moves `dormant` to `probation`.

Illegal transitions raise an explicit error. Every accepted transition appends an audit event with step, old/new status, reason, and related variable when applicable.

`ConfidenceUpdater` applies Beta-Bernoulli evidence. Support increments `alpha`; failure increments `beta`. A failure observed after a related change may receive a configurable multiplier greater than or equal to one. Counts and weights must be positive and finite.

Promotion and invalidation use configured evidence-count and confidence thresholds. These defaults are development settings and must be frozen or selected on validation scenarios before formal tests.

## Delayed validation

Inventory decisions cannot be evaluated on the order day. `DelayedValidator` therefore registers a pending validation with a due step derived from quoted lead time plus a configured service observation window.

Once the complete public window is available, it deterministically compares realized outcomes with configured criteria based on lost sales, fill rate, and incremental cost. It emits `support`, `failure`, or `inconclusive` plus the metrics and reason. Inconclusive outcomes do not update Beta evidence.

Requests before the due step remain pending. Missing days, future-dated evidence, and duplicate completion are rejected or reported explicitly rather than guessed.

## Conditional retrieval

Retrieval has two stages.

### Hard eligibility

The retriever excludes:

- `invalid` records;
- `dormant` records unless reactivated first;
- records whose typed applicability predicates do not match the current public observation;
- records with no overlap between requested and recorded variables when a variable filter is supplied.

`probation` records remain eligible but receive a ranking penalty.

### Soft ranking

Eligible records receive a transparent weighted score:

`semantic + confidence + recency + utility - shift_penalty`

The default semantic component is the existing deterministic lexical cosine scorer. A small scorer protocol allows a future embedding implementation without changing lifecycle or retrieval APIs. All component scores and the total score are returned in retrieval audit data; ties resolve deterministically by creation step and memory ID.

Weights are validated, configuration-driven, and not tuned on Test-ID or Test-OOD scenarios.

## Orchestration and compatibility

`ShiftMemory` owns the experience store, detectors, lifecycle manager, confidence updater, validator, and conditional retriever. Its public Agent-compatible operations remain:

- `add(MemoryRecord)` for compatibility and controlled imports;
- `retrieve(query, step, top_k)` returning Agent-facing `MemoryRecord` values.

Additional explicit methods handle completed decisions, public observations, detector updates, pending validations, and audit inspection. The facade does not call a provider and can be exercised entirely offline.

The existing NoMemory, FullHistory, Summary, Vector, and TimeDecay baselines remain unchanged. `make_memory("shiftmem")` constructs the new facade only after its isolated components and integration path pass tests.

## Errors and safety

- Duplicate experience IDs are rejected unless the replayed record is identical.
- Negative steps, future validation evidence, invalid predicate shapes, non-finite values, illegal lifecycle transitions, and non-positive scoring parameters fail explicitly.
- Insufficient detector warm-up and incomplete validation windows return typed non-error states.
- Only public observations and realized history enter extraction, detection, validation, and retrieval.
- No credentials, provider calls, raw API responses, or hidden environment context are involved.

## Testing and acceptance

Implementation follows TDD in dependency order:

1. experience schema, predicate matching, store, and audit events;
2. Page-Hinkley detector behavior, reset, warm-up, and deterministic change response;
3. lifecycle transitions and Beta-Bernoulli confidence updates;
4. delayed validation scheduling and outcome classification;
5. two-stage retrieval, score components, deterministic ties, and scorer replacement;
6. full `ShiftMemory` offline episode integration and existing-baseline regression tests.

Completion requires:

- all new and existing tests passing;
- compilation and diff checks passing;
- deterministic replay producing identical records, signals, transitions, and rankings;
- a related change affecting only overlapping experiences;
- dormant and invalid records absent from ordinary retrieval;
- no hidden-state fields in stored public evidence;
- every confidence and lifecycle update represented in audit history;
- README and implementation log updated with usage, limitations, and deferred Pilot decisions.
