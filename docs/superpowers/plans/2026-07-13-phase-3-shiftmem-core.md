# Phase 3 ShiftMem Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic, auditable ShiftMem loop that extracts experiences, detects related changes, updates lifecycle and confidence from delayed outcomes, and conditionally retrieves applicable memories.

**Architecture:** Focused components own schemas, detection, lifecycle/confidence, delayed validation, extraction, and retrieval. A `ShiftMemory` facade composes them behind the existing memory interface. Defaults remain offline and deterministic.

**Tech Stack:** Python 3.12+, Pydantic 2, standard-library math, existing lexical cosine scoring, pytest 8

## Global Constraints

- Never expose demand parameters, future demand/fill, shift schedules, regime IDs, or Oracle context.
- Do not call an LLM, embedding API, or network service in Phase 3.
- New experiences begin in `probation`; records are retained rather than deleted.
- Only experiences related to a detected variable may be demoted after a change.
- Confidence comes from positive finite Beta-Bernoulli `alpha` and `beta` values.
- Ordinary retrieval excludes `dormant` and `invalid` experiences.
- Existing memory baselines retain their behavior.

---

### Task 1: Experience schema, predicates, and store

**Files:** Modify `src/shiftmem/memory/schemas.py`, `src/shiftmem/memory/store.py`; create `tests/unit/test_shiftmem_schemas.py`.

**Interfaces:** Produces `MemoryStatus`, `ApplicabilityCondition.matches()`, `AuditEvent`, `ExperienceRecord.confidence`, `ExperienceRecord.to_memory_record()`, and `ExperienceStore`; consumes existing `MemoryRecord` and public observations.

- [ ] **Step 1: Write failing tests** for confidence, `eq/ge/gt/le/lt/in` predicates, Agent conversion, audit chronology, identical replay, and conflicting duplicate IDs.

```python
def test_experience_confidence_predicate_and_conversion() -> None:
    record = experience(alpha=3, beta=1, conditions=[
        ApplicabilityCondition(field="inventory", operator="le", value=20)
    ])
    assert record.confidence == 0.75
    assert record.is_applicable({"inventory": 20})
    assert not record.is_applicable({"inventory": 21})
    assert record.to_memory_record().payload["status"] == "probation"
```

- [ ] **Step 2: Verify RED**: `.venv\Scripts\python.exe -m pytest tests/unit/test_shiftmem_schemas.py -q`; expect missing schema/store imports.
- [ ] **Step 3: Implement** validated statuses, typed predicates, positive finite evidence, unique variables, derived confidence, Agent conversion, and replay-safe `add/get/all` storage.
- [ ] **Step 4: Verify GREEN**: `.venv\Scripts\python.exe -m pytest tests/unit/test_shiftmem_schemas.py tests/unit/test_memory_baselines.py -q`.

---

### Task 2: Page-Hinkley public-signal detector

**Files:** Modify `src/shiftmem/detection/base.py`, `page_hinkley.py`, `__init__.py`; create `tests/unit/test_page_hinkley.py`.

**Interfaces:** Produces `ChangeDirection`, `ChangeSignal`, `ChangeDetector`, and `PageHinkleyDetector.update(value: float, step: int) -> ChangeSignal | None`; consumes finite realized values at increasing steps.

- [ ] **Step 1: Write failing tests** for warm-up, upward/downward shifts, reset/replay, NaN/infinity, and repeated steps.

```python
def test_detector_ignores_warmup_then_detects_increase() -> None:
    detector = PageHinkleyDetector("demand", min_samples=5, delta=0.05, threshold=2)
    assert all(detector.update(10, step) is None for step in range(5))
    signal = next(filter(None, (detector.update(20, step) for step in range(5, 10))))
    assert signal.variable == "demand"
    assert signal.direction == ChangeDirection.INCREASE
```

- [ ] **Step 2: Verify RED**: `.venv\Scripts\python.exe -m pytest tests/unit/test_page_hinkley.py -q`.
- [ ] **Step 3: Implement** resettable two-sided deviations from a running mean, emitting one typed signal per crossing and resetting cumulative detection state afterward.
- [ ] **Step 4: Verify GREEN** with the same focused command.

---

### Task 3: Lifecycle and Beta-Bernoulli confidence

**Files:** Modify `src/shiftmem/memory/lifecycle.py`; create `src/shiftmem/memory/confidence.py` and `tests/unit/test_memory_lifecycle.py`.

**Interfaces:** Produces `EvidenceOutcome`, `ConfidenceUpdater.apply()`, `LifecyclePolicy`, and `LifecycleManager.apply_evidence/apply_change/mark_dormant/reactivate`; consumes experiences and change signals.

- [ ] **Step 1: Write failing tests** for promotion, weighted post-change failure, invalidation, dormant reactivation, illegal transitions, audit chronology, and variable-scoped changes.

```python
def test_change_only_demotes_related_record() -> None:
    demand = experience(status="active", variables=["demand"])
    lead = experience(memory_id="lead", status="active", variables=["lead_time"])
    manager.apply_change([demand, lead], change(variable="demand"), step=20)
    assert demand.status == MemoryStatus.PROBATION
    assert lead.status == MemoryStatus.ACTIVE
```

