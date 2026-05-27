from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


SyncRunSummary = Dict[str, Any]


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


class ConnectorSyncStore:
    """Local sync state store for cursors, run history, and dead-letter queue."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS connector_sync_cursor (
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    cursor_value TEXT,
                    cursor_mode TEXT NOT NULL DEFAULT 'incremental',
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (source_id, entity_type)
                );

                CREATE TABLE IF NOT EXISTS connector_sync_run (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    fetched_count INTEGER NOT NULL DEFAULT 0,
                    persisted_count INTEGER NOT NULL DEFAULT 0,
                    duplicate INTEGER NOT NULL DEFAULT 0,
                    error_text TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_connector_sync_run_source
                    ON connector_sync_run(source_id, entity_type, started_at DESC);

                CREATE TABLE IF NOT EXISTS connector_dead_letter (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    cursor_value TEXT,
                    payload_json TEXT,
                    error_text TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 1,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    last_attempt_at TEXT NOT NULL,
                    replayed_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_connector_dead_letter_status
                    ON connector_dead_letter(status, created_at DESC);
                """
            )

    def get_cursor(self, source_id: str, entity_type: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT cursor_value
                FROM connector_sync_cursor
                WHERE source_id = ? AND entity_type = ?
                """,
                (source_id, entity_type),
            ).fetchone()
            if not row:
                return None
            return str(row["cursor_value"]) if row["cursor_value"] is not None else None

    def upsert_cursor(self, source_id: str, entity_type: str, cursor_value: str | None, cursor_mode: str = "incremental") -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO connector_sync_cursor (source_id, entity_type, cursor_value, cursor_mode, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id, entity_type)
                DO UPDATE SET
                    cursor_value = excluded.cursor_value,
                    cursor_mode = excluded.cursor_mode,
                    updated_at = excluded.updated_at
                """,
                (source_id, entity_type, cursor_value, cursor_mode, _utcnow_iso()),
            )

    def start_run(self, run_id: str, source_id: str, entity_type: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO connector_sync_run (run_id, source_id, entity_type, started_at, status)
                VALUES (?, ?, ?, ?, 'running')
                """,
                (run_id, source_id, entity_type, _utcnow_iso()),
            )
            return int(cur.lastrowid)

    def finish_run(
        self,
        run_db_id: int,
        *,
        status: str,
        fetched_count: int,
        persisted_count: int,
        duplicate: bool,
        error_text: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE connector_sync_run
                SET finished_at = ?,
                    status = ?,
                    fetched_count = ?,
                    persisted_count = ?,
                    duplicate = ?,
                    error_text = ?
                WHERE id = ?
                """,
                (_utcnow_iso(), status, fetched_count, persisted_count, 1 if duplicate else 0, error_text, run_db_id),
            )

    def add_dead_letter(
        self,
        *,
        source_id: str,
        entity_type: str,
        cursor_value: str | None,
        payload: dict[str, Any] | None,
        error_text: str,
    ) -> int:
        payload_json = json.dumps(payload or {}, separators=(",", ":"))
        now = _utcnow_iso()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO connector_dead_letter (
                    source_id, entity_type, cursor_value, payload_json,
                    error_text, attempts, status, created_at, last_attempt_at
                )
                VALUES (?, ?, ?, ?, ?, 1, 'pending', ?, ?)
                """,
                (source_id, entity_type, cursor_value, payload_json, error_text, now, now),
            )
            return int(cur.lastrowid)

    def list_dead_letters(self, status: str = "pending", limit: int = 50) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, source_id, entity_type, cursor_value, payload_json,
                       error_text, attempts, status, created_at, last_attempt_at, replayed_at
                FROM connector_dead_letter
                WHERE status = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (status, max(1, min(limit, 500))),
            ).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            payload: dict[str, Any] = {}
            if row["payload_json"]:
                try:
                    payload = json.loads(row["payload_json"])
                except Exception:
                    payload = {}
            out.append(
                {
                    "id": int(row["id"]),
                    "source_id": row["source_id"],
                    "entity_type": row["entity_type"],
                    "cursor_value": row["cursor_value"],
                    "payload": payload,
                    "error_text": row["error_text"],
                    "attempts": int(row["attempts"]),
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "last_attempt_at": row["last_attempt_at"],
                    "replayed_at": row["replayed_at"],
                }
            )
        return out

    def get_dead_letter(self, dead_letter_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source_id, entity_type, cursor_value, payload_json,
                       error_text, attempts, status, created_at, last_attempt_at, replayed_at
                FROM connector_dead_letter
                WHERE id = ?
                """,
                (dead_letter_id,),
            ).fetchone()

        if not row:
            return None
        payload: dict[str, Any] = {}
        if row["payload_json"]:
            try:
                payload = json.loads(row["payload_json"])
            except Exception:
                payload = {}
        return {
            "id": int(row["id"]),
            "source_id": row["source_id"],
            "entity_type": row["entity_type"],
            "cursor_value": row["cursor_value"],
            "payload": payload,
            "error_text": row["error_text"],
            "attempts": int(row["attempts"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "last_attempt_at": row["last_attempt_at"],
            "replayed_at": row["replayed_at"],
        }

    def mark_dead_letter_replayed(self, dead_letter_id: int, success: bool, error_text: str | None = None) -> None:
        now = _utcnow_iso()
        with self._connect() as conn:
            if success:
                conn.execute(
                    """
                    UPDATE connector_dead_letter
                    SET status = 'replayed', replayed_at = ?, last_attempt_at = ?
                    WHERE id = ?
                    """,
                    (now, now, dead_letter_id),
                )
                return

            conn.execute(
                """
                UPDATE connector_dead_letter
                SET status = 'pending',
                    attempts = attempts + 1,
                    error_text = ?,
                    last_attempt_at = ?
                WHERE id = ?
                """,
                (error_text or 'Replay failed', now, dead_letter_id),
            )


def get_connector_sync_store() -> ConnectorSyncStore:
    db_path = os.getenv("CONNECTOR_SYNC_DB_PATH", "/tmp/evieai_connector_sync.db")
    return ConnectorSyncStore(db_path=db_path)
