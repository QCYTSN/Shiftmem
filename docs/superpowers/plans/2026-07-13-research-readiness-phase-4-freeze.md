# Research Readiness and Phase 4 Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a defensible, validation-selected, hashed formal-experiment package without inspecting Test-ID or Test-OOD outcomes.

**Architecture:** Three gated packages execute in order: research governance, engineering readiness, and Phase 4 selection/freeze. Pure validation and hashing utilities remain network-free; only model qualification and the bounded model Pilot may use configured APIs.

**Tech Stack:** Python 3.12+, Pydantic 2, PyYAML 6, NumPy, pytest 8, existing compatible providers, SHA-256

## Global Constraints

- Primary endpoint: `post_shift_cumulative_regret_30` for ShiftMem versus VectorMemory.
- Test-ID and Test-OOD outcomes may not be generated or read during selection.
- All model methods share observation, prompt, action schema, top-k budget, and paired environment seeds.
- Raw runs remain ignored; aggregate evidence, manifests, protocols, and figures remain trackable.
- No API key, authorization header, or populated `.env` value enters tracked files.
- A dirty repository, incomplete protocol, unresolved second core model, or failed acceptance gate blocks freeze.

---

### Task 1: Freeze the experiment protocol

**Files:** Modify `docs/experiment_protocol.md`; create `scripts/validate_protocol.py`; create `tests/unit/test_validate_protocol.py`.

**Interfaces:** `validate_protocol(path: Path) -> list[str]` returns missing/invalid freeze requirements; CLI exits nonzero on errors.