- [ ] **Step 2: Verify RED**: `.venv\Scripts\python.exe -m pytest tests/unit/test_memory_lifecycle.py -q`.
- [ ] **Step 3: Implement** the legal transition table, positive finite weights, inconclusive no-op evidence, threshold promotion/invalidation, and append-only audit events.
- [ ] **Step 4: Verify GREEN** with the same focused command.

---

### Task 4: Delayed validation and deterministic extraction

**Files:** Modify `src/shiftmem/memory/validator.py`, `extractor.py`; create `tests/unit/test_memory_validation.py` and `test_experience_extractor.py`.

**Interfaces:** Produces `PendingValidation`, `ValidationResult`, `DelayedValidator.register/evaluate`, and `ExperienceExtractor.extract(...) -> ExperienceRecord`; consumes public decisions and chronological realized records.

- [ ] **Step 1: Write failing validation tests** for due steps, incomplete/non-contiguous windows, outcome classification, duplicate completion, and public-only metrics.

```python
def test_validation_waits_for_complete_window() -> None:
    pending = validator.register("mem-1", decision_step=4, quoted_lead_time=2)
    assert pending.due_step == 9
    assert validator.evaluate(pending, history_through_day_8).outcome == EvidenceOutcome.PENDING
```

- [ ] **Step 2: Write failing extraction tests** for stable IDs, replay, templated text, typed conditions, and forbidden-key rejection.
- [ ] **Step 3: Verify RED**: `.venv\Scripts\python.exe -m pytest tests/unit/test_memory_validation.py tests/unit/test_experience_extractor.py -q`.
- [ ] **Step 4: Implement** lead-time-plus-window scheduling, contiguous-window checks, deterministic lost-sales/fill-rate/cost criteria, stable IDs, and filtered public payloads.
- [ ] **Step 5: Verify GREEN** with the same focused command.

---

### Task 5: Two-stage conditional retrieval

**Files:** Modify `src/shiftmem/memory/retriever.py`, `store.py`; create `tests/unit/test_conditional_retriever.py`.

**Interfaces:** Produces `SemanticScorer`, `LexicalSemanticScorer`, `RetrievalWeights`, `RetrievalScore`, `RetrievedExperience`, and `ConditionalRetriever.retrieve()`; consumes experiences, observation, query, step, top-k, variable filters, and recent changes.

- [ ] **Step 1: Write failing tests** for status/applicability filtering, probation and change penalties, score components, deterministic ties, top-k, and injected scorer.

```python
def test_retrieval_filters_and_exposes_score() -> None:
    results = retriever.retrieve(records, "rising demand", {"inventory": 10}, 30, 5)
    assert [item.record.memory_id for item in results] == ["active-match", "probation-match"]
    score = results[0].score
    assert score.total == pytest.approx(
        score.semantic + score.confidence + score.recency + score.utility - score.shift_penalty
    )
```

- [ ] **Step 2: Verify RED**: `.venv\Scripts\python.exe -m pytest tests/unit/test_conditional_retriever.py -q`.
- [ ] **Step 3: Implement** hard eligibility plus normalized lexical, confidence, recency, utility, and penalty components with validated weights and deterministic sorting.
- [ ] **Step 4: Verify GREEN**: `.venv\Scripts\python.exe -m pytest tests/unit/test_conditional_retriever.py tests/unit/test_memory_baselines.py -q`.

---

### Task 6: Facade, episode integration, and documentation

**Files:** Create `src/shiftmem/memory/shiftmem.py`, `tests/unit/test_shift_memory.py`; modify `memory/__init__.py`, `store.py`, `scripts/run_agent_episode.py`, `tests/integration/test_run_episode.py`, `README.md`, and `docs/implementation_log.md`.

**Interfaces:** Produces `ShiftMemory.add/retrieve/observe_signal/register_decision/process_validations/audit` and `make_memory("shiftmem")`; consumes all prior Phase 3 components and the structured Agent loop.

- [ ] **Step 1: Write failing facade tests** for an imported active experience, related detection, probation, delayed failure, audit inspection, and invalid-record exclusion.
- [ ] **Step 2: Extend integration tests** to run `--memory shiftmem`, require bounded IDs/audit output, and reject forbidden stored keys.
- [ ] **Step 3: Verify RED**: `.venv\Scripts\python.exe -m pytest tests/unit/test_shift_memory.py tests/integration/test_run_episode.py -q`.
- [ ] **Step 4: Implement** component composition while keeping `retrieve(query, step, top_k)` compatible with `StructuredAgent`.
- [ ] **Step 5: Document** the offline command and lexical/Page-Hinkley development limitations:

```powershell
.venv\Scripts\python.exe scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory shiftmem --provider deterministic --max-days 30 --output artifacts/raw_runs/shiftmem_offline.json
```

- [ ] **Step 6: Verify all work** by running full pytest, `compileall -q src scripts tests`, `git diff --check`, and `git status --short`. Expect all tests and compilation to pass and only intentional Phase 3 files to be modified.
