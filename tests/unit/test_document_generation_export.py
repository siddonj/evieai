from mcp_servers.document_generation.app.main import ExportRequest, _report_sections


def test_report_sections_falls_back_when_empty():
    payload = ExportRequest(type="report", format="pdf", title="Board Briefing", data={})

    sections = _report_sections(payload)

    assert sections == [
        {
            "heading": "Board Briefing",
            "content": "No structured sections were returned with this document.",
            "key_metrics": [],
        }
    ]


def test_report_sections_preserves_existing_sections():
    payload = ExportRequest(
        type="report",
        format="docx",
        title="Board Briefing",
        data={"sections": [{"heading": "Overview", "content": "Ready"}]},
    )

    sections = _report_sections(payload)

    assert sections == [{"heading": "Overview", "content": "Ready"}]
