# Protocol v1.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every post-freeze blocker using Development/Validation evidence, issue protocol v1.1, and create a verified replacement freeze without generating or reading Test-ID/Test-OOD outcomes.

**Architecture:** Make the environment daily record the canonical public detector-signal envelope, then use the same fields in selection and runtime. Keep statistical analysis pure and deterministic, put durable JSONL journaling behind a focused logger, and make the formal runner validate freeze identity, matrix completeness, and budgets before dispatch. Test manifests may be extended and hashed, but no code in this phase executes their scenarios.

**Tech Stack:** Python 3.12, Pydantic 2, NumPy, PyYAML, pytest 8, JSON/JSONL, SHA-256

## Global Constraints

- Never modify `configs/frozen/phase4-20260713-b99c0d3e4d27/`.
- Never generate or read Test-ID or Test-OOD outcomes during v1.1 preparation.
- Use only Development/Validation runs for detector selection and dry-runs.
- Preserve failed, fallback, partial, and unfavorable results.
- Perform provider calls only after explicit API-budget approval; network-free dry-runs do not imply that approval.
- The replacement freeze must be created from a clean commit and verified byte-for-byte.

---

### Task 1: Unify the public detector signal contract

**Files:**
- Modify: `src/shiftmem/envs/inventory_env.py`
- Modify: `src/shiftmem/memory/shiftmem.py`
- Modify: `scripts/select_validation_config.py`
- Test: `tests/unit/test_inventory_env.py`
- Test: `tests/unit/test_shift_memory.py`
- Test: `tests/unit/test_validation_selection.py`

**Interfaces:**
- Consumes: public daily fields `demand`, `lost_sales`, and `quoted_lead_time`.
- Produces: `DETECTOR_SIGNAL_FIELDS: tuple[str, ...]` and a daily record containing all three values.

- [ ] Add failing tests proving the environment record includes the decision-time quoted lead time and runtime routes it to `observe_signal`.
- [ ] Run the focused tests and confirm the missing field/routing failures.
- [ ] Add `quoted_lead_time` to the environment record before the day advances, define one shared signal-field tuple, and iterate it in `ShiftMemory.observe_outcome`.
- [ ] Make Validation selection import/use the same signal-field name for supply-only episodes.
- [ ] Run the focused tests and the complete suite.
- [ ] Rerun `scripts/select_validation_config.py` against Development/Validation and replace only `artifacts/aggregated/validation_selection.json`.

### Task 2: Add held-out H3/H4 definitions without outcome access

**Files:**
- Create: `configs/environments/test_id_stable.yaml`
- Create: `configs/environments/test_ood_periodic.yaml`
- Modify: `configs/splits/test_id.yaml`
- Modify: `configs/splits/test_ood.yaml`
- Modify: `tests/unit/test_splits.py`

**Interfaces:**
- Consumes: existing scenario schema and split collision validator.
- Produces: one held-out stable Test-ID definition and one held-out periodic Test-OOD definition with declared held-out dimensions.

- [ ] Add a failing manifest test requiring a stable Test-ID entry and periodic Test-OOD entry.
- [ ] Add scenario YAML files with unique semantic hashes and append config-only manifest entries.
- [ ] Run split validation and prove no outcome path was created.

### Task 3: Implement formal endpoints and paired statistics

**Files:**
- Modify: `src/shiftmem/evaluation/metrics.py`
- Replace: `src/shiftmem/evaluation/statistics.py`
- Create: `tests/unit/test_formal_metrics.py`
- Create: `tests/unit/test_statistics.py`

**Interfaces:**
- Produces: `recovery_time(records, oracle_records, shift_day, ...)`, `paired_summary(pairs)`, `holm_adjust(p_values)`, and JSON-safe result dictionaries.

- [ ] Write failing tests for 30-day regret, recovered/right-censored recovery, paired mean/SD/CI/effect size, exact sign-test fallback, and Holm monotonicity.
- [ ] Implement deterministic endpoints with standard library and NumPy only; do not claim a Wilcoxon p-value without a validated implementation.
- [ ] Run focused and full tests.

### Task 4: Implement durable per-decision journaling and budget gates

**Files:**
- Replace: `src/shiftmem/logging/schemas.py`
- Replace: `src/shiftmem/logging/run_logger.py`
- Create: `tests/unit/test_run_logger.py`

**Interfaces:**
- Produces: immutable `RunIdentity`, `DecisionJournalEntry`, `BudgetLimits`, and `JsonlRunJournal` with append/fsync, replay lookup, counters, and fail-closed budget checks.

- [ ] Write failing tests for identity mismatch, truncated-last-line recovery, response replay, duplicate decision rejection, and call/token/cost ceilings.
- [ ] Implement Pydantic schemas and append-only JSONL journaling; never persist credentials.
- [ ] Run focused and full tests.

### Task 5: Build the freeze-bound six-method runner

**Files:**
- Create: `configs/experiments/formal_v1_1.yaml`
- Create: `scripts/run_formal_experiment.py`
- Create: `tests/unit/test_formal_runner.py`
- Create: `tests/integration/test_formal_dry_run.py`

**Interfaces:**
- Consumes: a verified freeze, Development/Validation manifest, six method IDs, two core models, budgets, and the journal.
- Produces: a deterministic cell plan, dry-run report, and resumable provider execution path.

- [ ] Write failing tests for six-method completeness, Test manifest rejection, freeze mismatch, deterministic cell IDs, dry-run no-provider behavior, and budget preflight.
- [ ] Implement `build_cell_plan`, `validate_formal_config`, and CLI `--dry-run`; provider execution must consult the journal before each decision.
- [ ] Run Development/Validation dry-runs only and store a trackable aggregate readiness report.

### Task 6: Issue protocol v1.1 and replacement-freeze tooling

**Files:**
- Create: `docs/experiment_protocol_v1.1.md`
- Modify: `scripts/validate_protocol.py`
- Modify: `scripts/freeze_experiment.py`
- Modify: `tests/unit/test_validate_protocol.py`
- Modify: `tests/unit/test_freeze_experiment.py`
- Modify: `docs/formal_experiment_readiness_audit.md`
- Modify: `docs/implementation_log.md`

**Interfaces:**
- Produces: a numbered amendment, v1.1-specific gates, a full API call/token ceiling, and a versioned replacement-freeze ID.

- [ ] Write failing tests requiring amendment rationale, changed fields, selected detector evidence, held-out coverage, formal-runner dry-run, and budget-approval state.
- [ ] Write protocol v1.1 without changing v1; update freeze canonical inputs and compute a new date/hash-derived ID.
- [ ] Record an estimated full matrix budget but leave live execution blocked until the user explicitly approves it.
- [ ] Commit all v1.1 inputs, run 100% network-free validation, create the replacement freeze from the clean commit, and verify it.

### Task 7: Final verification and Test-access gate

**Files:**
- Verify only: `configs/frozen/phase4-20260713-b99c0d3e4d27/`
- Verify only: new replacement-freeze directory

- [ ] Run protocol validation, split validation, focused tests, full pytest, compileall, and `git diff --check`.
- [ ] Verify both old and replacement freezes.
- [ ] Scan raw outputs for Test-ID/Test-OOD names and fail if any outcome file exists.
- [ ] Report remaining blocker as explicit live API-budget approval and/or Development/Validation provider dry-run evidence; do not start Test execution automatically.
