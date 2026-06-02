from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from openai import AsyncAzureOpenAI


class LLMConfigError(RuntimeError):
    """Raised when LLM provider configuration is invalid."""


@dataclass(frozen=True)
class LLMRuntime:
    provider: str
    model: str
    client: Any


@dataclass(frozen=True)
class LLMProviderStatus:
    provider: str
    supported: bool
    configured: bool
    model: str
    missing_env_vars: list[str]
    endpoint: str | None
    error: str | None = None


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise LLMConfigError(f"Missing required env var: {name}")
    return value


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def get_llm_runtime_from_env() -> LLMRuntime:
    provider = os.getenv("LLM_PROVIDER", "azure-openai").strip().lower()

    if provider in {"azure", "azure-openai"}:
        endpoint = _required_env("AZURE_OPENAI_ENDPOINT")
        api_key = _required_env("AZURE_OPENAI_API_KEY")
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o").strip() or "gpt-4o"
        api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01").strip() or "2024-02-01"
        client = AsyncAzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        return LLMRuntime(provider="azure-openai", model=model, client=client)

    raise LLMConfigError(
        f"Unsupported LLM_PROVIDER '{provider}'. Supported values: azure-openai"
    )


def get_llm_provider_status_from_env() -> LLMProviderStatus:
    provider_raw = os.getenv("LLM_PROVIDER", "azure-openai").strip().lower()

    if provider_raw in {"azure", "azure-openai"}:
        model = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o").strip() or "gpt-4o"
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip() or None
        missing = [
            name
            for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY")
            if not os.getenv(name, "").strip()
        ]
        return LLMProviderStatus(
            provider="azure-openai",
            supported=True,
            configured=len(missing) == 0,
            model=model,
            missing_env_vars=missing,
            endpoint=endpoint,
            error=None,
        )

    return LLMProviderStatus(
        provider=provider_raw,
        supported=False,
        configured=False,
        model="",
        missing_env_vars=[],
        endpoint=None,
        error=f"Unsupported LLM_PROVIDER '{provider_raw}'. Supported values: azure-openai",
    )
