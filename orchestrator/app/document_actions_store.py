from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class DocumentActionsStore:
    def __init__(self, db_path: Path | str = "document_actions.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_actions (
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
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(document_actions)").fetchall()
            }
            if "artifacts_json" not in columns:
                conn.execute(
                    "ALTER TABLE document_actions ADD COLUMN artifacts_json TEXT NOT NULL DEFAULT '[]'"
                )
            if "announcement_json" not in columns:
                conn.execute(
                    "ALTER TABLE document_actions ADD COLUMN announcement_json TEXT"
                )
            if "executed_at" not in columns:
                conn.execute(
                    "ALTER TABLE document_actions ADD COLUMN executed_at TEXT"
                )

    def create_draft(
        self,
        *,
        user_id: str,
        work_packet_id: str,
        document_type: str,
        title: str,
        draft_markdown: str,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO document_actions (
                    user_id, work_packet_id, document_type, title,
                    draft_markdown, draft_version, status, output_formats_json,
                    artifacts_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    work_packet_id,
                    document_type,
                    title,
                    draft_markdown,
                    1,
                    "draft",
                    "[]",
                    "[]",
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM document_actions WHERE id = ?",
                (cur.lastrowid,),
            ).fetchone()
        return self._row_to_dict(row)

    def mark_approved(
        self,
        *,
        document_action_id: int,
        approved_by: str,
        destination_type: str,
        destination_ref: str,
        output_formats: list[str],
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE document_actions
                SET status = ?,
                    approved_by = ?,
                    approved_at = ?,
                    destination_type = ?,
                    destination_ref = ?,
                    output_formats_json = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    "approved",
                    approved_by,
                    now,
                    destination_type,
                    destination_ref,
                    _canonical_json(output_formats),
                    now,
                    document_action_id,
                ),
            )
            row = conn.execute(
                "SELECT * FROM document_actions WHERE id = ?",
                (document_action_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def get(self, document_action_id: int) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM document_actions WHERE id = ?",
                (document_action_id,),
            ).fetchone()
        return self._row_to_dict(row)

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any]:
        if row is None:
            raise KeyError("document action not found")

        data = dict(row)
        data["output_formats"] = json.loads(data.pop("output_formats_json") or "[]")
        data["artifacts"] = json.loads(data.pop("artifacts_json") or "[]")
        data["announcement"] = json.loads(data.pop("announcement_json") or "null")
        return data


_DOCUMENT_ACTIONS_STORE: DocumentActionsStore | None = None


def get_document_actions_store() -> DocumentActionsStore:
    global _DOCUMENT_ACTIONS_STORE
    if _DOCUMENT_ACTIONS_STORE is None:
        db_path = os.getenv("DOCUMENT_ACTIONS_DB_PATH", "data/document_actions.db")
        _DOCUMENT_ACTIONS_STORE = DocumentActionsStore(db_path=db_path)
    return _DOCUMENT_ACTIONS_STORE
