# Named API Profiles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Configure Bailian and SiliconFlow simultaneously, select either provider without editing `.env`, and override the model per run while keeping keys secret.

**Architecture:** Extend the existing OpenAI-compatible provider with named environment profiles and shared generation settings. Keep one HTTP implementation, resolve only the selected profile, and expose provider/model selection through the existing episode CLI. Preserve the generic `compatible` profile for backward compatibility.

**Tech Stack:** Python 3.11+, Pydantic 2, python-dotenv, urllib, argparse, pytest

## Global Constraints

- API keys remain blank in `.env.example` and are never logged.
- The ignored `.env` contains complete non-secret defaults and blank key slots.
- Bailian endpoint: `https://dashscope.aliyuncs.com/compatible-mode/v1`.
- SiliconFlow endpoint: `https://api.siliconflow.cn/v1`.
- Default Bailian model: `qwen3.5-flash-2026-02-23`.
- Default SiliconFlow model: `deepseek-ai/DeepSeek-V3.2`.
- Default temperature is `0`, maximum output is `512` tokens, timeout is `60` seconds, and named profiles disable thinking.
- Only the selected profile's key is required.
- Automated tests never call a live API.

---

### Task 1: Named provider configuration and request parameters

**Files:**
- Modify: `tests/unit/test_compatible_api_provider.py`
- Modify: `src/shiftmem/providers/compatible_api.py`

**Interfaces:**
- Consumes: `ProviderConfig.from_env(load_file: bool = True)` and `CompatibleAPIProvider.generate(request)`.
- Produces: `ProviderConfig.from_env(profile: str = "compatible", load_file: bool = True, model_override: str | None = None) -> ProviderConfig`; configuration fields `profile`, `temperature`, `max_tokens`, and `enable_thinking`.

- [ ] **Step 1: Write failing tests for independent named profiles**

Add tests that set only `BAILIAN_API_KEY`, `BAILIAN_BASE_URL`, and `BAILIAN_MODEL_NAME`, then assert `ProviderConfig.from_env("bailian", load_file=False)` loads that endpoint even when every `SILICONFLOW_*` value is absent. Add the mirror test for SiliconFlow. Add a missing-key test asserting the sanitized error names `BAILIAN_API_KEY` without containing any other environment value.

```python
def test_bailian_profile_only_requires_bailian_values(monkeypatch) -> None:
    monkeypatch.setenv("BAILIAN_API_KEY", "bailian-secret")
    monkeypatch.setenv("BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    monkeypatch.setenv("BAILIAN_MODEL_NAME", "qwen3.5-flash-2026-02-23")
    for name in ("SILICONFLOW_API_KEY", "SILICONFLOW_BASE_URL", "SILICONFLOW_MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)

    config = ProviderConfig.from_env("bailian", load_file=False)

    assert config.profile == "bailian"
    assert config.model_name == "qwen3.5-flash-2026-02-23"
    assert config.endpoint.endswith("/chat/completions")
```

- [ ] **Step 2: Run named-profile tests and verify RED**

Run: `python -m pytest tests/unit/test_compatible_api_provider.py -q`

Expected: FAIL because `from_env` does not accept a profile and `ProviderConfig` has no `profile` field.

- [ ] **Step 3: Implement named environment resolution**

Add a profile-to-variable mapping for `compatible`, `bailian`, and `siliconflow`. Resolve exactly one profile, validate the profile name, load shared `MODEL_TIMEOUT_SECONDS`, `MODEL_MAX_TOKENS`, `MODEL_TEMPERATURE`, and `MODEL_ENABLE_THINKING`, and apply `model_override` after environment resolution. Pydantic must parse and validate numeric/boolean strings. Error text lists missing variable names only.

```python
PROFILE_VARIABLES = {
    "compatible": ("MODEL_API_KEY", "MODEL_BASE_URL", "MODEL_NAME"),
    "bailian": ("BAILIAN_API_KEY", "BAILIAN_BASE_URL", "BAILIAN_MODEL_NAME"),
    "siliconflow": (
        "SILICONFLOW_API_KEY",
        "SILICONFLOW_BASE_URL",
        "SILICONFLOW_MODEL_NAME",
    ),
}
```

- [ ] **Step 4: Write failing tests for generation settings and override precedence**

Assert shared environment values load as typed fields, `model_override` wins over the profile default, invalid values fail before transport, named requests include `max_tokens` and `enable_thinking`, and generic requests omit `enable_thinking`.

```python
def test_model_override_wins_over_profile_default(monkeypatch) -> None:
    monkeypatch.setenv("SILICONFLOW_API_KEY", "key")
    monkeypatch.setenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("SILICONFLOW_MODEL_NAME", "deepseek-ai/DeepSeek-V3.2")

    config = ProviderConfig.from_env(
        "siliconflow", load_file=False, model_override="Pro/zai-org/GLM-5.1"
    )

    assert config.model_name == "Pro/zai-org/GLM-5.1"
```

