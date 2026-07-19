import json

import pytest

from shiftmem.providers.base import ProviderRequest
from shiftmem.providers.compatible_api import (
    CompatibleAPIProvider,
    HttpResponse,
    ProviderConfig,
    ProviderConfigurationError,
    ProviderError,
    TOKEN_ACCOUNTING_OVERHEAD,
)


class FakeTransport:
    def __init__(self, response: HttpResponse) -> None:
        self.response = response
        self.calls: list[dict] = []

    def post(self, url, headers, body, timeout):
        self.calls.append(
            {"url": url, "headers": headers, "body": body, "timeout": timeout}
        )
        return self.response


def request() -> ProviderRequest:
    return ProviderRequest(
        observation={"day": 1, "inventory": 10, "pipeline_inventory": 5},
        memory=[{"memory_id": "m1", "text": "demand increased"}],
    )


def test_config_loads_environment_and_redacts_key(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_API_KEY", "super-secret")
    monkeypatch.setenv("MODEL_BASE_URL", "https://example.test/v1/")
    monkeypatch.setenv("MODEL_NAME", "small-model")
    config = ProviderConfig.from_env("compatible", load_file=False)
    assert config.endpoint == "https://example.test/v1/chat/completions"
    assert "super-secret" not in repr(config)


def test_missing_configuration_fails_before_transport(monkeypatch) -> None:
    for name in ("MODEL_API_KEY", "MODEL_BASE_URL", "MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ProviderConfigurationError):
        ProviderConfig.from_env("compatible", load_file=False)


def test_bailian_profile_only_requires_bailian_values(monkeypatch) -> None:
    monkeypatch.setenv("BAILIAN_API_KEY", "bailian-secret")
    monkeypatch.setenv(
        "BAILIAN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    monkeypatch.setenv("BAILIAN_MODEL_NAME", "qwen3.5-flash-2026-02-23")
    for name in (
        "SILICONFLOW_API_KEY",
        "SILICONFLOW_BASE_URL",
        "SILICONFLOW_MODEL_NAME",
    ):
        monkeypatch.delenv(name, raising=False)

    config = ProviderConfig.from_env("bailian", load_file=False)

    assert config.profile == "bailian"
    assert config.model_name == "qwen3.5-flash-2026-02-23"
    assert config.endpoint == (
        "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    )


def test_siliconflow_profile_only_requires_siliconflow_values(monkeypatch) -> None:
    monkeypatch.setenv("SILICONFLOW_API_KEY", "siliconflow-secret")
    monkeypatch.setenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("SILICONFLOW_MODEL_NAME", "deepseek-ai/DeepSeek-V3.2")
    for name in ("BAILIAN_API_KEY", "BAILIAN_BASE_URL", "BAILIAN_MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)

    config = ProviderConfig.from_env("siliconflow", load_file=False)

    assert config.profile == "siliconflow"
    assert config.model_name == "deepseek-ai/DeepSeek-V3.2"


def test_default_profile_can_be_selected_by_environment(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_PROVIDER", "bailian")
    monkeypatch.setenv("BAILIAN_API_KEY", "key")
    monkeypatch.setenv("BAILIAN_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("BAILIAN_MODEL_NAME", "qwen")
    for name in ("MODEL_API_KEY", "MODEL_BASE_URL", "MODEL_NAME"):
        monkeypatch.delenv(name, raising=False)

    config = ProviderConfig.from_env(load_file=False)

    assert config.profile == "bailian"


def test_missing_named_profile_value_identifies_variable_without_secret(
    monkeypatch,
) -> None:
    monkeypatch.setenv("BAILIAN_BASE_URL", "https://secret-endpoint.example/v1")
    monkeypatch.setenv("BAILIAN_MODEL_NAME", "qwen-secret-name")
    monkeypatch.delenv("BAILIAN_API_KEY", raising=False)

    with pytest.raises(ProviderConfigurationError) as captured:
        ProviderConfig.from_env("bailian", load_file=False)

    message = str(captured.value)
    assert "BAILIAN_API_KEY" in message
    assert "secret-endpoint" not in message
    assert "qwen-secret-name" not in message


def test_named_profile_loads_shared_settings_and_model_override(monkeypatch) -> None:
    monkeypatch.setenv("SILICONFLOW_API_KEY", "key")
    monkeypatch.setenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")
    monkeypatch.setenv("SILICONFLOW_MODEL_NAME", "deepseek-ai/DeepSeek-V3.2")
    monkeypatch.setenv("MODEL_TIMEOUT_SECONDS", "30")
    monkeypatch.setenv("MODEL_MAX_TOKENS", "256")
    monkeypatch.setenv("MODEL_TEMPERATURE", "0.1")
    monkeypatch.setenv("MODEL_ENABLE_THINKING", "false")

    config = ProviderConfig.from_env(
        "siliconflow",
        load_file=False,
        model_override="Pro/zai-org/GLM-5.1",
    )

    assert config.model_name == "Pro/zai-org/GLM-5.1"
    assert config.timeout_seconds == 30
    assert config.max_tokens == 256
    assert config.temperature == 0.1
    assert config.enable_thinking is False


def test_invalid_shared_generation_setting_is_rejected(monkeypatch) -> None:
    monkeypatch.setenv("BAILIAN_API_KEY", "key")
    monkeypatch.setenv("BAILIAN_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("BAILIAN_MODEL_NAME", "qwen")
    monkeypatch.setenv("MODEL_MAX_TOKENS", "0")

    with pytest.raises(ProviderConfigurationError):
        ProviderConfig.from_env("bailian", load_file=False)


def test_provider_builds_request_and_extracts_usage() -> None:
    envelope = {
        "choices": [{"message": {"content": '{"order_quantity": 12}'}}],
        "usage": {"prompt_tokens": 101, "completion_tokens": 17},
    }
    transport = FakeTransport(HttpResponse(200, json.dumps(envelope).encode()))
    provider = CompatibleAPIProvider(
        ProviderConfig(
            api_key="super-secret",
            base_url="https://example.test/v1",
            model_name="small-model",
        ),
        transport=transport,
    )
    response = provider.generate(request())
    assert response.text == '{"order_quantity": 12}'
    assert response.input_tokens == 101
    assert response.output_tokens == 17
    call = transport.calls[0]
    assert call["headers"]["Authorization"] == "Bearer super-secret"
    payload = json.loads(call["body"])
    assert payload["model"] == "small-model"
    assert payload["temperature"] == 0
    assert payload["max_tokens"] == 512
    assert payload["response_format"] == {"type": "json_object"}
    assert "enable_thinking" not in payload
    assert "m1" in payload["messages"][1]["content"]


def test_inventory_prompt_defines_objective_and_public_information_rules() -> None:
    envelope = {
        "choices": [{"message": {"content": '{"order_quantity": 0}'}}],
        "usage": {},
    }
    transport = FakeTransport(HttpResponse(200, json.dumps(envelope).encode()))
    provider = CompatibleAPIProvider(
        ProviderConfig(
            api_key="key",
            base_url="https://example.test/v1",
            model_name="model",
        ),
        transport=transport,
    )

    provider.generate(request())

    payload = json.loads(transport.calls[0]["body"])
    system_prompt = payload["messages"][0]["content"]
    for required in (
        "purchase",
        "holding",
        "stockout",
        "pipeline",
        "recent_history",
        "fallible evidence",
        "hidden",
        "200 characters",
        "JSON",
    ):
        assert required in system_prompt


def test_named_provider_sends_non_thinking_generation_settings() -> None:
    envelope = {
        "choices": [{"message": {"content": '{"order_quantity": 12}'}}],
        "usage": {},
    }
    transport = FakeTransport(HttpResponse(200, json.dumps(envelope).encode()))
    provider = CompatibleAPIProvider(
        ProviderConfig(
            profile="bailian",
            api_key="key",
            base_url="https://example.test/v1",
            model_name="qwen",
            temperature=0.2,
            max_tokens=300,
            enable_thinking=False,
        ),
        transport=transport,
    )

    provider.generate(request())

    payload = json.loads(transport.calls[0]["body"])
    assert payload["temperature"] == 0.2
    assert payload["max_tokens"] == 300
    assert payload["enable_thinking"] is False


def test_preflight_token_bound_covers_exact_request_and_frozen_output_cap() -> None:
    envelope = {
        "choices": [{"message": {"content": '{"order_quantity": 12}'}}],
        "usage": {},
    }
    transport = FakeTransport(HttpResponse(200, json.dumps(envelope).encode()))
    provider = CompatibleAPIProvider(
        ProviderConfig(
            api_key="key",
            base_url="https://example.test/v1",
            model_name="model",
            max_tokens=321,
        ),
        transport=transport,
    )
    input_bound, output_bound = provider.token_budget_upper_bounds(request())
    provider.generate(request())

    assert input_bound == len(transport.calls[0]["body"]) + TOKEN_ACCOUNTING_OVERHEAD
    assert output_bound == 321


def test_http_error_is_sanitized() -> None:
    transport = FakeTransport(HttpResponse(401, b'{"error":"super-secret rejected"}'))
    provider = CompatibleAPIProvider(
        ProviderConfig(api_key="super-secret", base_url="https://example.test/v1", model_name="m"),
        transport=transport,
    )
    with pytest.raises(ProviderError) as captured:
        provider.generate(request())
    assert "401" in str(captured.value)
    assert "super-secret" not in str(captured.value)


@pytest.mark.parametrize(
    "body",
    [b"not-json", b"{}", b'{"choices": []}', b'{"choices":[{"message":{}}]}'],
)
def test_malformed_response_envelope_is_rejected(body: bytes) -> None:
    provider = CompatibleAPIProvider(
        ProviderConfig(api_key="key", base_url="https://example.test/v1", model_name="m"),
        transport=FakeTransport(HttpResponse(200, body)),
    )
    with pytest.raises(ProviderError):
        provider.generate(request())
