# Protocol v2 Implementation Plan

> **For agentic workers:** Implement this plan task-by-task using test-driven development. Steps use checkbox (`- [ ]`) syntax for tracking. Add a failing test first, confirm the failure, implement, then run the focused test and the full network-free suite before checking a task complete.

**Goal:** Turn the LLM from a direct daily-order agent into a low-frequency bounded strategy reviewer, move every daily order to a shared deterministic controller, and adapt experience/validation semantics to strategy revisions — all using Development/Validation engineering only, culminating in a bounded v2 Pilot report that precedes any budget approval or v2 freeze.

**Architecture:** A `DeterministicController` computes every daily `order_quantity` from public history, quoted lead time, inventory position, and the current validated strategy vector. A `ReviewScheduler` decides when the LLM may run (every five completed days or on a detector event, same-day triggers coalesced, repeated alerts suppressed by a frozen cooldown). The strategy-review Agent proposes only a small bounded vector (`forecast_window`, `safety_stock_multiplier`, `lead_time_buffer`) plus cited memories, confidence, and one reason — never `order_quantity`. Experience extraction and delayed validation attribute a complete post-review outcome window to a strategy revision, not to a single day. All memory methods share one controller, scheduler, parameter space, and fallback.

**Tech Stack:** Python 3.12, Pydantic 2, NumPy, PyYAML, pytest 8, JSON/JSONL, SHA-256

## Global Constraints

- Never modify `configs/frozen/phase4-20260713-b99c0d3e4d27/`.
- Never generate, open, summarize, or tune on Test-ID or Test-OOD outcomes during v2 preparation.
- Use only Development/Validation runs for controller calibration, detector/retrieval selection, and dry-runs.
- Preserve failed, fallback, partial, and unfavorable results; never delete unfavorable evidence.
- Perform provider calls only after explicit API-budget approval; network-free dry-runs do not imply that approval.
- Do not merge v1/v1.1 Pilot or Validation evidence with v2 outcomes.
- Keep the deterministic offline path the CLI default so no ordinary command spends API credit.
- The v2 freeze is a separate, later, explicitly approved step; this plan stops at a completed Pilot report and blocked Test execution.

## Research invariants (must not change)

RQ1–RQ5, H1–H5, the primary endpoint `post_shift_cumulative_regret_30`, the six memory methods, the eight held-out scenarios, the paired-seed design, the no-test-tuning rule, and the Conditional-not-Causal framing all remain exactly as specified. If any task appears to require changing one of these, stop and request confirmation instead.

---

### Task 1: Deterministic parameterized controller

**Files:**
- Create: `src/shiftmem/control/__init__.py`
- Create: `src/shiftmem/control/controller.py`
- Create: `tests/unit/test_controller.py`

**Interfaces:**
- Consumes: public observation (`inventory`, `pipeline_inventory`, `recent_history`, `quoted_lead_time`, `last_demand`), a validated `StrategyParameters` vector, and nothing hidden.
- Produces: `StrategyParameters` (Pydantic, bounded) and `DeterministicController.order(observation, strategy) -> dict[str, int | str]` returning a non-negative integer `order_quantity` and `supplier_id="standard"` that passes `InventoryEnv._validate_action`.

- [x] Write failing tests: forecast from public `recent_history` only; order-up-to target = forecast × `forecast_window`-derived protection + `safety_stock_multiplier`·σ + `lead_time_buffer`; non-negative integer output; identical output for identical inputs; rejection if observation carries oracle/hidden keys; clamping to declared bounds.
- [x] Confirm the failures.
- [x] Implement `StrategyParameters` with fields `forecast_window`, `safety_stock_multiplier`, `lead_time_buffer` and configurable bounds/defaults (values are Validation decisions; use placeholder defaults marked as provisional). Implement the controller reusing the moving-average/order-up-to pattern already in `classical.py`, with no provider call and no hidden-truth access.
- [x] Run the focused test and the full suite. (8 controller tests; full suite 246 passing)

