# Compatible API Provider Design

## Goal

Connect the Phase 2 structured Agent pipeline to an OpenAI-compatible chat-completions endpoint without hard-coding a vendor, model, URL, or credential. Keep all tests offline through an injected HTTP transport.

## Configuration and security

Load `MODEL_API_KEY`, `MODEL_BASE_URL`, and `MODEL_NAME` from the process environment or local `.env`. Store the key as a secret value, never include it in logs, exceptions, decision records, or object representations, and fail before network access when configuration is incomplete.

## Request and response

POST JSON to `<MODEL_BASE_URL>/chat/completions` with the configured model, low temperature, system instructions defining the exact `AgentDecision` schema, observation and retrieved memory context, and JSON-object response mode. Return only the model message content to the existing `StructuredAgent`; provider usage and measured latency populate `ProviderResponse`.

## Error handling

Use a replaceable transport protocol. Convert non-2xx status, malformed API envelopes, missing choices/content, timeouts, and connection failures into sanitized `ProviderError` messages. Agent-level invalid decision JSON still follows the existing one-retry-then-fallback policy.

## CPU-only environment

No local runtime is installed, so this phase does not add model weights or a CPU inference dependency. The compatible provider is selectable from the existing CLI. Deterministic mode remains the default for tests and offline development.

## Validation

- Unit tests use a fake transport and make no network calls.
- Authorization headers are sent but never logged.
- Usage, latency, request schema, retry, and fallback flow are verified.
- A missing `.env` or incomplete configuration produces an actionable error without exposing secret data.
