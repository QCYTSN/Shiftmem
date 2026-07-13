# Named API Profiles Design

## Goal

Configure Alibaba Cloud Model Studio (Bailian) and SiliconFlow at the same time so a local experiment can switch providers without editing credentials or endpoint values between runs. The user will only need to fill the two API keys in the ignored `.env` file.

## Configuration layout

Both `.env.example` and the ignored local `.env` will contain the same non-secret defaults. API key values remain empty.

```dotenv
MODEL_PROVIDER=bailian
MODEL_TIMEOUT_SECONDS=60
MODEL_MAX_TOKENS=512
MODEL_TEMPERATURE=0
MODEL_ENABLE_THINKING=false

BAILIAN_API_KEY=
BAILIAN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
BAILIAN_MODEL_NAME=qwen3.5-flash-2026-02-23

SILICONFLOW_API_KEY=
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL_NAME=deepseek-ai/DeepSeek-V3.2
```

The default Bailian model is a low-cost, version-pinned smoke-test model. Formal Qwen experiments can override it with `qwen3.7-plus-2026-05-26`. The default SiliconFlow model is the economical cross-family comparison. Additional controlled comparisons can override it with `Pro/zai-org/GLM-4.7`; the more expensive `Pro/zai-org/GLM-5.1` is reserved for small confirmatory runs.

Secrets stay only in `.env`. Model identifiers, endpoints, and non-secret generation settings are duplicated in `.env.example` so repository users can reproduce the configuration shape without receiving credentials.

## Provider selection

The episode CLI will accept `deterministic`, `bailian`, `siliconflow`, and the existing generic `compatible` provider. Named providers load their matching prefixed variables. `compatible` remains available for backward compatibility and continues to read `MODEL_API_KEY`, `MODEL_BASE_URL`, and `MODEL_NAME` when explicitly selected.

An optional `--model-name` argument overrides only the selected profile's default model for that invocation. It never changes `.env`. This supports fixed-model research runs without duplicating or moving API keys.

## Request behavior

All remote profiles use the existing OpenAI-compatible `/chat/completions` transport. Requests include:

- `response_format={"type":"json_object"}`;
- an explicit JSON instruction in the system message;
- a configurable temperature, defaulting to `0`;
- a configurable maximum output of 512 tokens;
- non-thinking mode by default where the endpoint accepts the `enable_thinking` parameter;
- the existing 60-second timeout.

Because provider-specific optional fields are not universally accepted, `enable_thinking` will only be sent for the two known named profiles. Generic `compatible` requests retain the portable field set.

## Validation and errors

Only the selected provider's key is required. For example, a Bailian run must not fail because the SiliconFlow key is still blank. Configuration errors identify missing variable names but never include key contents. Numeric settings are validated before any network request.

The existing structured-agent retry and fallback behavior remains unchanged. Malformed JSON, incomplete response envelopes, HTTP failures, and timeouts continue to be sanitized and logged without secrets.

## Tests

Tests will be written before implementation and will cover:

1. loading each named profile independently;
2. requiring only the selected profile's API key;
3. model override precedence;
4. shared numeric settings and validation;
5. named-provider request parameters;
6. backward compatibility for the generic profile;
7. CLI provider selection;
8. key redaction and sanitized failures.

No live API request belongs in the automated test suite. After the user fills a key, a separate ten-day smoke run will validate the real endpoint, JSON response, token counts, latency, retry behavior, and fallback rate.

## Scope

This change configures remote model access and provider switching only. It does not start large experiments, purchase services, change memory algorithms, or place generated results under version control.
