"""Unit tests for LLM provider runtime/config selection."""

import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "orchestrator"))

# Keep tests runnable in bare environments that do not have the openai package installed.
if "openai" not in sys.modules:
    sys.modules["openai"] = types.SimpleNamespace(AsyncAzureOpenAI=object, AsyncOpenAI=object)

from app.llm_provider import LLMConfigError, get_llm_provider_status_from_env, get_llm_runtime_from_env


class DummyClient:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def clear_llm_env(monkeypatch):
    for name in [
        "LLM_PROVIDER",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_DEPLOYMENT",
        "AZURE_OPENAI_API_VERSION",
        "OBOT_BASE_URL",
        "OBOT_API_KEY",
        "OBOT_API_REQUIRED",
        "OBOT_MODEL",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_runtime_defaults_to_azure(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "test-key")
    monkeypatch.setattr("app.llm_provider.AsyncAzureOpenAI", DummyClient)

    runtime = get_llm_runtime_from_env()

    assert runtime.provider == "azure-openai"
    assert runtime.model == "gpt-4o"
    assert isinstance(runtime.client, DummyClient)
    assert runtime.client.kwargs["azure_endpoint"] == "https://example.openai.azure.com"


def test_runtime_uses_obot_alias(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "obot")
    monkeypatch.setenv("OBOT_BASE_URL", "https://obot.example.com/v1")
    monkeypatch.setenv("OBOT_API_KEY", "obot-key")
    monkeypatch.setenv("OBOT_MODEL", "obot-large")
    monkeypatch.setattr("app.llm_provider.AsyncOpenAI", DummyClient)

    runtime = get_llm_runtime_from_env()

    assert runtime.provider == "obot-ai"
    assert runtime.model == "obot-large"
    assert isinstance(runtime.client, DummyClient)
    assert runtime.client.kwargs["base_url"] == "https://obot.example.com/v1"


def test_runtime_raises_on_missing_required_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "obot-ai")
    monkeypatch.setenv("OBOT_BASE_URL", "https://obot.example.com/v1")

    with pytest.raises(LLMConfigError, match="OBOT_API_KEY"):
        get_llm_runtime_from_env()


def test_runtime_raises_on_unsupported_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "invalid-provider")

    with pytest.raises(LLMConfigError, match="Unsupported LLM_PROVIDER"):
        get_llm_runtime_from_env()


def test_status_reports_missing_azure_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "azure-openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")

    status = get_llm_provider_status_from_env()

    assert status.provider == "azure-openai"
    assert status.supported is True
    assert status.configured is False
    assert status.missing_env_vars == ["AZURE_OPENAI_API_KEY"]


def test_status_reports_unsupported_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")

    status = get_llm_provider_status_from_env()

    assert status.provider == "nope"
    assert status.supported is False
    assert status.configured is False
    assert status.error is not None


def test_runtime_allows_obot_without_api_key_when_flag_disabled(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "obot-ai")
    monkeypatch.setenv("OBOT_BASE_URL", "https://obot.example.com/v1")
    monkeypatch.setenv("OBOT_API_REQUIRED", "false")
    monkeypatch.setattr("app.llm_provider.AsyncOpenAI", DummyClient)

    runtime = get_llm_runtime_from_env()

    assert runtime.provider == "obot-ai"
    assert runtime.client.kwargs["api_key"] == "local-no-auth"


def test_status_ignores_missing_obot_api_key_when_flag_disabled(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "obot-ai")
    monkeypatch.setenv("OBOT_BASE_URL", "https://obot.example.com/v1")
    monkeypatch.setenv("OBOT_API_REQUIRED", "false")

    status = get_llm_provider_status_from_env()

    assert status.provider == "obot-ai"
    assert status.supported is True
    assert status.configured is True
    assert status.missing_env_vars == []
