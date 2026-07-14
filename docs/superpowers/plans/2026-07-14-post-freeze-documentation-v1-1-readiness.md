# Post-Freeze Documentation and v1.1 Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the live project documentation accurately describe the verified v1 freeze, its known blockers, and the exact v1.1 work required before formal Test execution.

**Architecture:** Preserve the frozen directory byte-for-byte and update only live documentation. A focused document test encodes the critical freeze ID, model roles, Pilot scope disclosures, blocker categories, and no-Test-access rule so future edits cannot silently restore obsolete readiness claims.

**Tech Stack:** Markdown, pytest 8, existing protocol/split/freeze validators, Git

## Global Constraints

- Do not modify any file under `configs/frozen/phase4-20260713-b99c0d3e4d27/`.
- Do not generate or read Test-ID or Test-OOD outcome files.
- Preserve every measured value already reported by the Phase 4 Pilot.
- Treat freeze v1 as an immutable audit snapshot, not as the package for immediate formal execution.
- The next formal package is a versioned v1.1 replacement freeze produced only after Development/Validation revalidation.

---

### Task 1: Encode documentation consistency requirements

**Files:**
- Modify: `tests/unit/test_research_docs.py`

**Interfaces:**
- Consumes: live Markdown files and the fixed freeze ID.
- Produces: pytest assertions that block obsolete model status, missing Pilot disclosures, missing audit blockers, or an omitted no-Test-access rule.

- [ ] **Step 1: Add a failing live-document status test**

Add a test that reads `README.md`, `docs/implementation_log.md`, `docs/phase4_pilot_report.md`, and `docs/formal_experiment_readiness_audit.md`. Require:

```python
assert "phase4-20260713-b99c0d3e4d27" in readme
assert "MiniMax-M2.5" in readme
assert "v1.1" in readme
assert "fixed-policy pre-shift warm-up" in pilot
assert "pre-seeded memories" in pilot
assert "Detector-selection/runtime mismatch" in audit
assert "Hypothesis coverage gaps" in audit
assert "Test-ID and Test-OOD outcomes must not be generated or read" in audit
assert "Post-freeze readiness audit" in implementation_log
```

Also reject the obsolete README sentence `the planned two-model formal design is not yet frozen`.

- [ ] **Step 2: Run the focused test and confirm the documentation is stale**

Run `.venv\Scripts\python.exe -m pytest tests/unit/test_research_docs.py -q`.

Expected: failure because the readiness audit does not exist and README/Pilot disclosures are absent.

### Task 2: Update the project entry point and implementation history

**Files:**
- Modify: `README.md`
- Modify: `docs/implementation_log.md`

**Interfaces:**
- Consumes: verified freeze state and aggregate evidence.
- Produces: a current repository overview and chronological audit history.

- [ ] **Step 1: Replace obsolete README qualification text**

State that DeepSeek-V3.2 and MiniMax-M2.5 are Core A/Core B, GLM-5.1 is supplementary, and both Qwen candidates failed the fixed applicability gate. Add the v1 freeze ID, link the live Pilot report and readiness audit, and state that formal execution is blocked pending v1.1.

- [ ] **Step 2: Add current verification and next-phase commands**

Document these network-free commands:

```powershell
.venv\Scripts\python.exe scripts/verify_freeze.py configs/frozen/phase4-20260713-b99c0d3e4d27
.venv\Scripts\python.exe -m pytest -q
```

Explain that users must not edit the archived freeze or run Test outcomes before a replacement freeze.

- [ ] **Step 3: Append Phase 4 and post-freeze entries to the implementation log**

Record Phase 1 acceptance, ADWIN, dormancy/reactivation, split creation, Validation selections, MiniMax qualification, Phase 4 metrics, v1 freeze creation, and the five blocker classes from the design. Label the new section `Post-freeze readiness audit`.

### Task 3: Correct Pilot interpretation and create the readiness audit

**Files:**
- Modify: `docs/phase4_pilot_report.md`
- Create: `docs/formal_experiment_readiness_audit.md`

**Interfaces:**
- Consumes: Pilot and Validation aggregate evidence, the live runtime signal path, and frozen Test manifests.
- Produces: an explicit evidence boundary and a pass/blocked readiness matrix.

- [ ] **Step 1: Add a Pilot design disclosure**

Add a section stating one Validation `demand_jump` scenario, two seeds, 30 post-shift model decisions per cell, fixed-policy pre-shift warm-up, four pre-seeded memories, only VectorMemory and ShiftMem, and that 52 seeds is provisional. Do not change existing measured values.

- [ ] **Step 2: Write the formal readiness audit**

Create a table with statuses `PASS`, `LIMITATION`, and `BLOCKED`. Include freeze integrity, automated tests, Phase 1, model qualification, detector alert rate, Pilot scope, detector signal mismatch, H3/H4 coverage, formal statistics, idempotent logging/budget gates, and the six-method formal configuration.

State that Test-ID and Test-OOD outcomes must not be generated or read before v1.1 replacement freeze verification.

- [ ] **Step 3: Define v1.1 exit criteria and work order**

Copy the approved nine-step work order and add measurable exit criteria: selected signal path regression tests, affected Validation rerun, hashed held-out stable/periodic configs, tested statistics/formal runner, budget approval, committed protocol v1.1, and a verified replacement freeze.

### Task 4: Verify documentation and preserve freeze integrity

**Files:**
- Test: `tests/unit/test_research_docs.py`
- Verify only: `configs/frozen/phase4-20260713-b99c0d3e4d27/`

**Interfaces:**
- Consumes: all documentation changes.
- Produces: evidence that documentation is consistent and frozen v1 remains unchanged.

- [ ] **Step 1: Run focused document tests**

Run `.venv\Scripts\python.exe -m pytest tests/unit/test_research_docs.py -q`.

Expected: all document tests pass.

- [ ] **Step 2: Run validators and freeze verification**

Run:

```powershell
.venv\Scripts\python.exe scripts/validate_protocol.py docs/experiment_protocol.md
.venv\Scripts\python.exe scripts/validate_splits.py configs/splits/development.yaml configs/splits/validation.yaml configs/splits/test_id.yaml configs/splits/test_ood.yaml
.venv\Scripts\python.exe scripts/verify_freeze.py configs/frozen/phase4-20260713-b99c0d3e4d27
```

Expected: protocol/split validation and freeze verification succeed.

- [ ] **Step 3: Run full verification**

Run:

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m compileall -q src scripts tests
git diff --check
git status --short
```

Expected: 206 or more tests pass; compilation and diff checks exit zero; Git lists only the four live documents, the new audit, and the document test.

- [ ] **Step 4: Commit the documentation update**

After review, commit with:

```powershell
git add README.md docs/implementation_log.md docs/phase4_pilot_report.md docs/formal_experiment_readiness_audit.md tests/unit/test_research_docs.py
git commit -m "Document post-freeze audit and v1.1 blockers"
```

