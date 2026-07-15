# Protocol v2 Qualification Conformance Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the runtime strategy reviewer and model-qualification harness conform to protocol `2.0-draft` while preserving the strict four-of-four monotonicity gate and all prior unfavorable evidence.

**Architecture:** Add a v2-only provider request contract and propagate it through runtime and qualification. Route strategy qualification through the strategy prompt, replace impossible synthetic histories with invariant-checked public histories, preserve every retry attempt, and make run outputs provenance-rich and non-overwriting by default. Keep the archived v1 request, v1 prompt, formal endpoints, frozen configuration, and Test outcomes untouched.

**Tech Stack:** Python 3.12, Pydantic 2, pytest 8, JSON/JSONL, SHA-256, Git metadata, PowerShell verification

## Global Constraints

- Keep `monotonicity_checks == 4` and `monotonicity_passes == 4` as the qualification requirement.
- Keep RQ1-RQ5, H1-H5, `post_shift_cumulative_regret_30`, paired seeds, memory methods, scenario manifests, and Conditional-not-Causal framing unchanged.
- Do not modify `configs/frozen/phase4-20260713-b99c0d3e4d27/`.
- Do not access or create Test-ID or Test-OOD outcomes.
- Do not call a live provider during implementation or verification.
- Preserve the current `artifacts/raw_runs/model_qualification_v2.jsonl` and `artifacts/aggregated/model_qualification_v2_summary.json` byte-for-byte.
- Work in the existing checkout because the uncommitted v2 implementation is the repair target; do not reset, discard, or overwrite unrelated user changes.

---

### Task 1: Complete the v2 provider request contract

**Files:**
- Modify: `src/shiftmem/providers/base.py`
- Modify: `src/shiftmem/providers/inventory_prompt.py`
- Modify: `src/shiftmem/agents/strategy_agent.py`
- Modify: `src/shiftmem/control/episode.py`
- Modify: `tests/unit/test_agent_schemas.py`
- Modify: `tests/unit/test_strategy_agent.py`
- Modify: `tests/integration/test_v2_episode.py`

**Interfaces:**
- Consumes: validated `StrategyParameters`, scheduler `ReviewDecision`, public observation, retrieved memory.
- Produces: `StrategyProviderRequest(current_strategy, trigger_reason, trigger_evidence)` used by every v2 provider call.

- [ ] **Step 1: Add failing request-schema and prompt-serialization tests**

```python
def test_strategy_request_requires_protocol_inputs():
    request = StrategyProviderRequest(
        observation=_observation(),
        memory=[],
        current_strategy={
            "forecast_window": 14,
            "safety_stock_multiplier": 1.2,
            "lead_time_buffer": 1,
        },
        trigger_reason="event",
        trigger_evidence={"variable": "lost_sales", "day": 8},
    )
    payload = json.loads(build_strategy_review_user_message(request))
    assert payload["current_strategy"]["forecast_window"] == 14
    assert payload["trigger_reason"] == "event"
    assert payload["trigger_evidence"]["variable"] == "lost_sales"

def test_archived_provider_request_shape_is_unchanged():
    request = ProviderRequest(observation={"day": 1}, memory=[])
    assert request.model_dump() == {
        "observation": {"day": 1}, "memory": [], "correction": None
    }
```

- [ ] **Step 2: Run schema tests and confirm RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_agent_schemas.py -q`

Expected: import or validation failure because `StrategyProviderRequest` does not exist.

- [ ] **Step 3: Implement the v2-only request type and typed prompt builder**

```python
class StrategyProviderRequest(ProviderRequest):
    current_strategy: dict[str, int | float]
    trigger_reason: Literal["periodic", "event", "coalesced"]
    trigger_evidence: dict[str, Any] = Field(default_factory=dict)


