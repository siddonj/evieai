from __future__ import annotations

from orchestrator.app.document_actions_service import DocumentActionsService
from orchestrator.app.document_actions_store import DocumentActionsStore


def test_service_creates_document_draft(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)

    record = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="executive_briefing",
        title="Executive Briefing",
        source_summary="Portfolio summary",
    )

    assert record["status"] == "draft"
    assert "Portfolio summary" in record["draft_markdown"]


def test_service_blocks_finalization_before_approval(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)
    record = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="operational_report",
        title="Ops Report",
        source_summary="Ops summary",
    )

    result = service.finalize(document_action_id=record["id"])

    assert result["status"] == "blocked"
    assert result["reason"] == "approval_required"


def test_service_finalizes_after_approval_and_records_artifacts(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)
    draft = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="board_report",
        title="Board Report",
        source_summary="Board summary",
    )
    store.mark_approved(
        document_action_id=draft["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Board",
        output_formats=["pdf", "docx"],
    )

    result = service.finalize(document_action_id=draft["id"])
    persisted = store.get(draft["id"])

    assert result["status"] == "executed"
    assert result["artifacts"][0]["format"] == "pdf"
    assert result["artifacts"][0]["storage_ref"] == "onedrive://Reports/Board/board_report.pdf"
    assert result["destination"]["type"] == "onedrive"
    assert result["announcement"]["status"] == "created"
    assert result["announcement"]["id"] > 0
    assert persisted["status"] == "executed"
    assert persisted["executed_at"]
    assert persisted["artifacts"] == result["artifacts"]
    assert persisted["announcement"]["id"] == result["announcement"]["id"]

    rerun = service.finalize(document_action_id=draft["id"])

    assert rerun["status"] == "executed"
    assert rerun["announcement"]["id"] == result["announcement"]["id"]
