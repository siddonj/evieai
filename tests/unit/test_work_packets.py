from app.work_packets import build_work_packet


def test_build_work_packet_groups_evidence_and_sets_conflict_status():
    packet = build_work_packet(
        reply="Pipeline is $8.7M, but two systems disagree on active deal count.",
        tool_calls=[{"name": "query_sql", "args": {"query": "pipeline"}}],
        mcp_results=[
            {
                "service": "sql",
                "summary": "SQL pipeline snapshot",
                "metrics": {"total_pipeline_value": 8700000, "active_deals_count": 9},
            },
            {
                "service": "analytics",
                "summary": "Analytics pipeline snapshot",
                "kpi_cards": [
                    {
                        "name": "Active Deals",
                        "value": 42,
                        "change": "+5",
                        "period": "30d",
                        "status": "up",
                        "target": "40",
                        "target_status": "met",
                    }
                ],
            },
        ],
    )

    assert packet["answer"]["summary"] == "Pipeline is $8.7M, but two systems disagree on active deal count."
    assert packet["reconciliation"]["status"] == "conflicting"
    assert packet["reconciliation"]["source_count"] == 2
    assert len(packet["evidence"]) == 2
    assert packet["evidence"][0] == {
        "source": "sql",
        "title": "SQL",
        "summary": "SQL pipeline snapshot",
        "signals": ["active_deals_count:9"],
        "snippets": [],
        "raw": {
            "service": "sql",
            "summary": "SQL pipeline snapshot",
            "metrics": {"total_pipeline_value": 8700000, "active_deals_count": 9},
        },
    }
    assert packet["evidence"][1] == {
        "source": "analytics",
        "title": "Analytics",
        "summary": "Analytics pipeline snapshot",
        "signals": ["active_deals_count:42"],
        "snippets": [],
        "raw": {
            "service": "analytics",
            "summary": "Analytics pipeline snapshot",
            "kpi_cards": [
                {
                    "name": "Active Deals",
                    "value": 42,
                    "change": "+5",
                    "period": "30d",
                    "status": "up",
                    "target": "40",
                    "target_status": "met",
                }
            ],
        },
    }
    assert packet["suggested_exports"] == []
    assert packet["tool_calls"] == [{"name": "query_sql", "args": {"query": "pipeline"}}]


def test_build_work_packet_confirms_when_sources_share_same_signal():
    packet = build_work_packet(
        reply="Both systems agree on 9 active deals.",
        tool_calls=[{"name": "query_sql", "args": {"query": "active deals"}}],
        mcp_results=[
            {
                "service": "sql",
                "summary": "SQL pipeline snapshot",
                "metrics": {"active_deals_count": 9},
            },
            {
                "service": "analytics",
                "summary": "Analytics pipeline snapshot",
                "kpi_cards": [
                    {
                        "name": "Active Deals",
                        "value": 9,
                    }
                ],
            },
        ],
    )

    assert packet["reconciliation"]["status"] == "confirmed"
    assert packet["reconciliation"]["source_count"] == 2
    assert packet["suggested_exports"] == []


def test_build_work_packet_preserves_kb_acronym_in_titles():
    packet = build_work_packet(
        reply="Found one policy document.",
        tool_calls=[],
        mcp_results=[
            {
                "service": "kb",
                "summary": "Found one policy",
                "documents": [{"title": "Expense Policy"}],
            }
        ],
    )

    assert packet["evidence"][0]["title"] == "KB"


def test_build_work_packet_marks_partial_when_only_one_source_returns_evidence():
    packet = build_work_packet(
        reply="I found one supporting source.",
        tool_calls=[],
        mcp_results=[
            {
                "service": "mail",
                "summary": "Found 3 emails",
                "messages": [{"subject": "Board update", "from": "ceo@example.com"}],
            },
            {
                "service": "analytics",
                "summary": "No matching records",
            }
        ],
    )

    assert packet["reconciliation"]["status"] == "partial"
    assert packet["reconciliation"]["source_count"] == 2
    assert packet["evidence"][0]["snippets"] == ["1 email(s)"]
    assert packet["evidence"][1]["signals"] == []
    assert packet["evidence"][1]["snippets"] == []


def test_build_work_packet_marks_conflicting_when_populated_sources_mix_signals_and_snippets():
    packet = build_work_packet(
        reply="One source has metric evidence and another has only email evidence.",
        tool_calls=[],
        mcp_results=[
            {
                "service": "sql",
                "summary": "SQL pipeline snapshot",
                "metrics": {"active_deals_count": 9},
            },
            {
                "service": "mail",
                "summary": "Found 3 emails",
                "messages": [{"subject": "Board update", "from": "ceo@example.com"}],
            },
        ],
    )

    assert packet["reconciliation"]["status"] == "conflicting"
    assert packet["reconciliation"]["source_count"] == 2


def test_build_work_packet_collects_export_and_action_suggestions_from_documents():
    packet = build_work_packet(
        reply="Draft board briefing ready.",
        tool_calls=[{"name": "query_document_generation", "args": {"query": "board briefing"}}],
        mcp_results=[
            {
                "service": "document_generation",
                "summary": "Generated board briefing",
                "generated_documents": [{"title": "Board Briefing", "status": "draft"}],
            }
        ],
    )

    assert packet["suggested_exports"] == ["pdf", "docx"]
    assert packet["suggested_actions"][0]["type"] == "review_document"
    assert packet["suggested_actions"][0]["label"] == "Review Board Briefing"
