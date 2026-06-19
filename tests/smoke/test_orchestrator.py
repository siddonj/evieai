"""Smoke tests — run against deployed orchestrator.

Usage:
    ORCHESTRATOR_BASE_URL=https://api.resiq.co pytest tests/smoke/ -v
    ORCHESTRATOR_BASE_URL=http://localhost:8000 pytest tests/smoke/ -v
"""

import json
import os

import httpx
import pytest


def _base_url():
    return os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8000")


def _extract_sse_payload(resp: httpx.Response) -> dict:
    """Parse chat SSE stream and return the final done payload."""
    done_payload: dict = {}
    for line in resp.text.splitlines():
        if not line.startswith("data: "):
            continue
        raw = line[6:].strip()
        if not raw:
            continue
        try:
            event = json.loads(raw)
        except Exception:
            continue
        if isinstance(event, dict) and event.get("type") == "done":
            done_payload = event
    return done_payload


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
        assert "reliability" in body
        assert "run_success_rate_last_200" in body["reliability"]


@pytest.mark.asyncio
async def test_ready():
    async with httpx.AsyncClient(timeout=35) as client:
        resp = await client.get(f"{_base_url()}/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert "dependencies" in data


@pytest.mark.asyncio
async def test_chat_basic():
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"{_base_url()}/chat",
            json={"message": "Hello", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in (resp.headers.get("content-type") or "")
        data = _extract_sse_payload(resp)
        assert "reply" in data
        assert isinstance(data["reply"], str)
        assert len(data["reply"]) > 0


@pytest.mark.asyncio
async def test_chat_with_tool_calls():
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"{_base_url()}/chat",
            json={"message": "Show me the sales pipeline", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        assert "text/event-stream" in (resp.headers.get("content-type") or "")
        data = _extract_sse_payload(resp)
        assert "reply" in data
        # Should have tool calls or MCP results
        assert "tool_calls" in data
        assert "mcp_results" in data


@pytest.mark.asyncio
async def test_chat_with_tool_calls_includes_work_packet():
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"{_base_url()}/chat",
            json={"message": "Show me the sales pipeline", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        data = _extract_sse_payload(resp)
        assert "work_packet" in data
        assert "answer" in data["work_packet"]
        assert "reconciliation" in data["work_packet"]
        assert "evidence" in data["work_packet"]


@pytest.mark.asyncio
async def test_chat_batch_includes_work_packet():
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"{_base_url()}/chat/batch",
            json={"message": "Show me the sales pipeline", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "work_packet" in data
        assert "answer" in data["work_packet"]
        assert "reconciliation" in data["work_packet"]
        assert "evidence" in data["work_packet"]


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


@pytest.mark.asyncio
async def test_dashboard_performance_populated():
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{_base_url()}/dashboard/performance")
        assert resp.status_code == 200

        body = resp.json()
        assert "generated_at" in body

        overview = body.get("overview") or {}
        pipeline = body.get("pipeline") or {}
        activities = body.get("activities") or {}
        top_props = body.get("top_properties_by_noi") or []

        assert overview.get("portfolio_value", 0) > 0
        assert overview.get("pipeline_value", 0) > 0

        # Regression guard: pipeline must be populated, not zeroed.
        assert pipeline.get("pipeline_total", 0) > 0
        assert pipeline.get("commission_pipeline", 0) > 0
        assert len(pipeline.get("by_stage") or {}) > 0

        assert activities.get("upcoming_count", 0) >= 0
        assert len(top_props) > 0
