from __future__ import annotations

from app.main import admin_mcp_config


def test_admin_mcp_config_includes_full_source_registry():
    body = admin_mcp_config()
    keys = {server["key"] for server in body["servers"]}

    assert {
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
    }.issubset(keys)
