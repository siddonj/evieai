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
        "title": "Sql",
        "summary": "SQL pipeline snapshot",
        "signals": ["active_deals_count:9"],
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
    assert packet["suggested_exports"] == ["pdf", "docx", "xlsx"]
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
