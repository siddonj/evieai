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


def test_service_allows_finalization_after_approval(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)
    record = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="board_report",
        title="Board Report",
        source_summary="Board summary",
    )
    store.mark_approved(
        document_action_id=record["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Board",
        output_formats=["pdf", "docx"],
    )

    result = service.finalize(document_action_id=record["id"])

    assert result["status"] == "ready"
    assert result["document_action_id"] == record["id"]
