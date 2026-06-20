from __future__ import annotations

import sqlite3

import pytest

import orchestrator.app.document_actions_service as document_actions_service_module

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
    assert result["announcement"]["status"] == "completed"
    assert result["announcement"]["id"] > 0
    assert result["announcement"]["action_id"]
    announcement_action = actions_store.get_action_request(result["announcement"]["action_id"])
    assert announcement_action is not None
    assert announcement_action["source_id"] == "document_workflow"
    assert announcement_action["entity_type"] == "announcement"
    assert announcement_action["status"] == "completed"
    assert announcement_action["payload"]["document_action_id"] == draft["id"]
    assert announcement_action["result"]["delivered"] is True
    assert persisted["status"] == "executed"
    assert persisted["executed_at"]
    assert persisted["artifacts"] == result["artifacts"]
    assert persisted["announcement"]["id"] == result["announcement"]["id"]

    rerun = service.finalize(document_action_id=draft["id"])

    assert rerun["status"] == "executed"
    assert rerun["announcement"]["id"] == result["announcement"]["id"]
    assert rerun["announcement"]["action_id"] == result["announcement"]["action_id"]
    assert rerun["artifacts"][0]["storage_ref"] == result["artifacts"][0]["storage_ref"]


def test_service_records_export_package_metadata(tmp_path):
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
    service.finalize(document_action_id=draft["id"])

    result = service.export_package(document_action_id=draft["id"])
    persisted = store.get(draft["id"])
    export_action = actions_store.get_action_request(result["export_action"]["action_id"])

    assert result["status"] == "completed"
    assert persisted["export_package"]["status"] == "completed"
    assert len(result["artifacts"]) == 3
    assert result["artifacts"][0]["format"] == "pdf"
    assert result["artifacts"][1]["format"] == "docx"
    assert result["artifacts"][2]["format"] == "xlsx"
    assert export_action is not None
    assert export_action["source_id"] == "document_workflow"
    assert export_action["entity_type"] == "export_package"
    assert export_action["status"] == "completed"
    assert export_action["payload"]["document_action_id"] == draft["id"]
    assert export_action["result"]["artifact_count"] == 3

    rerun = service.export_package(document_action_id=draft["id"])

    assert rerun["status"] == "completed"
    assert rerun["export_action"]["action_id"] == result["export_action"]["action_id"]
    assert rerun["artifacts"] == result["artifacts"]


def test_service_blocks_export_before_finalization(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)
    draft = service.create_draft(
        user_id="alice",
        work_packet_id="wp-export-blocked",
        document_type="board_report",
        title="Board Report",
        source_summary="Board summary",
    )

    result = service.export_package(document_action_id=draft["id"])

    assert result["status"] == "blocked"
    assert result["reason"] == "finalization_required"
    assert result["document_action_id"] == draft["id"]


def test_store_migrates_legacy_schema_for_export_package_metadata(tmp_path):
    db_path = tmp_path / "document_actions.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE document_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                work_packet_id TEXT NOT NULL,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                draft_markdown TEXT NOT NULL,
                draft_version INTEGER NOT NULL,
                status TEXT NOT NULL,
                destination_type TEXT,
                destination_ref TEXT,
                output_formats_json TEXT NOT NULL,
                approved_by TEXT,
                approved_at TEXT,
                artifacts_json TEXT NOT NULL DEFAULT '[]',
                announcement_json TEXT,
                executed_at TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

    store = DocumentActionsStore(db_path=db_path)

    with store._connect() as conn:
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(document_actions)").fetchall()
        }

    assert "export_package_json" in columns
    assert "exported_at" in columns


def test_store_round_trips_export_package_metadata(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    draft = store.create_draft(
        user_id="alice",
        work_packet_id="wp-export-1",
        document_type="board_report",
        title="Board Report",
        draft_markdown="# Board Report\n",
    )
    export_package = {
        "status": "completed",
        "artifacts": [
            {"format": "pdf", "file_name": "board_report.pdf"},
            {"format": "docx", "file_name": "board_report.docx"},
            {"format": "zip", "file_name": "board_report.zip"},
        ],
        "requested_by": "alice",
    }

    updated = store.mark_export_package(
        document_action_id=draft["id"],
        export_package=export_package,
    )
    persisted = store.get(draft["id"])

    assert updated["export_package"] == export_package
    assert updated["exported_at"]
    assert persisted["export_package"] == export_package
    assert persisted["exported_at"] == updated["exported_at"]


def test_service_promotes_artifact_to_blob_when_available(tmp_path, monkeypatch):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    actions_store = ActionsStore(str(tmp_path / "actions.db"))
    artifact_root = tmp_path / "document_artifacts"
    service = DocumentActionsService(
        store=store,
        artifact_root=artifact_root,
        actions_store=actions_store,
    )
    monkeypatch.setattr(
        document_actions_service_module,
        "upload_report",
        lambda name, content, content_type="text/plain": f"https://blob.example/{name}",
    )
    draft = service.create_draft(
        user_id="alice",
        work_packet_id="wp-blob-1",
        document_type="executive_briefing",
        title="Executive Briefing",
        source_summary="Blob summary",
    )
    store.mark_approved(
        document_action_id=draft["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Exec",
        output_formats=["pdf"],
    )

    result = service.finalize(document_action_id=draft["id"])

    assert result["artifacts"][0]["blob_url"] == f"https://blob.example/document_artifacts/{draft['id']}/executive_briefing.pdf"
