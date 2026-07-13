"""Secure OpenAI-compatible chat-completions provider."""

from dataclasses import dataclass
import json
import os
from time import perf_counter
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from .base import ProviderRequest, ProviderResponse


class ProviderError(RuntimeError):
    """Sanitized provider failure safe for logs."""


class ProviderConfigurationError(ProviderError):
    """Provider environment configuration is incomplete or invalid."""


PROFILE_VARIABLES = {
    "compatible": ("MODEL_API_KEY", "MODEL_BASE_URL", "MODEL_NAME"),
    "bailian": ("BAILIAN_API_KEY", "BAILIAN_BASE_URL", "BAILIAN_MODEL_NAME"),
    "siliconflow": (
        "SILICONFLOW_API_KEY",
        "SILICONFLOW_BASE_URL",
        "SILICONFLOW_MODEL_NAME",
    ),
}


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


class HttpTransport(Protocol):
    def post(
        self,
        url: str,
        headers: dict[str, str],
        body: bytes,
        timeout: float,
    ) -> HttpResponse: ...


class UrllibTransport:
    def post(
        self,
        url: str,
        headers: dict[str, str],
        body: bytes,
        timeout: float,
    ) -> HttpResponse:
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=timeout) as response:
                return HttpResponse(response.status, response.read())
        except HTTPError as error:
            return HttpResponse(error.code, error.read())
        except (URLError, TimeoutError, OSError) as error:
            raise ProviderError(f"provider connection failed: {type(error).__name__}") from error


class ProviderConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: str = "compatible"
    api_key: SecretStr
    base_url: str
    model_name: str = Field(min_length=1)
    timeout_seconds: float = Field(default=60, gt=0)
    max_tokens: int = Field(default=512, ge=1)
    temperature: float = Field(default=0, ge=0, le=1)
    enable_thinking: bool = False

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        normalized = value.rstrip("/")
        if not normalized.startswith(("https://", "http://")):
            raise ValueError("base_url must use http or https")
        return normalized

    @property
    def endpoint(self) -> str:
        return f"{self.base_url}/chat/completions"

    @classmethod
    def from_env(
        cls,
        profile: str | None = None,
        load_file: bool = True,
        model_override: str | None = None,
    ) -> "ProviderConfig":
        if load_file:
            load_dotenv(override=False)
        resolved_profile = profile or os.getenv("MODEL_PROVIDER", "compatible")
        try:
            api_key_name, base_url_name, model_name = PROFILE_VARIABLES[
                resolved_profile
            ]
        except KeyError as error:
            raise ProviderConfigurationError(
                f"unknown provider profile: {resolved_profile}"
            ) from error
        values = {
            "profile": resolved_profile,
            "api_key": os.getenv(api_key_name, ""),
            "base_url": os.getenv(base_url_name, ""),
            "model_name": model_override or os.getenv(model_name, ""),
            "timeout_seconds": os.getenv("MODEL_TIMEOUT_SECONDS", "60"),
            "max_tokens": os.getenv("MODEL_MAX_TOKENS", "512"),
            "temperature": os.getenv("MODEL_TEMPERATURE", "0"),
            "enable_thinking": os.getenv("MODEL_ENABLE_THINKING", "false"),
        }
        missing = [
            name
            for name, value in zip(
                (api_key_name, base_url_name, model_name),
                (
                    values["api_key"],
                    values["base_url"],
                    values["model_name"],
                ),
                strict=True,
            )
            if not value
        ]
        if missing:
            raise ProviderConfigurationError(
                f"missing provider environment variables: {', '.join(missing)}"
            )
        try:
            return cls(**values)
        except ValueError as error:
            raise ProviderConfigurationError("provider environment is invalid") from error


SYSTEM_INSTRUCTION = """Return only one JSON object with this exact schema:
{"order_quantity": non-negative integer, "supplier_id": "standard",
 "used_memory_ids": array of supplied memory IDs, "confidence": number from 0 to 1,
 "reason": non-empty string}. Do not invent memory IDs or add fields."""


class CompatibleAPIProvider:
    def __init__(
        self,
        config: ProviderConfig,
        transport: HttpTransport | None = None,
    ) -> None:
        self.config = config
        self.transport = transport or UrllibTransport()

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        payload = {
            "model": self.config.model_name,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_INSTRUCTION},
                {
                    "role": "user",
                    "content": json.dumps(request.model_dump(), ensure_ascii=False, sort_keys=True),
                },
            ],
        }
        if self.config.profile in {"bailian", "siliconflow"}:
            payload["enable_thinking"] = self.config.enable_thinking
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.config.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        started = perf_counter()
        response = self.transport.post(
            self.config.endpoint,
            headers,
            body,
            self.config.timeout_seconds,
        )
        latency_ms = (perf_counter() - started) * 1000
        if not 200 <= response.status < 300:
            raise ProviderError(f"provider returned HTTP {response.status}")
        try:
            envelope = json.loads(response.body)
            content = envelope["choices"][0]["message"]["content"]
            if not isinstance(content, str) or not content:
                raise ValueError("content is missing")
            usage = envelope.get("usage", {})
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
        except (json.JSONDecodeError, KeyError, IndexError, TypeError, ValueError) as error:
            raise ProviderError("provider returned a malformed response envelope") from error
        return ProviderResponse(
            text=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )
