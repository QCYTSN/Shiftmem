# Implementation Log

Implementation decisions and deviations from the specification will be recorded here as development proceeds.

## 2026-07-13 — Phase 1 environment foundation

- Selected Python 3.12+, NumPy, PyYAML, Matplotlib, and pytest with a lightweight Gymnasium-shaped interface.
- Fixed the default environment to lost sales with a 150-day horizon and one `standard` supplier.
- Fixed daily event order to arrivals, regime lookup, demand sampling, sales/lost sales, new-order scheduling, cost calculation, then day advancement.
- Recognize purchase cost on the order day; recognize holding and stockout costs after demand is realized.
- Restricted ordinary observations to day, on-hand inventory, pipeline inventory, last demand, and last sales.
- Kept true demand mean, lead time, and fill rate in an explicit Oracle-only context.
- Added two protection-period standard deviations of safety stock to the simplified Oracle after its mean-only base-stock rule failed the required random-policy sanity comparison.
- Used synthetic scenarios only; no external data or model API is required in Phase 1.

## 2026-07-13 — Phase 1 diagnostic corrections

- Deferred stochastic fill-rate sampling until the order arrival day. Pipeline inventory now reports the nominal outstanding order quantity rather than revealing the future realized fill.
- Extended Oracle-only context with demand-model type and dispersion. Oracle safety stock now uses the configured Poisson or negative-binomial variance.
- Derived independent reproducible environment and policy RNG seeds from the CLI master seed.
- Added regime-shift markers to generated diagnostic figures.
- Retained fixed-order policy as an intentionally weak sanity baseline; multi-seed aggregation remains a separate evaluation task.

## 2026-07-13 — Classical development pilot

- Added separate demand and supply RNG streams inside each environment so policy-dependent supply sampling cannot alter paired demand trajectories.
- Fixed the development pilot at five scenarios, five classical policies, ten paired seeds, and 150-day episodes.
- Added average inventory, stockout-day rate, fill rate, and pre/post-shift 7/14/30-day metrics.
- Stored raw run records as ignored JSONL under `artifacts/raw_runs/` and committed aggregate CSV outputs under `artifacts/aggregated/`.
- Used sample standard deviation and a normal-approximation 95% confidence interval for pilot summaries. Formal analysis may replace the approximation after power and distribution checks.
- Calculated total-cost regret by pairing each policy with Oracle on the same scenario and master seed.
- Classified all current pilot scenarios as development data; validation, Test-ID, and Test-OOD remain unfrozen.

## 2026-07-13 — Phase 2 offline Agent foundation

- Added Pydantic-validated Agent decisions and provider request/response schemas.
- Standardized provider parsing to one initial attempt, one correction retry, then a classical safe fallback.
- Logged raw outputs, token counts, latency, parse failures, supplied memory IDs, final decisions, and fallback use.
- Added NoMemory, bounded FullHistory, deterministic Summary, lexical Vector, and lexical-plus-time-decay memory baselines behind one interface.
- Rejected any decision that cites a memory ID not supplied in its retrieval context.
- Added a deterministic provider and baseline-switching CLI for offline integration only. It deliberately ignores memory content, so these runs must not be interpreted as memory-method comparisons.
- Deferred a real local instruction model and compatible API integration until hardware, model license, and model selection are explicitly decided.

## 2026-07-13 — CPU-only compatible provider

- Detected an Intel Core Ultra 5 125H and 31.5 GB system memory with no Ollama, llama.cpp, or GPU runtime installed.
- Kept deterministic mode as the offline default and added an opt-in OpenAI-compatible chat-completions provider.
- Loaded endpoint, model name, and API key only from the process environment or ignored local `.env`; credentials are represented as secret values and omitted from errors and logs.
- Injected the HTTP transport so all automated tests remain offline and deterministic.
- Added sanitized handling for HTTP status, connection, timeout, malformed envelope, provider exception, JSON parse, and decision validation failures.
- Deferred the first real model smoke test until the user configures a compatible endpoint. No model choice or provider-specific result has been recorded.

