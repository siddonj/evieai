"""Test fixtures for orchestrator and MCP server tests."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "orchestrator"))


@pytest.fixture
def mock_openai(monkeypatch):
    """Mock Azure OpenAI to return a simple text response without tool calls."""
    mock_choice = MagicMock()
    mock_choice.finish_reason = "stop"
    mock_choice.message = MagicMock(content="Here is your answer.", tool_calls=None)

    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    monkeypatch.setattr("app.main.AsyncAzureOpenAI", lambda **kw: mock_client)
    return mock_client
