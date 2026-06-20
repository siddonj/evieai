from __future__ import annotations

from app.main import MCP_ENDPOINTS


def test_orchestrator_exposes_all_local_data_sources():
    expected = {
        "sql",
        "files",
        "mail",
        "onedrive",
        "memory",
        "knowledge_base",
        "document_generation",
        "analytics",
        "postgresql",
        "dashboard",
    }

    assert expected.issubset(set(MCP_ENDPOINTS))