## 2026-07-13 — Named remote model profiles

- Added independent Bailian and SiliconFlow profiles over the same OpenAI-compatible transport; only the selected profile's key is required.
- Fixed non-thinking JSON generation defaults at temperature 0, 512 maximum output tokens, and a 60-second timeout.
- Selected `qwen3.5-flash-2026-02-23` as the low-cost pinned Bailian smoke model and `deepseek-ai/DeepSeek-V3.2` as the default SiliconFlow cross-family model.
- Kept `qwen3.7-plus-2026-05-26` and `Pro/zai-org/GLM-5.1` as explicit per-run overrides.
- Kept deterministic mode as the CLI default and did not perform a live request before the user supplied a key and reviewed provider billing and quotas.
- After credentials were supplied, the live model list showed that SiliconFlow no longer offered `Pro/zai-org/GLM-4.7`. The available `zai-org/GLM-4.5-Air` rejected JSON mode, while `Pro/zai-org/GLM-5.1` passed the structured decision smoke test.

## 2026-07-13 - Inventory prompt and model qualification

- Expanded the public Agent observation with scheduled pipeline orders, quoted lead time, public costs, and a chronological 14-day realized-history window without exposing Oracle or future information.
- Added one provider-independent inventory objective and memory-applicability instruction for every compatible API model.
- Added eight fixed behavioral cases, two repetitions, paired monotonicity gates, citation checks, ignored raw JSONL output, and a trackable aggregate result.
- The first live pass exposed output truncation in both Qwen models because unconstrained reasons exhausted the shared 512-token cap. Applied one model-independent correction: `reason` is now one sentence with at most 200 characters, enforced by both prompt and schema, then reran all four candidates from scratch.
- On the corrected run, all four candidates had zero parse failures, zero fallbacks, and passed all six monotonicity comparisons. DeepSeek-V3.2 and GLM-5.1 passed every hard gate. Qwen Flash and Qwen3.5-35B-A3B each cited the explicitly dormant, mismatched memory in both repetitions, so both failed the predeclared applicability gate.
- Selected DeepSeek-V3.2 as the current core candidate and retained GLM-5.1 only as a supplementary candidate. The intended two-model formal design remains unfrozen until a second eligible core model qualifies.

## 2026-07-13 - Phase 3 deterministic ShiftMem core

- Added structured experiences with public applicability predicates, lifecycle status, Beta-Bernoulli evidence, stable Agent conversion, replay-safe storage, and append-only audit events.
- Implemented a resettable two-sided Page-Hinkley detector over realized public signals. A detected variable only places overlapping active experiences into probation; it never invalidates the entire store.
- Implemented explicit probation, active, dormant, and invalid transitions, configurable post-change failure weighting, and deterministic delayed validation after lead time plus a service window.
- Added template-based experience extraction from public observations, actions, and realized service/cost metrics. Hidden demand parameters, future information, shift schedules, regime IDs, and Oracle context are rejected at the extraction boundary.
- Added two-stage retrieval: hard lifecycle/applicability filtering followed by transparent lexical relevance, confidence, recency, utility, and shift-penalty scoring with deterministic ties.
- Integrated `ShiftMemory` through optional structured-Agent hooks without changing the behavior of the five existing memory baselines. Raw audit output remains under ignored experiment-output paths.
- Deferred ADWIN, remote embeddings, persistence, and all detector/retrieval hyperparameter selection to Pilot/design-freeze work. The deterministic provider remains an interface check and cannot support a performance conclusion.

## 2026-07-13 - Phase 1 acceptance and research governance

- Completed the 100-seed Phase 1 acceptance matrix: 2,500 network-free runs across five scenarios and five classical policies, with all declared acceptance gates passing.
- Froze experiment protocol v1.0, established the related-work matrix, and created disjoint Development, Validation, Test-ID, and Test-OOD manifests with automated split validation.
- Preserved the rule that Test-ID and Test-OOD manifests may be created and hashed before freeze, but their outcomes may not be generated or inspected during selection.

## 2026-07-13 - Detector, lifecycle, and Validation selection

