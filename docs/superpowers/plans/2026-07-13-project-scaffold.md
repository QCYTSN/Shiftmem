# ShiftMem Project Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the complete ShiftMem repository skeleton defined in `ShiftMem_Implementation_Spec.md` without implementing business logic or connecting to a real model API.

**Architecture:** Use a `src/`-layout Python package with responsibility-focused subpackages for environments, agents, memory, detection, evaluation, providers, and logging. Keep executable entry points, configuration, tests, artifacts, paper sources, and documentation separated at the repository root.

**Tech Stack:** Python package layout, Markdown, dotenv-compatible environment template, Git ignore rules.

## Global Constraints

- Do not implement inventory, agent, ShiftMem, demo, provider, or experiment behavior.
- Do not call or configure a real LLM API.
- Do not place credentials in any tracked file.
- Do not create `LICENSE`.
- Do not create a Git commit.
- Preserve `ShiftMem_Implementation_Spec.md` unchanged.
- Keep `configs/`, `tests/`, `scripts/`, `data/sample/`, `artifacts/aggregated/`, `artifacts/figures/`, and `.env.example` trackable.

---

### Task 1: Repository metadata and safety rules

**Files:**
- Create: `README.md`
- Create: `.env.example`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: research scope and repository rules from `ShiftMem_Implementation_Spec.md`.
- Produces: the human entry point, safe environment-variable template, and repository tracking policy.

- [ ] **Step 1: Create the README**

Create `README.md` with the project title, the specification summary, current scaffold-only status, a link to `ShiftMem_Implementation_Spec.md`, the planned package areas, and this credential rule: copy `.env.example` to `.env`, keep `.env` local, and never commit API keys.

- [ ] **Step 2: Create the environment template**

Create `.env.example` with exactly:

```dotenv
MODEL_API_KEY=
MODEL_BASE_URL=
MODEL_NAME=
```

- [ ] **Step 3: Extend the Python `.gitignore`**

Append project-specific rules for Python caches, environments, IDE state, Jupyter checkpoints, model/cache directories, raw experiment outputs, large data/model files, OS files, and LaTeX build files. Add negation rules for `.env.example`, `data/sample/`, `artifacts/aggregated/`, and `artifacts/figures/` so reproducibility assets remain trackable.

- [ ] **Step 4: Verify credential and tracking rules**

Run:

```powershell
git check-ignore -v .env .env.example artifacts/raw_runs/example.json artifacts/aggregated/.gitkeep data/raw/example.csv data/sample/.gitkeep
```

Expected: `.env`, raw runs, and raw data are ignored; `.env.example`, aggregated artifacts, and sample data are not ignored.

### Task 2: Complete source and project skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/shiftmem/__init__.py`
- Create: `src/shiftmem/envs/{__init__.py,inventory_env.py,demand_models.py,supply_models.py,shifts.py}`
- Create: `src/shiftmem/agents/{__init__.py,base.py,llm_agent.py,classical.py,oracle.py}`
- Create: `src/shiftmem/memory/{__init__.py,schemas.py,store.py,extractor.py,retriever.py,validator.py,lifecycle.py}`
- Create: `src/shiftmem/detection/{__init__.py,base.py,page_hinkley.py,adwin.py}`
- Create: `src/shiftmem/evaluation/{__init__.py,metrics.py,statistics.py,plots.py}`
- Create: `src/shiftmem/providers/{__init__.py,base.py,local.py,compatible_api.py}`
- Create: `src/shiftmem/logging/{__init__.py,schemas.py,run_logger.py}`
- Create: `scripts/{run_episode.py,run_experiment.py,aggregate_results.py,make_paper_figures.py}`
- Create: `demo/app.py`
- Create: `paper/main.tex`
- Create: `paper/references.bib`
- Create: `docs/{experiment_protocol.md,memory_schema.md,model_card.md,implementation_log.md}`
- Create: `.gitkeep` files under empty configuration, test, artifact, and sample-data directories.

**Interfaces:**
- Consumes: repository map from specification section 11.
- Produces: importable package boundaries and visible placeholders for every planned project component.

- [ ] **Step 1: Create project directories**

Create all directories listed in the file map, including `configs/environments`, `configs/agents`, `configs/experiments`, `tests/unit`, `tests/integration`, `tests/regression`, `artifacts/raw_runs`, `artifacts/aggregated`, `artifacts/figures`, and `data/sample`.

- [ ] **Step 2: Create package marker and module files**

Each `__init__.py` and Python module must contain only a concise module docstring describing its planned responsibility. No classes, functions, imports with side effects, network calls, or executable behavior may be added.

- [ ] **Step 3: Create non-Python placeholders**

Use a minimal valid LaTeX document for `paper/main.tex`, an empty BibTeX file for `paper/references.bib`, short scope statements in the planned docs, and `.gitkeep` files for otherwise empty tracked directories.

- [ ] **Step 4: Create minimal package metadata**

Create `pyproject.toml` with a standards-based build-system section, project name `shiftmem`, version `0.1.0`, a Python version floor derived from the locally available interpreter, and setuptools package discovery under `src`. Do not add runtime dependencies before Phase 1 selects them.

- [ ] **Step 5: Compile all Python placeholders**

Run:

```powershell
python -m compileall -q src scripts demo
```

Expected: exit code 0 with no syntax errors.

### Task 3: Structure and scope verification

**Files:**
- Verify: all files created by Tasks 1 and 2
- Verify unchanged: `ShiftMem_Implementation_Spec.md`

**Interfaces:**
- Consumes: completed scaffold.
- Produces: evidence that the skeleton is complete, safe, and free of business implementation.

- [ ] **Step 1: Compare the tree with the specification**

List all files recursively, excluding `.git` and generated `__pycache__` directories, then confirm every path from specification section 11 exists plus the approved `__init__.py`, `.env.example`, `.gitkeep`, and implementation-planning files.

- [ ] **Step 2: Scan for secrets**

Run a case-insensitive search for common credential assignments and confirm no non-empty API key or token value exists.

- [ ] **Step 3: Confirm ignored and trackable outputs**

Use `git check-ignore` on representative raw, aggregate, figure, sample-data, `.env`, and `.env.example` paths. Confirm raw/large outputs are ignored and reproducibility assets remain trackable.

- [ ] **Step 4: Review Git status**

Run:

```powershell
git status --short
```

Expected: only the implementation specification and approved scaffold files are new or modified; no environment, cache, compiled bytecode, credentials, dataset, model, or raw experiment output is present.

