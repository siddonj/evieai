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


def test_md_blocks_parses_headings_bullets_and_paragraphs():
    from mcp_servers.document_generation.app.main import _md_blocks

    blocks = _md_blocks("## Summary\n\n- **NOI:** $4.8M\nPlain line\n1. First step")

    assert blocks == [
        ("heading", 2, "Summary"),
        ("bullet", 0, "**NOI:** $4.8M"),
        ("para", 0, "Plain line"),
        ("bullet", 0, "First step"),
    ]


def test_md_plain_content_strips_markers():
    from mcp_servers.document_generation.app.main import _md_plain_content

    text = _md_plain_content("### Key Metrics\n- **Occupancy:** 94.2%\nRegular *text*")

    assert text == "Key Metrics\n• Occupancy: 94.2%\nRegular text"
    assert "**" not in text and "#" not in text


def test_md_html_renders_structure_and_escapes():
    from mcp_servers.document_generation.app.main import _md_html

    html = _md_html("## Trends\n- **Rent** <up>\nBody text")

    assert "<h3" in html and "Trends" in html
    assert "<ul" in html and "<strong>Rent</strong>" in html
    assert "&lt;up&gt;" in html
    assert "**" not in html and "##" not in html