### Task 2: Review scheduler with trigger coalescing and cooldown

**Files:**
- Create: `src/shiftmem/control/scheduler.py`
- Create: `tests/unit/test_scheduler.py`

**Interfaces:**
- Consumes: current day, periodic interval (fixed 5), a detector event flag/evidence, and a frozen cooldown.
- Produces: `ReviewDecision(should_review: bool, trigger: Literal["periodic","event","coalesced","none"], evidence, last_review_day, coalesced: bool, cooldown_suppressed: bool)`.

- [x] Write failing tests: periodic trigger every five completed days from a fixed origin; event trigger outside cooldown; same-day periodic+event coalesced into one review with `trigger="coalesced"`; repeated event inside cooldown logged as `cooldown_suppressed` with no review; interval and cooldown not mutable by any caller-supplied field.
- [x] Confirm the failures.
- [x] Implement the scheduler as pure deterministic logic. Cooldown and interval are constructor config (Validation-selected, frozen later), never derived from model output.
- [x] Run the focused test and the full suite. (7 scheduler tests; full suite 253 passing)

### Task 3: Strategy-review decision schema and agent

**Files:**
- Modify: `src/shiftmem/agents/base.py` (add strategy schemas; keep `AgentDecision` for archived v1 compatibility but do not use it in v2 paths)
- Create: `src/shiftmem/agents/strategy_agent.py`
- Modify: `src/shiftmem/providers/inventory_prompt.py`
- Create: `tests/unit/test_strategy_agent.py`
- Modify: `tests/unit/test_agent_schemas.py`

**Interfaces:**
- Produces: `StrategyProposal` (`forecast_window`, `safety_stock_multiplier`, `lead_time_buffer`, `used_memory_ids`, `confidence`, `reason`; `extra="forbid"`; no `order_quantity`) and `StrategyReviewLog`.
- `StrategyReviewAgent.review(observation, current_strategy, trigger_reason) -> StrategyParameters`: retrieve memories, one schema-correction retry, then retain the previous validated strategy on failure; reject citations of unsupplied memory IDs; clamp to bounds and record clamping.

- [x] Write failing tests: valid proposal parsed and clamped; `order_quantity` in output rejected; unsupplied-memory citation rejected; one retry then retain-previous-strategy fallback logged; single-review change magnitude clamp; prompt asks for a strategy vector, not a daily order.
- [x] Confirm the failures.
- [x] Implement the agent mirroring `StructuredAgent`'s retry/fallback structure but for strategy proposals; update the prompt text to the strategy-review objective; keep deterministic offline provider support.
- [x] Run the focused test and the full suite. (7 strategy-agent + prompt tests; full suite 261 passing)

**Implementation note:** `StrategyProposal` enforces only structural sanity (`forecast_window>=1`, `safety_stock_multiplier>=0`, `lead_time_buffer>=0`); the frozen operational bounds are applied by `StrategyParameters.clamp()` as a separate deterministic step, so an out-of-range proposal is projected into bounds and logged as `clamped`, not discarded as a fallback. `DeterministicStrategyProvider` ignores memory content (interface check only, not a memory-method result), mirroring the v1 deterministic provider.

### Task 4: Strategy experience extraction and delayed validation

**Files:**
- Modify: `src/shiftmem/memory/extractor.py`
- Modify: `src/shiftmem/memory/validator.py`
- Modify: `src/shiftmem/memory/shiftmem.py`
- Modify: `tests/unit/test_experience_extractor.py`
- Modify: `tests/unit/test_memory_validation.py`
- Modify: `tests/unit/test_shift_memory.py`

**Interfaces:**
- Consumes: a strategy revision (previous vs proposed parameters, trigger, cited memories, review day) and the subsequent frozen-length daily outcome window.
- Produces: a strategy experience record and a deterministic `support`/`failure`/`inconclusive` verdict over the complete post-review window; a reuse counter that increments only when an invalid experience was supplied, cited, and the proposal passed validation.