def build_strategy_review_user_message(request: StrategyProviderRequest) -> str:
    return json.dumps(
        {
            "task": "Propose the bounded strategy parameters for the deterministic controller.",
            **request.model_dump(),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
```

- [ ] **Step 4: Add failing runtime-forwarding tests**

```python
def test_agent_forwards_current_strategy_and_trigger_evidence():
    provider = CapturingStrategyProvider(_valid_strategy_json())
    agent = StrategyReviewAgent(provider=provider, memory=NoMemory())
    current = StrategyParameters()
    evidence = {"variable": "lost_sales", "day": 7}
    agent.review(_observation(), current, "event", evidence)
    sent = provider.requests[0]
    assert sent.current_strategy == current.model_dump()
    assert sent.trigger_reason == "event"
    assert sent.trigger_evidence == evidence
```

Add an integration assertion that an event/coalesced review log contains the
same evidence placed in the provider request by `run_v2_episode`.

- [ ] **Step 5: Run runtime tests and confirm RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_strategy_agent.py tests/integration/test_v2_episode.py -q`

Expected: `StrategyReviewAgent.review` rejects the evidence argument or captured requests lack protocol fields.

- [ ] **Step 6: Propagate the complete request through agent and episode**

```python
def review(
    self,
    observation: dict[str, Any],
    current_strategy: StrategyParameters,
    trigger_reason: Literal["periodic", "event", "coalesced"],
    trigger_evidence: dict[str, Any] | None = None,
) -> StrategyParameters:
    request = StrategyProviderRequest(
        observation=observation,
        memory=[record.model_dump() for record in records],
        correction=correction,
        current_strategy=current_strategy.model_dump(),
        trigger_reason=trigger_reason,
        trigger_evidence=dict(trigger_evidence or {}),
    )
```

In `run_v2_episode`, pass `decision.evidence or {}` to `agent.review` and record
that evidence in `StrategyReviewLog` so the model-facing input remains auditable.

- [ ] **Step 7: Run focused tests and confirm GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_agent_schemas.py tests/unit/test_strategy_agent.py tests/integration/test_v2_episode.py -q`

Expected: all selected tests pass.

---

### Task 2: Route qualification through the v2 prompt and expose the controller formula

**Files:**
- Modify: `src/shiftmem/providers/inventory_prompt.py`
- Modify: `scripts/qualify_models.py`
- Modify: `tests/unit/test_agent_schemas.py`
- Modify: `tests/unit/test_strategy_qualification_runner.py`

**Interfaces:**
- Consumes: provider profile and model ID.
- Produces: `_default_strategy_provider_factory` configured with the strategy system prompt and strategy message builder.

- [ ] **Step 1: Add failing prompt-routing tests**

```python
def test_strategy_factory_uses_strategy_prompt_and_builder():
    provider = _default_strategy_provider_factory(
        "siliconflow", "deepseek-ai/DeepSeek-V3.2"
    )
    assert provider.system_prompt == STRATEGY_REVIEW_SYSTEM_PROMPT
    assert provider.build_user_message is build_strategy_review_user_message

def test_order_factory_remains_on_archived_order_prompt():
    provider = _default_provider_factory("siliconflow", "model")
    assert provider.system_prompt == INVENTORY_DECISION_SYSTEM_PROMPT
    assert provider.build_user_message is build_inventory_user_message

def test_strategy_prompt_explains_joint_target_formula():
    prompt = STRATEGY_REVIEW_SYSTEM_PROMPT
    assert "quoted_lead_time + lead_time_buffer + 1" in prompt
    assert "safety_stock_multiplier" in prompt
    assert "sqrt(protection_periods)" in prompt
```

- [ ] **Step 2: Run prompt-routing tests and confirm RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_agent_schemas.py tests/unit/test_strategy_qualification_runner.py -q`

Expected: missing `_default_strategy_provider_factory` and formula text.

- [ ] **Step 3: Implement schema-specific factory and formula disclosure**

```python
def _default_strategy_provider_factory(profile: str, model_id: str):
    return CompatibleAPIProvider(
        ProviderConfig.from_env(profile, model_override=model_id),
        system_prompt=STRATEGY_REVIEW_SYSTEM_PROMPT,
        build_user_message=build_strategy_review_user_message,
    )
```

Set the default value of `execute_strategy_qualification`'s
`provider_factory` parameter to `_default_strategy_provider_factory`. Add the exact public controller formula to
`STRATEGY_REVIEW_SYSTEM_PROMPT` without changing controller code or bounds.

- [ ] **Step 4: Run focused tests and confirm GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_agent_schemas.py tests/unit/test_strategy_qualification_runner.py -q`

Expected: all selected tests pass without a provider call.

---

### Task 3: Replace impossible qualification histories with validated public fixtures

**Files:**
- Modify: `src/shiftmem/evaluation/strategy_qualification.py`
- Modify: `tests/unit/test_strategy_qualification.py`

**Interfaces:**
- Consumes: deterministic realized-demand levels and per-day lost-sales pressure.
- Produces: chronological public history rows satisfying inventory and observation invariants.

- [ ] **Step 1: Add failing fixture-invariant tests**

```python
def test_all_qualification_histories_are_public_and_consistent():
    allowed = {
        "day", "demand", "sales", "lost_sales", "ending_inventory",
        "order_quantity", "arrivals", "total_cost",
    }
    for case in build_strategy_qualification_cases():
        observation = case.request.observation
        history = observation["recent_history"]
        assert [row["day"] for row in history] == sorted(row["day"] for row in history)
        assert all(set(row) == allowed for row in history)
        assert all(row["sales"] + row["lost_sales"] == row["demand"] for row in history)
        assert all(row["ending_inventory"] >= 0 for row in history)
        assert all(
            row["lost_sales"] == 0 or row["ending_inventory"] == 0
            for row in history
        )
        final = history[-1]
        assert observation["last_demand"] == final["demand"]
        assert observation["last_sales"] == final["sales"]
        assert observation["inventory"] == final["ending_inventory"]

def test_lost_sales_pair_keeps_identical_realized_demand():
    cases = {case.case_id: case for case in build_strategy_qualification_cases()}
    calm = cases["lost_sales_none"].request.observation["recent_history"]
    pressured = cases["lost_sales_high"].request.observation["recent_history"]
    assert [row["demand"] for row in calm] == [row["demand"] for row in pressured]
```

- [ ] **Step 2: Run fixture tests and confirm RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_strategy_qualification.py -q`

Expected: pressured rows have positive lost sales with positive ending inventory, and final observation fields disagree with history.

- [ ] **Step 3: Implement an invariant-checked history builder**

```python
def _history(demand: int, lost_sales: int = 0) -> list[dict[str, int | float]]:
    rows = []
    for frac, day in zip(_VARIATION_FRAC, range(1, 8), strict=True):
        realized = max(0, round(demand * (1 + frac)))
        lost = min(lost_sales, realized)
        sales = realized - lost
        ending = 0 if lost else demand
        order = realized
        total_cost = order * 1.0 + ending * 0.2 + lost * 5.0
        row = {
            "day": day,
            "demand": realized,
            "sales": sales,
            "lost_sales": lost,
            "ending_inventory": ending,
            "order_quantity": order,
            "arrivals": sales,
            "total_cost": total_cost,
        }
        _validate_public_history_row(row)
        rows.append(row)
    return rows
```

Build each observation from its final row, and construct a
`StrategyProviderRequest` with a shared current strategy plus explicit trigger
reason/evidence. Keep all six case IDs and both monotonicity pairs unchanged.

- [ ] **Step 4: Run fixture and monotonicity tests and confirm GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_strategy_qualification.py -q`

Expected: all tests pass and the existing strict four-of-four assertion remains.

---

### Task 4: Preserve every attempt and make run outputs non-overwriting

**Files:**
- Create: `src/shiftmem/evaluation/qualification_run.py`
- Modify: `src/shiftmem/evaluation/strategy_qualification.py`
- Modify: `scripts/qualify_models.py`
- Modify: `tests/unit/test_strategy_qualification.py`
- Modify: `tests/unit/test_strategy_qualification_runner.py`

**Interfaces:**
- Consumes: provider response/error per attempt, config path/content, prompt text, output paths, optional run ID.
- Produces: `QualificationAttempt`, truthful summary counters, `QualificationRunMetadata`, and safe output preflight.

- [ ] **Step 1: Add failing retry-accounting tests**

```python
def test_corrected_case_preserves_failed_and_successful_attempts():
    provider = ScriptedProvider(["not-json", _good_proposal().model_dump_json()])
    outcome = run_strategy_case(
        provider, build_strategy_qualification_cases()[0], repetition=0
    )
    assert outcome.fallback_used is False
    assert len(outcome.attempts) == 2
    assert outcome.attempts[0].error is not None
    assert outcome.attempts[0].raw_output == "not-json"
    assert outcome.attempts[1].error is None

def test_summary_distinguishes_corrected_and_unresolved_failures():
    summary = summarize_strategy_qualification("model", corrected_results)
    assert summary.attempt_count == 13
    assert summary.corrected_case_count == 1
    assert summary.attempt_parse_failure_count == 1
    assert summary.unresolved_parse_failure_count == 0
```

- [ ] **Step 2: Run retry tests and confirm RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_strategy_qualification.py tests/unit/test_strategy_qualification_runner.py -q`

Expected: results have no attempt list or corrected-case counters.

- [ ] **Step 3: Implement attempt records and truthful counters**

```python
class QualificationAttempt(BaseModel):
    attempt: int = Field(ge=1, le=2)
    correction: str | None = None
    raw_output: str = ""
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0, ge=0)
    error: str | None = None


class StrategyQualificationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str
    repetition: int = Field(ge=0)
    proposal: StrategyProposal | None = None
    fallback_used: bool = False
    supplied_memory_ids: set[str] = Field(default_factory=set)
    inapplicable_memory_ids: set[str] = Field(default_factory=set)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(default=0, ge=0)
    error: str | None = None
    attempts: list[QualificationAttempt] = Field(default_factory=list)
```

Append the attempt before retrying or returning. Compute attempt-level counters
from `result.attempts`; keep qualification dependent on result count, no
fallback, no unresolved failures, valid citations, and strict four-of-four
monotonicity.

- [ ] **Step 4: Add failing overwrite and provenance tests**

```python
def test_existing_outputs_are_rejected_before_provider_creation(tmp_path):
    raw = tmp_path / "raw.jsonl"
    raw.write_text("existing\n", encoding="utf-8")
    created = 0
    with pytest.raises(FileExistsError):
        execute_strategy_qualification(
            config, raw, tmp_path / "summary.json", provider_factory=counting_factory
        )
    assert created == 0

def test_run_metadata_hashes_config_and_prompt():
    metadata = build_run_metadata(
        run_id="qual-001", schema="strategy", config_bytes=b"models: []\n",
        system_prompt="strategy prompt", builder_name="build_strategy_review_user_message",
    )
    assert metadata.run_id == "qual-001"
    assert len(metadata.config_sha256) == 64
    assert len(metadata.system_prompt_sha256) == 64
```

- [ ] **Step 5: Run provenance tests and confirm RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_strategy_qualification_runner.py -q`

Expected: existing files are overwritten or provenance helpers are missing.

- [ ] **Step 6: Implement safe preflight and run metadata**

```python
def ensure_output_paths_available(paths: Iterable[Path], overwrite: bool = False) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        raise FileExistsError(
            "qualification outputs already exist: " + ", ".join(map(str, existing))
        )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()
```

Add `QualificationRunMetadata` with run ID, UTC timestamp, schema, config and
prompt hashes, builder name, Git revision, and dirty flag. Call output preflight
before provider construction. Add CLI `--run-id` and `--overwrite`; default
documented behavior refuses replacement. Write metadata into the summary and
repeat `run_id` on every raw row.

- [ ] **Step 7: Run focused tests and confirm GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_strategy_qualification.py tests/unit/test_strategy_qualification_runner.py -q`

Expected: all selected tests pass without network access.

---

### Task 5: Record the invalid harness evidence and direction stop rule

**Files:**
- Create: `docs/v2_qualification_audit.md`
- Modify: `docs/implementation_log.md`
- Modify: `docs/experiment_protocol.md`
- Test: `tests/unit/test_validate_protocol.py`

**Interfaces:**
- Consumes: preserved artifact paths and SHA-256 values, approved repair design.
- Produces: auditable status `inconclusive_harness_invalid` and a one-rerun stop rule.

- [ ] **Step 1: Record current artifact hashes before any implementation write**

Run:

```powershell
Get-FileHash artifacts/raw_runs/model_qualification_v2.jsonl -Algorithm SHA256
Get-FileHash artifacts/aggregated/model_qualification_v2_summary.json -Algorithm SHA256
```

Expected: two stable 64-character hashes saved for the audit document.

- [ ] **Step 2: Add a failing protocol-documentation test**

```python
def test_v2_protocol_records_qualification_stop_rule():
    text = Path("docs/experiment_protocol.md").read_text(encoding="utf-8")
    assert "inconclusive_harness_invalid" in text
    assert "one newly budget-approved qualification run" in text
    assert "monotonicity_passes == 4" in text
```

- [ ] **Step 3: Run documentation test and confirm RED**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_validate_protocol.py -q`

Expected: protocol lacks the audit status and stop rule.

- [ ] **Step 4: Write audit and direction-alignment documentation**

The audit document must state:

```markdown
Status: inconclusive_harness_invalid

The 2026-07-15 run is preserved as engineering evidence but cannot qualify or
disqualify a model because the standard strategy runner used the v1 prompt,
successful correction retries hid attempt-level failures, protocol inputs were
omitted, and the lost-sales fixtures violated environment invariants.
```

Add the exact artifact hashes, 24 result rows versus approximately 48 reported
calls, the unchanged strict four-of-four gate, and the prohibition on deleting
or overwriting the files. Add the approved one-rerun stop rule to the protocol
and record the implementation decision in `docs/implementation_log.md`.

- [ ] **Step 5: Run documentation tests and confirm GREEN**

Run: `.venv\Scripts\python.exe -m pytest tests/unit/test_validate_protocol.py -q`

Expected: all selected tests pass.

---

### Task 6: Full offline verification and scope audit

**Files:**
- Verify only: all changed files
- Verify only: `configs/frozen/phase4-20260713-b99c0d3e4d27/`
- Verify only: `artifacts/raw_runs/model_qualification_v2.jsonl`
- Verify only: `artifacts/aggregated/model_qualification_v2_summary.json`

**Interfaces:**
- Consumes: completed Tasks 1-5.
- Produces: fresh evidence that the repair is network-free, protocol-conformant, regression-safe, and does not alter frozen or prior-run evidence.

- [ ] **Step 1: Run focused qualification and runtime tests**

Run:

```powershell
.venv\Scripts\python.exe -m pytest tests/unit/test_agent_schemas.py tests/unit/test_strategy_agent.py tests/integration/test_v2_episode.py tests/unit/test_strategy_qualification.py tests/unit/test_strategy_qualification_runner.py tests/unit/test_validate_protocol.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run the complete network-free suite**

Run: `.venv\Scripts\python.exe -m pytest -q`

Expected: zero failures.

- [ ] **Step 3: Run protocol and compile verification**

Run:

```powershell
.venv\Scripts\python.exe scripts/validate_protocol.py docs/experiment_protocol.md
.venv\Scripts\python.exe scripts/validate_protocol.py --v2 docs/experiment_protocol.md
.venv\Scripts\python.exe -m compileall -q src scripts
git diff --check
```

Expected: every command exits zero.

- [ ] **Step 4: Verify preserved evidence and freeze scope**

Run:

```powershell
Get-FileHash artifacts/raw_runs/model_qualification_v2.jsonl -Algorithm SHA256
Get-FileHash artifacts/aggregated/model_qualification_v2_summary.json -Algorithm SHA256
git status --short configs/frozen/phase4-20260713-b99c0d3e4d27
Get-ChildItem artifacts -Recurse -File | Select-String -Pattern 'Test-ID|Test-OOD'
```

Expected: artifact hashes equal Task 5 Step 1, frozen status is empty, and no new Test outcome artifact appears.

- [ ] **Step 5: Review the final diff against project purpose**

Confirm that changed production behavior is limited to strategy request
conformance, prompt routing, qualification fixtures, attempt evidence, and safe
output provenance. Confirm no controller formula, qualification threshold,
formal endpoint, memory algorithm, scenario manifest, or statistical design was
changed.
