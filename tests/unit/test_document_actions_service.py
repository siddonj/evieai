from __future__ import annotations

from orchestrator.app.actions_store import ActionsStore
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
    actions_store = ActionsStore(str(tmp_path / "actions.db"))
    artifact_root = tmp_path / "document_artifacts"
    service = DocumentActionsService(
        store=store,
        artifact_root=artifact_root,
        actions_store=actions_store,
    )
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
    first_artifact_path = artifact_root / str(draft["id"]) / "board_report.pdf"

    assert result["status"] == "executed"
    assert result["artifacts"][0]["format"] == "pdf"
    assert result["artifacts"][0]["storage_ref"] == str(first_artifact_path)
    assert result["artifacts"][0]["size_bytes"] == first_artifact_path.stat().st_size
    assert first_artifact_path.exists()
    assert "# Board Report" in first_artifact_path.read_text(encoding="utf-8")
    assert result["destination"]["type"] == "onedrive"
    assert result["announcement"]["status"] == "approved"
    assert result["announcement"]["id"] > 0
    assert result["announcement"]["action_id"]
    announcement_action = actions_store.get_action_request(result["announcement"]["action_id"])
    assert announcement_action is not None
    assert announcement_action["source_id"] == "document_workflow"
    assert announcement_action["entity_type"] == "announcement"
    assert announcement_action["status"] == "approved"
    assert announcement_action["payload"]["document_action_id"] == draft["id"]
    assert persisted["status"] == "executed"
    assert persisted["executed_at"]
    assert persisted["artifacts"] == result["artifacts"]
    assert persisted["announcement"]["id"] == result["announcement"]["id"]

    rerun = service.finalize(document_action_id=draft["id"])

    assert rerun["status"] == "executed"
    assert rerun["announcement"]["id"] == result["announcement"]["id"]
    assert rerun["announcement"]["action_id"] == result["announcement"]["action_id"]
    assert rerun["artifacts"][0]["storage_ref"] == result["artifacts"][0]["storage_ref"]