- [x] Write failing tests: experience unit is a strategy revision, not a day; delayed validation aggregates cost/service/stockout/holding over the frozen window; invalid-reuse counts only supplied+cited+accepted; retrieval-only and cited-but-rejected reported separately; hidden/future/oracle keys rejected at extraction.
- [x] Confirm the failures.
- [x] Implement the revised extraction/validation semantics, keeping Beta-Bernoulli confidence, lifecycle states, and audit events unchanged. (`extractor.extract_strategy_revision` + new `memory/reuse.py`; delayed-validation window scoring in `DelayedValidator` reused unchanged.)
- [x] Run the focused test and the full suite. (6 new tests; full suite 267 passing)

**Scope note:** The `shiftmem.py` `register_strategy_revision` wiring is only exercised by the v2 episode loop, so it is implemented and tested in Task 5 where it runs end-to-end rather than here. This task delivered the pure, measurement-sensitive semantics (revision-unit extraction and the strict H2 reuse rule) in isolation so they can be unit-verified without a full episode.

### Task 5: v2 episode orchestration (controller + scheduler + agent + memory)

**Files:**
- Create: `src/shiftmem/control/episode.py` (or extend the existing episode runner)
- Modify: `scripts/run_agent_episode.py`
- Create: `tests/integration/test_v2_episode.py`

**Interfaces:**
- Produces: a deterministic offline v2 episode where the controller orders every day, the scheduler gates reviews, the agent proposes strategies on review days only, and memory validates revisions after the window. Logs separate detector signal, scheduler decision, retrieved memory, cited memory, proposal, validation/clamping, active strategy, deterministic order, and delayed outcome.

- [x] Write a failing integration test: a network-free episode runs to completion with the deterministic provider; reviews occur only on scheduled/event days; every day has a controller order; logs contain the required separated fields.
- [x] Confirm the failure.
- [x] Implement the loop and CLI wiring; keep deterministic mode the default. Added `shiftmem.register_strategy_revision` + `process_validations` handling (the Task 4 wiring), `control/episode.py`, and a `--protocol v2` CLI branch on `run_agent_episode.py`.
- [x] Run the integration test and the full suite. (5 integration tests; full suite 272 passing; verified ShiftMem accumulates 12 revision experiences over 60 days with 0 pending left and both periodic+coalesced triggers firing)

### Task 6: v2 metrics and formal runner adaptation

**Files:**
- Modify: `src/shiftmem/evaluation/metrics.py`
- Modify: `scripts/run_formal_experiment.py`
- Create: `configs/experiments/formal_v2.yaml`
- Modify: `tests/unit/test_formal_metrics.py`
- Modify: `tests/unit/test_formal_runner.py`

**Interfaces:**
- Produces: v2 operational metrics (scheduled/event/coalesced/cooldown-suppressed review counts, parameter change magnitude and churn, invalid-proposal rate, retained-strategy fallback count, days between successful revisions, cost per successful revision) and a cell plan for the 320-cell primary tier + 160-cell secondary tier.

- [x] Write failing tests: primary tier = 8×10×2×{Vector,ShiftMem} = 320 cells; secondary tier = DeepSeek only ×5×4 baselines = 160 cells; Test-manifest rejection still enforced; new metrics computed deterministically from logs.
- [x] Confirm the failures.
- [x] Implement the metrics and the v2 cell plan; keep the freeze/Test-rejection gates intact. Added `summarize_strategy_reviews` (metrics), `validate_v2_config` + `build_v2_cell_plan` (runner), and `configs/experiments/formal_v2.yaml` with `budget_approved: false` and zero budgets.
- [x] Run focused and full tests. (12 new tests; full suite 280 passing; verified 320 primary + 160 secondary cells against 8 held-out IDs, Test-manifest IDs rejected)

### Task 7: Requalify core models on the strategy schema (offline first)

