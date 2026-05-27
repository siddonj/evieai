"""Smoke tests — run against deployed orchestrator.

Usage:
    pytest tests/smoke/ -v --base-url https://api.resiq.co
    pytest tests/smoke/ -v --base-url http://localhost:8000
"""

import os

import httpx
import pytest


def _base_url():
    return os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8000")


@pytest.mark.asyncio
async def test_health():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_base_url()}/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "connectors" in body
        assert "runtime" in body["connectors"]
        assert "health" in body["connectors"]


@pytest.mark.asyncio
async def test_ready():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_base_url()}/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "dependencies" in data


@pytest.mark.asyncio
async def test_chat_basic():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base_url()}/chat",
            json={"message": "Hello", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0


@pytest.mark.asyncio
async def test_chat_with_tool_calls():
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{_base_url()}/chat",
            json={"message": "Show me the sales pipeline", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        # Should have tool calls or MCP results
        assert "tool_calls" in data
        assert "mcp_results" in data


@pytest.mark.asyncio
async def test_openapi_schema():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_base_url()}/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "orchestrator"
        assert "/chat" in schema["paths"]


@pytest.mark.asyncio
async def test_download_endpoint_404():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_base_url()}/download/nonexistent/file.txt")
        assert resp.status_code == 404
