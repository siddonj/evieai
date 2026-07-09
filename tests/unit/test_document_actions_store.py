from __future__ import annotations

import sqlite3

from orchestrator.app.document_actions_store import DocumentActionsStore


def test_store_creates_draft_record(tmp_path):
    db_path = tmp_path / "document_actions.db"
    store = DocumentActionsStore(db_path=db_path)
    created = store.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="executive_briefing",
        title="Executive Briefing",
        draft_markdown="# Briefing",
    )
    reopened = DocumentActionsStore(db_path=db_path)
    record = reopened.get(created["id"])

    assert record["status"] == "draft"
    assert record["user_id"] == "alice"
    assert record["work_packet_id"] == "wp-1"
    assert record["document_type"] == "executive_briefing"
    assert record["title"] == "Executive Briefing"
    assert record["draft_version"] == 1
    assert record["output_formats"] == []
    assert record["artifacts"] == []
    assert record["created_at"]
    assert record["updated_at"]


def test_store_records_approval_and_destination(tmp_path):
    db_path = tmp_path / "document_actions.db"
    store = DocumentActionsStore(db_path=db_path)
    created = store.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="board_report",
        title="Board Report",
        draft_markdown="# Board",
    )

    store.mark_approved(
        document_action_id=created["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Board",
        output_formats=["pdf", "docx"],
    )
    reopened = DocumentActionsStore(db_path=db_path)
    approved = reopened.get(created["id"])

    assert approved["status"] == "approved"
    assert approved["approved_by"] == "alice"
    assert approved["approved_at"]
    assert approved["destination_type"] == "onedrive"
    assert approved["destination_ref"] == "Reports/Board"
    assert approved["output_formats"] == ["pdf", "docx"]


def test_store_migrates_older_schema_on_reopen(tmp_path):
    db_path = tmp_path / "document_actions.db"
    conn = sqlite3.connect(db_path)
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
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        INSERT INTO document_actions (
            user_id, work_packet_id, document_type, title, draft_markdown,
            draft_version, status, output_formats_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "alice",
            "wp-1",
            "executive_briefing",
            "Executive Briefing",
            "# Briefing",
            1,
            "draft",
            "[]",
            "2026-06-19T00:00:00+00:00",
            "2026-06-19T00:00:00+00:00",
        ),
    )
    conn.commit()
    conn.close()

    reopened = DocumentActionsStore(db_path=db_path)
    record = reopened.get(1)

    assert record["artifacts"] == []
    assert record["announcement"] is None


def test_store_lists_actions_for_user_newest_first(tmp_path):
    db_path = tmp_path / "document_actions.db"
    store = DocumentActionsStore(db_path=db_path)
    first = store.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="executive_briefing",
        title="Executive Briefing",
        draft_markdown="# Briefing",
    )
    second = store.create_draft(
        user_id="alice",
        work_packet_id="wp-2",
        document_type="board_report",
        title="Board Report",
        draft_markdown="# Board",
    )
    store.create_draft(
        user_id="bob",
        work_packet_id="wp-3",
        document_type="operational_report",
        title="Ops Report",
        draft_markdown="# Ops",
    )

    actions = store.list_actions(user_id="alice", limit=10)

    assert [action["id"] for action in actions] == [second["id"], first["id"]]
    assert all(action["user_id"] == "alice" for action in actions)


def test_store_delete_removes_record(tmp_path):
    db_path = tmp_path / "document_actions.db"
    store = DocumentActionsStore(db_path=db_path)
    created = store.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="executive_briefing",
        title="Executive Briefing",
        draft_markdown="# Briefing",
    )

    store.delete(created["id"])

    try:
        store.get(created["id"])
        raised = False
    except Exception:
        raised = True
    assert raised
    assert store.list_actions(user_id="alice") == []


def test_store_delete_missing_record_raises(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    try:
        store.delete(999)
        raised = False
    except KeyError:
        raised = True
    assert raised