**Files:**
- Modify: `src/shiftmem/evaluation/model_qualification.py`
- Modify: `scripts/qualify_models.py`
- Create: `configs/experiments/model_qualification_v2.yaml`
- Modify: `tests/unit/test_model_qualification.py`

**Interfaces:**
- Produces: a bounded strategy-schema qualification suite (monotonicity and applicability gates expressed over strategy proposals) runnable offline against the deterministic provider, with live execution gated behind explicit budget approval.

- [x] Write failing tests for strategy-schema qualification gates.
- [x] Confirm the failures.
- [x] Implement the suite; do not perform any live call in this task. Added `src/shiftmem/evaluation/strategy_qualification.py` with monotonicity expressed over the strategy vector (higher demand / higher lost-sales pressure must not lower protection) and the unchanged dormant-memory applicability gate.
- [x] Run focused and full tests. (4 new tests; full suite 284 passing)

**Pending (live-gated):** The offline suite and its gates are complete and verified against synthetic qualifying/failing models. Running DeepSeek-V3.2 and MiniMax-M2.5 against this suite requires provider calls and is therefore blocked until explicit API-budget approval; the CLI runner wiring (`scripts/qualify_models.py --schema strategy`) will be added at that point so no accidental spend can occur beforehand.

### Task 8: v2 Pilot (Development/Validation only) and protocol finalization

**Files:**
- Create: `configs/experiments/v2_pilot.yaml`
- Create: `scripts/run_v2_pilot.py`
- Modify: `docs/experiment_protocol.md`
- Modify: `scripts/validate_protocol.py`
- Modify: `tests/unit/test_validate_protocol.py`
- Modify: `docs/implementation_log.md`
- Create: `docs/v2_pilot_report.md` (after the Pilot runs)

**Interfaces:**
- Produces: a network-free Pilot dry-run and, only after explicit budget approval, a bounded live Development/Validation Pilot measuring review frequency, attempts, tokens, latency, cost, parameter behavior, and variance — with no confirmatory held-out p-values.

- [x] Write failing tests: Pilot config is Validation-only; protocol validation requires v2 controller/scheduler/strategy fields and Pilot-report presence before any freeze claim.
- [x] Confirm the failures.
- [x] Implement the Pilot runner and offline dry-run; run the dry-run and record a trackable readiness report. Added `scripts/run_v2_pilot.py`, `configs/experiments/v2_pilot.yaml`, `validate_protocol_v2`, and `docs/v2_pilot_report.md`; the offline Pilot ran 40 episodes (0 fallbacks) and measured 30.8 reviews / 150-day episode (~0.205/day, a ~5× call reduction vs v1's 1.0/day).
- [x] Record the estimated v2 budget from the Pilot but leave live Test execution blocked pending explicit user approval. (Frequency measured offline; token-cost-per-review and the CNY ceiling are explicitly deferred to a budget-approved live Pilot.)
- [ ] Finalize `docs/experiment_protocol.md` from `2.0-draft` to `2.0` only after the Pilot report exists and the user approves the budget. **(BLOCKED on live Pilot + budget approval — the one remaining gate.)**

### Task 9: Final verification and Test-access gate

**Files:**
- Verify only: `configs/frozen/phase4-20260713-b99c0d3e4d27/`

- [x] Run protocol validation, split validation, focused tests, full pytest, `python -m compileall src`, and `git diff --check`. (289 passing; base + v2 protocol gates pass; compile OK; diff-check clean.)
- [x] Verify the v1 freeze is byte-for-byte unchanged. (`verify_freeze` verified; `git status configs/frozen/` empty.)
- [x] Scan `artifacts/` for Test-ID/Test-OOD outcome files and fail if any exist. (None present.)
- [x] Report the remaining blocker as explicit live API-budget approval plus a clean v2 freeze; do not start Test execution automatically. **Remaining blockers: (1) budget-approved live Pilot to measure token cost per review and requalify the two core models on the strategy schema; (2) protocol finalization to 2.0; (3) a clean v2 freeze. No Test execution until all three clear.**
