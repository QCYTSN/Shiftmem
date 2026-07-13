# Inventory Prompt and Model Qualification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give every Agent a complete public inventory state and a unified decision objective, then qualify candidate models with bounded behavioral checks before formal experiments.

**Architecture:** `InventoryEnv` remains the source of public state and adds a 14-day realized-history window plus public costs and scheduled arrivals. A focused prompt module supplies one provider-independent system instruction. A pure qualification module defines paired cases and gates, while a CLI performs the bounded live calls and writes ignored raw plus trackable aggregate results.

**Tech Stack:** Python 3.11+, Pydantic 2, NumPy, PyYAML, pytest, existing OpenAI-compatible provider

## Global Constraints

- Never expose demand parameters, dispersion, future demand/fill, shift schedule, regime ID, or Oracle context.
- `recent_history` contains at most 14 completed days in chronological order.
- `pipeline_orders` contains nominal quantity and known due day only.
- All models receive identical requests at temperature 0, non-thinking JSON mode, and the same token cap.
- Automated tests use fake providers; only the final bounded qualification CLI uses live APIs.
- Raw model outputs stay under ignored `artifacts/raw_runs/`; aggregate qualification results are trackable.

---

### Task 1: Enrich the public inventory observation

**Files:**
- Modify: `tests/unit/test_inventory_env.py`
- Modify: `src/shiftmem/envs/inventory_env.py`
- Modify: `src/shiftmem/agents/llm_agent.py`

**Interfaces:**
- Produces: `InventoryEnv._observation() -> dict[str, Any]` with scalar compatibility keys, `pipeline_orders`, `quoted_lead_time`, `costs`, and `recent_history`.
- Consumes: existing scenario costs, current-day public supply terms, pending order due days, and completed environment records.

- [x] Write tests asserting reset has empty history/public costs, completed records enter history chronologically, the window truncates to 14, pipeline due dates are visible, and forbidden Oracle/shift keys are absent.
- [x] Run `.venv\Scripts\python.exe -m pytest tests/unit/test_inventory_env.py -q` and observe failures for missing keys.
- [x] Implement `_pipeline_orders()` and build the richer observation without changing transition order or record contents. Update Agent/fallback observation annotations to `dict[str, Any]`.
- [x] Re-run the inventory and structured-agent tests and require all to pass.

### Task 2: Add the unified inventory decision prompt

**Files:**
- Create: `src/shiftmem/providers/inventory_prompt.py`
- Modify: `src/shiftmem/providers/compatible_api.py`
- Modify: `tests/unit/test_compatible_api_provider.py`

**Interfaces:**
- Produces: `INVENTORY_DECISION_SYSTEM_PROMPT: str` and `build_inventory_user_message(request: ProviderRequest) -> str`.
- Consumes: the richer observation and retrieved memory records.

- [x] Write failing tests that inspect the fake HTTP payload and require the prompt to name the cost objective, inventory/pipeline accounting, recent history, fallible memory, supplied-ID rule, hidden-state prohibition, and exact JSON schema.
- [x] Run the provider test file and verify the prompt assertions fail.
- [x] Implement the focused prompt module and use it from `CompatibleAPIProvider`; user serialization stays deterministic and includes correction feedback when present.
- [x] Re-run provider and structured-agent tests and require all to pass.

### Task 3: Implement pure qualification cases and gates

**Files:**
- Create: `src/shiftmem/evaluation/model_qualification.py`
- Create: `tests/unit/test_model_qualification.py`

**Interfaces:**
- Produces: `QualificationCase`, `QualificationResult`, `build_qualification_cases()`, and `summarize_qualification(model_id, results)`.
- Paired groups: `demand_low/high`, `pipeline_empty/full`, and `stockout_cost_low/high`; single cases: `applicable_memory` and `inapplicable_memory`.

- [x] Write failing tests for deterministic case IDs, identical non-target fields within pairs, dormant-memory metadata, monotonic gate calculation, schema/fallback accounting, and aggregate qualification status.
- [x] Run the new test file and observe import/behavior failures.
- [x] Implement Pydantic result schemas, eight deterministic cases, and pure aggregate logic. A model qualifies only when both repetitions parse without fallback or invalid citations and all paired comparisons pass.
- [x] Re-run the new tests and require all to pass.

### Task 4: Add the bounded live qualification runner

**Files:**
- Create: `scripts/qualify_models.py`
- Create: `configs/experiments/model_qualification.yaml`
- Create: `tests/unit/test_qualify_models.py`
- Modify: `README.md`
- Modify: `docs/implementation_log.md`

**Interfaces:**
- Consumes: named provider profiles, optional model overrides, qualification cases, and two repetitions from YAML.
- Produces: ignored JSONL request results and aggregate JSON containing model/provider IDs, date, gates, tokens, latency, and qualification status.

- [x] Write failing tests using a fake provider factory to verify exact model/profile selection, two repetitions, unavailable/error recording, no credential fields, and aggregate output.
- [x] Run the new runner tests and observe import/behavior failures.
- [x] Implement CLI arguments `--config`, `--raw-output`, and `--summary-output`; configure Flash, open Qwen 35B-A3B, DeepSeek V3.2, and GLM-5.1 without embedding keys.
- [x] Re-run runner tests, then the full offline suite and compilation.
- [x] Run the bounded live qualification, inspect hard gates, apply one equal prompt correction after diagnosing truncation, rerun all candidates, update the implementation log/model recommendation, and verify raw output and `.env` are ignored and no populated key is present in repository text.