- [ ] Write failing tests requiring RQs/H1-H5, primary comparison/endpoint, split rules, seed policy, statistical decision tree, multiplicity, failure handling, exclusion rules, model roles, no-test-tuning rule, and amendment process.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/unit/test_validate_protocol.py -q`; expect missing validator imports.
- [ ] Implement the validator with exact required heading/key phrases and placeholder rejection (`TBD`, `TODO`, `will record`).
- [ ] Replace the one-line protocol with a complete frozen document derived from the approved design and implementation specification.
- [ ] Run the focused tests and validator CLI; require zero errors.

### Task 2: Build the primary-source related-work matrix

**Files:** Create `docs/related_work_matrix.md`; modify `paper/references.bib`; create `tests/unit/test_research_docs.py`.

**Interfaces:** The Markdown matrix contains columns `Work`, `Problem`, `Memory unit`, `Change assumption`, `Retrieval`, `Validation`, `Lifecycle`, `Environment`, `Metrics`, `Limitations`, and `ShiftMem distinction`.

- [ ] Search only primary papers and official project pages for agent memory, reflection/skills, drift detection, nonstationary inventory, and business-agent evaluation.
- [ ] Write failing document tests requiring at least 12 works, all matrix columns, direct DOI/arXiv/official links, and no unsupported “first/novel/state-of-the-art” claim.
- [ ] Populate the matrix and BibTeX entries with verified metadata; distinguish confirmed facts from ShiftMem inferences.
- [ ] Run `.venv\Scripts\python.exe -m pytest tests/unit/test_research_docs.py -q`.

### Task 3: Complete the 100-seed Phase 1 acceptance

**Files:** Create `configs/experiments/phase1_acceptance.yaml`, `scripts/run_phase1_acceptance.py`, `tests/unit/test_phase1_acceptance.py`; create trackable `artifacts/aggregated/phase1_acceptance.json`.

**Interfaces:** `execute_acceptance(config, runner) -> AcceptanceSummary` evaluates 100 seeds × 5 scenarios × 5 policies and records run counts, finite metrics, horizon, paired demand, Oracle/random, and shift-marker gates.

- [ ] Write failing fake-runner tests for expected 2,500 runs and each failure gate.
- [ ] Implement a resumable network-free runner using existing scenario/policy factories and compact aggregate-only output.
- [ ] Run focused tests, then execute all 2,500 short CPU runs.
- [ ] Require all runs complete, all metrics finite, paired demand equality, Oracle mean cost below random per scenario, and valid shift markers.

### Task 4: Implement exact-window ADWIN

**Files:** Modify `src/shiftmem/detection/adwin.py`, `src/shiftmem/detection/__init__.py`; create `tests/unit/test_adwin.py`.

**Interfaces:** `ADWINDetector(variable, delta, min_window, clock, max_window).update(value, step) -> ChangeSignal | None` implements `ChangeDetector`.

- [ ] Write failing tests for stationary traces, upward/downward shifts, adaptive shrinkage, reset replay, finite values, step order, and configuration bounds.
- [ ] Implement exact cut-point scanning with two subwindows and a Hoeffding-style bound; shrink the oldest segment after detection.
- [ ] Run ADWIN and shared detector tests; require deterministic signals.

### Task 5: Automate dormancy and reactivation

**Files:** Modify `src/shiftmem/memory/shiftmem.py`; modify `src/shiftmem/memory/schemas.py`; create `tests/unit/test_memory_dormancy.py`.

**Interfaces:** `ShiftMemoryConfig.dormancy_patience`; retrieval updates per-memory consecutive mismatch counts, calls lifecycle transitions, and exposes counts in audit output.

- [ ] Write failing tests for patience, match reset, no-condition exemption, dormant exclusion, first-match reactivation, and audit reasons.
- [ ] Implement condition evaluation before hard retrieval and persist state through `ExperienceStore.replace`.
- [ ] Run dormancy, lifecycle, retrieval, and facade regressions.

### Task 6: Create split manifests and leakage validation

**Files:** Create Validation/Test-ID/Test-OOD YAML files under `configs/environments/`; create `configs/splits/*.yaml`; create `src/shiftmem/evaluation/splits.py`; create `scripts/validate_splits.py`; create `tests/unit/test_splits.py`.

**Interfaces:** `load_split_manifest`, `validate_split_manifests`, and `hash_scenario` reject duplicate IDs, hashes, prohibited seed overlap, and OOD definitions lacking held-out parameter/structure changes.

- [ ] Write failing tests for all leakage modes and deterministic hashes.
- [ ] Define explicit parameter ranges and held-out scenario configurations without running them.
- [ ] Implement validation and run it over all four manifests.

### Task 7: Select detector, dormancy, and retrieval settings on Validation

**Files:** Create `configs/experiments/validation_selection.yaml`, `scripts/select_validation_config.py`, `tests/unit/test_validation_selection.py`; create `artifacts/aggregated/validation_selection.json`.

**Interfaces:** The selector accepts Development/Validation manifests only; detector selection is lexicographic on misses, false positives, delay; retrieval selection uses primary endpoint, invalid reuse, then tokens.

- [ ] Write failing tests that reject Test-ID/Test-OOD paths and enforce deterministic tie-breaking.
- [ ] Implement the bounded predeclared grid and aggregate schema.
- [ ] Run detector selection offline; run the bounded DeepSeek retrieval selection with existing credentials only after cost estimation.
- [ ] Record selected settings without editing Test manifests.

### Task 8: Qualify a second open core model

**Files:** Modify `configs/experiments/model_qualification.yaml`; modify `docs/model_qualification.md`; update `artifacts/aggregated/model_qualification_summary.json`.

**Interfaces:** Reuse the fixed 8-case × 2-repetition qualification runner and hard gates unchanged.

- [ ] Query configured provider model lists and record available structured-output-capable open candidates without exposing keys.
- [ ] Predeclare exactly one candidate and license/role before live calls.
- [ ] Run the unchanged suite; raw output stays ignored and aggregate output is trackable.
- [ ] If it fails, stop model freeze and write an amendment rather than silently substituting another model.

### Task 9: Run the bounded Phase 4 Pilot

**Files:** Create `configs/experiments/phase4_pilot.yaml`, `scripts/run_phase4_pilot.py`, `scripts/report_phase4_pilot.py`, corresponding unit tests; create `docs/phase4_pilot_report.md` and aggregate artifacts.

**Interfaces:** Pilot consumes Development/Validation only and emits variance, runtime, token/failure metrics, metric completeness, and recommended formal seed count.

- [ ] Write fake-provider tests for matrix bounds, paired seeds, resume behavior, failure retention, and report generation from logs.
- [ ] Estimate call count/cost before live execution and keep the matrix bounded.
- [ ] Execute only after Tasks 1-8 pass; generate the report from raw logs.

### Task 10: Freeze and hash the formal package

**Files:** Create `scripts/freeze_experiment.py`, `scripts/verify_freeze.py`, tests; create `configs/frozen/<freeze-id>/manifest.sha256` plus canonical copied configs.

**Interfaces:** Freeze verifies clean Git state, protocol validator, second-model gate, selection evidence, and split manifests; SHA-256 manifest is sorted and reproducible.

- [ ] Write failing tests for every blocking condition, deterministic hashing, tamper detection, and accidental outcome files.
- [ ] Implement freeze/verify CLIs and create the freeze from committed canonical inputs.
- [ ] Run full pytest, compilation, diff, secret, ignore, and freeze verification checks.
- [ ] Do not begin formal experiments in this plan; hand off the verified freeze ID and manifest.
