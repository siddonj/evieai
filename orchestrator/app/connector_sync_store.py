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
    """Local sync state store for cursors, run history, dead-letter queue, and durable schedules."""

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

                CREATE TABLE IF NOT EXISTS connector_sync_schedule (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    limit_value INTEGER NOT NULL DEFAULT 100,
                    interval_seconds INTEGER NOT NULL DEFAULT 300,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    next_run_at TEXT NOT NULL,
                    lease_owner TEXT,
                    lease_until TEXT,
                    last_run_started_at TEXT,
                    last_run_finished_at TEXT,
                    last_status TEXT,
                    last_error TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(source_id, entity_type)
                );

                CREATE INDEX IF NOT EXISTS idx_connector_sync_schedule_due
                    ON connector_sync_schedule(enabled, next_run_at);
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

    def upsert_schedule(
        self,
        *,
        source_id: str,
        entity_type: str,
        limit_value: int,
        interval_seconds: int,
        enabled: bool = True,
    ) -> dict[str, Any]:
        now = _utcnow_iso()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO connector_sync_schedule (
                    source_id, entity_type, limit_value, interval_seconds, enabled,
                    next_run_at, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, entity_type)
                DO UPDATE SET
                    limit_value = excluded.limit_value,
                    interval_seconds = excluded.interval_seconds,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at,
                    next_run_at = CASE
                        WHEN connector_sync_schedule.next_run_at < excluded.updated_at
                        THEN excluded.updated_at
                        ELSE connector_sync_schedule.next_run_at
                    END
                """,
                (
                    source_id,
                    entity_type,
                    max(1, limit_value),
                    max(5, interval_seconds),
                    1 if enabled else 0,
                    now,
                    now,
                    now,
                ),
            )

        row = self.get_schedule(source_id, entity_type)
        if row is None:
            raise RuntimeError("Failed to upsert schedule")
        return row

    def list_schedules(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        query = """
            SELECT id, source_id, entity_type, limit_value, interval_seconds,
                   enabled, next_run_at, lease_owner, lease_until,
                   last_run_started_at, last_run_finished_at, last_status,
                   last_error, created_at, updated_at
            FROM connector_sync_schedule
        """
        params: tuple[Any, ...] = ()
        if enabled_only:
            query += " WHERE enabled = 1"
        query += " ORDER BY source_id, entity_type"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_schedule_dict(row) for row in rows]

    def get_schedule(self, source_id: str, entity_type: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source_id, entity_type, limit_value, interval_seconds,
                       enabled, next_run_at, lease_owner, lease_until,
                       last_run_started_at, last_run_finished_at, last_status,
                       last_error, created_at, updated_at
                FROM connector_sync_schedule
                WHERE source_id = ? AND entity_type = ?
                """,
                (source_id, entity_type),
            ).fetchone()
        return self._row_to_schedule_dict(row) if row else None

    def set_schedule_enabled(self, source_id: str, entity_type: str, enabled: bool) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE connector_sync_schedule
                SET enabled = ?,
                    updated_at = ?,
                    next_run_at = CASE WHEN ? = 1 THEN ? ELSE next_run_at END
                WHERE source_id = ? AND entity_type = ?
                """,
                (1 if enabled else 0, _utcnow_iso(), 1 if enabled else 0, _utcnow_iso(), source_id, entity_type),
            )
            return cur.rowcount > 0

    def delete_schedule(self, source_id: str, entity_type: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                DELETE FROM connector_sync_schedule
                WHERE source_id = ? AND entity_type = ?
                """,
                (source_id, entity_type),
            )
            return cur.rowcount > 0

    def claim_due_schedule(self, *, worker_id: str, lease_seconds: int = 60) -> dict[str, Any] | None:
        now = _utcnow_iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, source_id, entity_type, limit_value, interval_seconds,
                       enabled, next_run_at, lease_owner, lease_until,
                       last_run_started_at, last_run_finished_at, last_status,
                       last_error, created_at, updated_at
                FROM connector_sync_schedule
                WHERE enabled = 1
                  AND next_run_at <= ?
                  AND (lease_until IS NULL OR lease_until <= ?)
                ORDER BY next_run_at ASC
                LIMIT 1
                """,
                (now, now),
            ).fetchone()
            if not row:
                return None

            schedule_id = int(row["id"])
            lease_until = datetime.utcnow().timestamp() + max(5, lease_seconds)
            lease_until_iso = datetime.utcfromtimestamp(lease_until).isoformat(timespec="microseconds") + "Z"

            cur = conn.execute(
                """
                UPDATE connector_sync_schedule
                SET lease_owner = ?,
                    lease_until = ?,
                    last_run_started_at = ?,
                    updated_at = ?
                WHERE id = ?
                  AND (lease_until IS NULL OR lease_until <= ?)
                """,
                (worker_id, lease_until_iso, now, now, schedule_id, now),
            )
            if cur.rowcount == 0:
                return None

        # reload with lease assignment
        with self._connect() as conn2:
            claimed = conn2.execute(
                """
                SELECT id, source_id, entity_type, limit_value, interval_seconds,
                       enabled, next_run_at, lease_owner, lease_until,
                       last_run_started_at, last_run_finished_at, last_status,
                       last_error, created_at, updated_at
                FROM connector_sync_schedule
                WHERE id = ?
                """,
                (schedule_id,),
            ).fetchone()
        return self._row_to_schedule_dict(claimed) if claimed else None

    def complete_claimed_schedule(
        self,
        *,
        schedule_id: int,
        worker_id: str,
        success: bool,
        error_text: str | None = None,
    ) -> bool:
        now = _utcnow_iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT interval_seconds, lease_owner
                FROM connector_sync_schedule
                WHERE id = ?
                """,
                (schedule_id,),
            ).fetchone()
            if not row:
                return False
            if row["lease_owner"] != worker_id:
                return False

            interval_seconds = int(row["interval_seconds"])
            next_run_dt = datetime.utcnow().timestamp() + max(5, interval_seconds)
            next_run_iso = datetime.utcfromtimestamp(next_run_dt).isoformat(timespec="microseconds") + "Z"

            cur = conn.execute(
                """
                UPDATE connector_sync_schedule
                SET lease_owner = NULL,
                    lease_until = NULL,
                    next_run_at = ?,
                    last_run_finished_at = ?,
                    last_status = ?,
                    last_error = ?,
                    updated_at = ?
                WHERE id = ? AND lease_owner = ?
                """,
                (
                    next_run_iso,
                    now,
                    "success" if success else "failed",
                    None if success else (error_text or "Schedule run failed"),
                    now,
                    schedule_id,
                    worker_id,
                ),
            )
            return cur.rowcount > 0

    @staticmethod
    def _row_to_schedule_dict(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "source_id": row["source_id"],
            "entity_type": row["entity_type"],
            "limit_value": int(row["limit_value"]),
            "interval_seconds": int(row["interval_seconds"]),
            "enabled": bool(row["enabled"]),
            "next_run_at": row["next_run_at"],
            "lease_owner": row["lease_owner"],
            "lease_until": row["lease_until"],
            "last_run_started_at": row["last_run_started_at"],
            "last_run_finished_at": row["last_run_finished_at"],
            "last_status": row["last_status"],
            "last_error": row["last_error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }


def get_connector_sync_store() -> ConnectorSyncStore:
    db_path = os.getenv("CONNECTOR_SYNC_DB_PATH", "/tmp/evieai_connector_sync.db")
    return ConnectorSyncStore(db_path=db_path)