- Added ADWIN alongside Page-Hinkley and implemented automatic dormancy/reactivation behavior.
- Selected Page-Hinkley threshold 48, dormancy patience 3, and recency-heavy retrieval using Development/Validation evidence only.
- Recorded that the selected detector produced zero misses but 283 repeated false-positive signals across 80 Validation episodes; this remains a material operational limitation.

## 2026-07-13 - Second core model, Phase 4 Pilot, and v1 freeze

- Qualified `MiniMaxAI/MiniMax-M2.5` as Core B alongside Core A `deepseek-ai/DeepSeek-V3.2`; retained `Pro/zai-org/GLM-5.1` as supplementary and kept both failed Qwen applicability results.
- Completed the bounded Phase 4 Pilot on one Validation demand-jump scenario, two seeds, VectorMemory and ShiftMem, producing eight unique cells without reading Test outcomes.
- Retained one fallback and documented the interrupted-run duplicate-call incident instead of deleting unfavorable or operational evidence.
- Created and verified immutable freeze `phase4-20260713-b99c0d3e4d27` with a sorted SHA-256 manifest.

## 2026-07-14 - Post-freeze readiness audit

- Reverified the v1 freeze and full automated suite before reviewing formal-experiment readiness.
- Found that detector selection evaluates supply change through public `quoted_lead_time`, while the production ShiftMemory outcome path updates detectors only with demand and lost sales. Supply-change Validation evidence therefore does not match the runtime signal path.
- Found no held-out stable scenario for H3 and no held-out periodic recurrence scenario for H4 in the frozen Test manifests.
- Confirmed that formal statistics, machine-readable result schemas, the six-method runner, per-decision idempotent recovery, and budget gates are not yet complete.
- Clarified that the Pilot used fixed-policy warm-up and pre-seeded memories, and that 52 seeds is a provisional planning estimate based on two paired observations per model.
- Classified v1 as a valid immutable audit snapshot but blocked it from formal Test execution. Corrections must use Development/Validation only, be recorded in protocol v1.1, and culminate in a verified replacement freeze before any Test outcome is generated or read.

## 2026-07-14 - Protocol v1.1 implementation and live Validation gate

- Unified runtime and Validation selection on public detector signals `demand`, `lost_sales`, and `quoted_lead_time`; the affected offline selection rerun retained Page-Hinkley threshold 48.
- Added held-out stable Test-ID and periodic Test-OOD definitions without executing either split.
- Implemented recovery/regret endpoints, paired inference, Wilcoxon fallback, Holm correction, a six-method matrix, and freeze-bound dry-run validation.
- Added fsynced per-decision response replay and CNY budgets. A CNY 30 Validation-only live run completed all 12 model/method cells for CNY 3.2184 with zero fallbacks.
- Found that the initial journal omitted six failed provider attempts even though cell logs counted them. Preserved the deviation, then changed the journal to persist and replay sanitized failures and count them against budgets.
- Corrected the formal matrix arithmetic to 5,616 cells and 168,480 planned decisions. The measured projection is CNY 1,506.22; the proposed 20% safety cap is CNY 1,810 and remains subject to explicit approval before replacement freeze.

## 2026-07-14 - Protocol v2 hierarchical strategy-Agent revision

