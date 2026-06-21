from __future__ import annotations

import pytest
from app.main import _forced_source_plan


@pytest.mark.parametrize(
    ("message", "expected_tool"),
    [
        ("Show me the open work orders", "query_sql"),
        ("Give me the latest dashboard overview", "query_dashboard"),
        ("Summarize the occupancy and cap rate trends", "query_analytics"),
        ("What is our remote work policy?", "query_knowledge_base"),
        ("Find the latest email from John", "query_mail"),
        ("Open the shared folder for the board packet", "query_onedrive"),
        ("Find the meeting notes from May", "query_files"),
        ("Show me the PostgreSQL table schema", "query_postgresql"),
        ("Generate an executive summary", "query_document_generation"),
    ],
)
def test_forced_source_plan_routes_common_intents(message: str, expected_tool: str):
    plan = _forced_source_plan(message)

    assert plan is not None
    assert plan[0] == expected_tool