- [ ] **Step 5: Run new setting tests and verify RED**

Run: `python -m pytest tests/unit/test_compatible_api_provider.py -q`

Expected: FAIL because the settings are not yet represented in the request.

- [ ] **Step 6: Implement request settings**

Use `config.temperature` and `config.max_tokens` in the payload. Include `enable_thinking` only when `config.profile` is `bailian` or `siliconflow`. Retain `response_format={"type":"json_object"}` and ensure the system message contains the literal word `JSON`.

- [ ] **Step 7: Verify Task 1 GREEN**

Run: `python -m pytest tests/unit/test_compatible_api_provider.py -q`

Expected: all tests in the file PASS.

### Task 2: CLI selection and model override

**Files:**
- Modify: `tests/unit/test_agent_provider_selection.py`
- Modify: `scripts/run_agent_episode.py`

**Interfaces:**
- Consumes: `ProviderConfig.from_env(profile, model_override=...)` from Task 1.
- Produces: `make_provider(name: str, target_inventory: int, model_name: str | None = None)` and CLI choices `deterministic`, `compatible`, `bailian`, `siliconflow` plus `--model-name`.

- [ ] **Step 1: Write failing provider-selection tests**

Patch `ProviderConfig.from_env`, call `make_provider("bailian", 60, "qwen-test")` and `make_provider("siliconflow", 60, "ds-test")`, and assert the selected profile and override are forwarded. Retain the deterministic and unknown-provider tests.

```python
def test_named_provider_forwards_profile_and_model(monkeypatch) -> None:
    captured = {}

    def fake_from_env(profile="compatible", load_file=True, model_override=None):
        captured.update(profile=profile, model_override=model_override)
        return ProviderConfig(api_key="key", base_url="https://example.test/v1", model_name="m")

    monkeypatch.setattr(ProviderConfig, "from_env", fake_from_env)
    make_provider("bailian", 60, "qwen-test")
    assert captured == {"profile": "bailian", "model_override": "qwen-test"}
```

- [ ] **Step 2: Run CLI selection tests and verify RED**

Run: `python -m pytest tests/unit/test_agent_provider_selection.py -q`

Expected: FAIL because `make_provider` has no model argument and named choices are unknown.

- [ ] **Step 3: Implement CLI named selection**

For any of `compatible`, `bailian`, or `siliconflow`, construct `CompatibleAPIProvider(ProviderConfig.from_env(name, model_override=model_name))`. Add named provider choices and optional `--model-name`; keep `deterministic` as the CLI default so ordinary offline commands never spend API credit accidentally.

- [ ] **Step 4: Verify Task 2 GREEN**

Run: `python -m pytest tests/unit/test_agent_provider_selection.py tests/unit/test_compatible_api_provider.py -q`

Expected: all selected tests PASS.

### Task 3: Complete local environment template and documentation

**Files:**
- Modify: `.env.example`
- Create (ignored): `.env`
- Modify: `README.md`
- Modify: `docs/implementation_log.md`

**Interfaces:**
- Consumes: named CLI options from Task 2.
- Produces: a safe local configuration requiring the user to fill only `BAILIAN_API_KEY` and `SILICONFLOW_API_KEY`.

- [ ] **Step 1: Replace the environment template and create ignored local configuration**

Write the exact non-secret settings from the approved design into both files, with blank API key values. Add comments listing `qwen3.7-plus-2026-05-26` and `Pro/zai-org/GLM-5.1` as optional overrides without activating them.

- [ ] **Step 2: Document safe smoke commands**

Add one ten-day command for each provider:

```powershell
python scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory vector --provider bailian --max-days 10 --output artifacts/raw_runs/bailian_smoke.json
python scripts/run_agent_episode.py --config configs/environments/stable.yaml --memory vector --provider siliconflow --model-name Pro/zai-org/GLM-5.1 --max-days 10 --output artifacts/raw_runs/siliconflow_glm_smoke.json
```

State explicitly that no live call should be made until the matching key has been filled and account billing/quotas are understood.

- [ ] **Step 3: Run focused and complete verification**

Run:

```powershell
python -m pytest tests/unit/test_compatible_api_provider.py tests/unit/test_agent_provider_selection.py -q
python -m pytest -q
python -m compileall -q src scripts
git check-ignore .env
git diff --check
```

Expected: focused tests PASS, full suite has zero failures, compilation exits `0`, `.env` is reported as ignored, and diff check exits `0`.

- [ ] **Step 4: Scan tracked and untracked repository text for populated keys**

Use a PowerShell `Select-String` scan that excludes `.git` and ignored `.env`; verify no committed/example assignment has a non-empty value for `*_API_KEY`.

- [ ] **Step 5: Review the final diff**

Run `git status --short` and `git diff --stat`, confirm the pre-existing compatible-provider work remains present, `.env` is absent from status, and no unrelated file was changed.