- Retired the v1.1 direct-daily-order formal design before any Test-ID/Test-OOD execution. The v1 freeze remains immutable, and the v1/v1.1 Pilot and Validation evidence remain historical engineering evidence only.
- Corrected a later-discovered scope error in the v1.1 projection: the declared held-out manifests contain eight scenarios, so the retired direct-order matrix would have 4,992 cells and 149,760 planned decisions, not 5,616 and 168,480. This correction does not authorize that matrix.
- Redefined the LLM as a low-frequency strategy-review Agent, eligible every five completed days or after a detector event. Same-day triggers are coalesced, repeated alerts use a frozen cooldown, and the LLM cannot modify its schedule.
- Assigned every daily `order_quantity` calculation to one deterministic controller shared by all LLM memory methods. The model may only propose a small bounded vector containing forecast window, safety-stock multiplier, and lead-time buffer.
- Changed experience attribution from individual LLM orders to strategy revisions and their delayed daily outcomes. Retrieval, citation, proposal validation, active strategy, deterministic order, and delayed evidence must be logged separately.
- Reduced the proposed primary matrix to eight scenarios, ten seeds, two core models, and VectorMemory versus ShiftMem (320 cells). Other memory baselines move to a DeepSeek-only five-seed secondary tier, while H3--H5 use targeted scenarios and ablations.
- Retired the v1.1 CNY 1,506.22/CNY 1,810 budget proposal. A new Development/Validation-only Pilot must measure review frequency and token cost before any v2 formal budget or replacement freeze is approved.
- Kept simulation and remote-API orchestration CPU-capable. GPU rental is optional, separately budgeted local-model appendix work and is not required for remote API experiments.

## 2026-07-14 - Protocol v2 engineering (Tasks 1-4)

- Wrote the v2 implementation plan at `docs/superpowers/plans/2026-07-14-protocol-v2-implementation.md` with a research-invariant guard: RQ1-RQ5, H1-H5, the `post_shift_cumulative_regret_30` endpoint, the six memory methods, the eight held-out scenarios, paired seeds, and no-test-tuning must not change.
- Added `src/shiftmem/control/` with a `DeterministicController` and bounded `StrategyParameters` (forecast_window, safety_stock_multiplier, lead_time_buffer). The controller computes every daily order from public state only; strict mode rejects hidden-truth keys. Bounds/defaults are provisional Development placeholders pending Validation selection.
- Added a `ReviewScheduler` implementing the fixed five-day interval, event triggering, same-day coalescing, and a frozen cooldown that suppresses repeated alerts. Interval and cooldown are constructor config, never model-controlled.
- Added `StrategyProposal` (extra-forbid, no `order_quantity`) and a `StrategyReviewAgent` mirroring the v1 retry/fallback structure: one schema-correction retry, then retain the previous validated strategy. Proposal schema enforces only structural sanity; frozen operational bounds are applied by a separate `StrategyParameters.clamp()` step, so out-of-range proposals are projected and logged as clamped rather than discarded.
- Added a strategy-review prompt that instructs the model to propose parameters and never emit a daily order, plus a memory-agnostic `DeterministicStrategyProvider` for offline integration checks only.
- Added `extractor.extract_strategy_revision` (experience unit is a strategy revision, not a day) and `memory/reuse.py`, which counts invalid reuse only when a memory was supplied, cited, and the proposal was accepted; retrieval-only and cited-but-rejected cases are reported separately for H2. The `DelayedValidator` window scoring is reused unchanged.
- Kept the archived v1 `AgentDecision`/`StructuredAgent` path intact; no v1 test was altered. Full network-free suite grew from 238 to 267 passing. No provider call was made, no Test-ID/Test-OOD scenario was executed, and the v1 freeze was not touched.
- Deferred `shiftmem.py` strategy-revision wiring, the v2 episode loop, v2 metrics/runner, model requalification, and the v2 Pilot to Tasks 5-8.

## 2026-07-14 - Protocol v2 engineering (Tasks 5-9)

- Wired `ShiftMemory.register_strategy_revision` and `process_validations` to extract strategy-revision experiences over the delayed window, then built `control/episode.py` as the full offline v2 loop (scheduler gates reviews, controller orders every day, agent proposes on review days, memory validates revisions). Added a `--protocol v2` branch to `run_agent_episode.py`; deterministic mode stays the CLI default.
- Verified the loop end-to-end offline: a 60-day ShiftMem episode produced 12 reviews, 12 revision experiences, 0 pending validations left, and both periodic and coalesced triggers, confirming detector events coalesce with periodic reviews.
- Added `summarize_strategy_reviews` (scheduled/event/coalesced/suppressed counts, fallback/clamp counts, invalid-proposal rate, parameter churn) and the v2 hierarchical cell plan (`validate_v2_config`, `build_v2_cell_plan`) producing exactly 320 primary cells (VectorMemory vs ShiftMem, 2 models, 10 seeds, 8 scenarios) and 160 DeepSeek-only secondary cells; Test-ID/Test-OOD IDs are rejected. Added `configs/experiments/formal_v2.yaml` with zero budgets and `budget_approved: false`.
- Added `evaluation/strategy_qualification.py`: monotonicity is expressed over the strategy vector (higher demand or lost-sales pressure must not lower protection) with the unchanged dormant-memory applicability gate. The suite runs offline; live requalification of DeepSeek-V3.2 and MiniMax-M2.5 is deferred to budget approval.
- Added the Development/Validation-only Pilot (`scripts/run_v2_pilot.py`, `configs/experiments/v2_pilot.yaml`, `validate_protocol_v2`). The offline Pilot ran 40 episodes with 0 fallbacks and measured 30.8 reviews per 150-day episode (~0.205/day) versus v1's 1.0/day, a roughly five-fold provider-call reduction. Recorded in `docs/v2_pilot_report.md` with the explicit caveat that token cost per review is not yet measured and requires a budget-approved live Pilot.
- Added the exact `forecast_window`/`safety_stock_multiplier`/`lead_time_buffer` identifiers and coalescing/cooldown description to the protocol's strategy-review section so `validate_protocol_v2` passes without weakening the base validator.
- Final verification: full network-free suite 289 passing, compileall OK, both protocol gates pass, `git diff --check` clean. The v1 freeze `phase4-20260713-b99c0d3e4d27` verified byte-for-byte and its directory is untouched. No Test-ID/Test-OOD outcome file exists and no provider call was made.
- Protocol remains `2.0-draft`. Remaining blockers before any Test execution: a budget-approved live Pilot (token cost per review + core-model requalification), protocol finalization to 2.0, and a clean v2 freeze. None may proceed without explicit user budget approval.

## 2026-07-15 - Protocol v2 qualification harness audit and repair

- Audited the two live v2 qualification attempts and classified their inference status as `inconclusive_harness_invalid`; preserved the existing raw and aggregate artifacts and recorded their SHA-256 values in `docs/v2_qualification_audit.md`.
- Confirmed that the standard strategy qualification factory used the archived v1 daily-order prompt, while successful correction retries hid earlier attempt failures. The 24 raw result rows versus approximately 48 reported calls are consistent with one retry per case, but the old schema cannot reconstruct those first attempts.
- Confirmed that runtime/qualification requests omitted current strategy and trigger evidence despite the protocol contract, and that the pressured lost-sales fixture violated inventory-state consistency.
- Kept the strict four-of-four monotonicity gate unchanged. The repair is limited to request conformance, v2 prompt routing, feasible fixtures, attempt-level audit records, provenance metadata, and default overwrite protection.
- Direction review: the hierarchical strategy-review architecture remains aligned with the ShiftMem memory-reuse research goal, but repeated gate tuning would be scope drift. After offline repair verification, the qualification harness freezes and each candidate gets at most one newly budget-approved run; an unfavorable result triggers reporting/model-scope review rather than another gate change.
- No provider call, Test-ID/Test-OOD access, controller change, endpoint change, or v1 freeze modification was authorized by this repair.
- On 2026-07-15 the user approved one frozen-harness live requalification with hard limits of 48 provider calls and CNY 0.50. Added a qualification-specific budget wrapper that stops before the next call, cannot be swallowed by the per-case retry handler, requires explicit approval for live profiles, and records provider-call and estimated-cost usage in the aggregate. No provider call was made while implementing or testing this gate.
- Executed the one authorized frozen-harness requalification as `v2-qual-live-20260715-739bc99`. Both DeepSeek-V3.2 and MiniMax-M2.5 passed the unchanged 4/4 monotonicity gate and all applicability/validity gates. The run produced 24 rows from 24 calls with zero retries, parse failures, fallbacks, invalid citations, or inapplicable citations; estimated spend was CNY 0.2146. No Test-ID/Test-OOD outcome was accessed, and no additional qualification rerun is authorized.
