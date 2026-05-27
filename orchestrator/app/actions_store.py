from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


def _parse_limit(value: int, *, default: int = 100, min_value: int = 1, max_value: int = 500) -> int:
    n = value if isinstance(value, int) else default
    return max(min_value, min(max_value, n))


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ActionsStore:
    """Durable local state for write-back requests, approvals, circuit breakers, and audit events."""

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
                CREATE TABLE IF NOT EXISTS action_request (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT UNIQUE NOT NULL,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    policy_version TEXT NOT NULL,
                    policy_decision_json TEXT NOT NULL,
                    requires_approval INTEGER NOT NULL DEFAULT 0,
                    approved_by TEXT,
                    approved_at TEXT,
                    rejection_reason TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    result_json TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_action_request_source
                    ON action_request(source_id, entity_type, created_at DESC);

                CREATE INDEX IF NOT EXISTS idx_action_request_status
                    ON action_request(status, created_at DESC);

                CREATE UNIQUE INDEX IF NOT EXISTS idx_action_request_idempotency
                    ON action_request(source_id, entity_type, idempotency_key);

                CREATE TABLE IF NOT EXISTS approval_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action_id TEXT UNIQUE NOT NULL,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT,
                    requested_at TEXT NOT NULL,
                    decided_by TEXT,
                    decided_at TEXT,
                    decision_note TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_approval_queue_status
                    ON approval_queue(status, requested_at DESC);

                CREATE TABLE IF NOT EXISTS connector_circuit_breaker (
                    source_id TEXT PRIMARY KEY,
                    state TEXT NOT NULL,
                    reason TEXT,
                    opened_at TEXT,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS actions_audit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    action_id TEXT,
                    source_id TEXT,
                    entity_type TEXT,
                    payload_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    prev_hash TEXT,
                    row_hash TEXT NOT NULL
                );
                """
            )

    def _last_ledger_hash(self, conn: sqlite3.Connection) -> str | None:
        row = conn.execute("SELECT row_hash FROM actions_audit_ledger ORDER BY id DESC LIMIT 1").fetchone()
        return str(row["row_hash"]) if row else None

    def append_audit_event(
        self,
        *,
        event_type: str,
        action_id: str | None,
        source_id: str | None,
        entity_type: str | None,
        payload: dict[str, Any],
    ) -> None:
        recorded_at = _utcnow_iso()
        payload_json = _canonical_json(payload)

        with self._connect() as conn:
            prev_hash = self._last_ledger_hash(conn)
            digest_input = (
                f"{event_type}|{action_id or ''}|{source_id or ''}|{entity_type or ''}|"
                f"{recorded_at}|{prev_hash or ''}|{payload_json}"
            )
            row_hash = _sha256(digest_input)
            conn.execute(
                """
                INSERT INTO actions_audit_ledger (
                    event_type, action_id, source_id, entity_type, payload_json,
                    recorded_at, prev_hash, row_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (event_type, action_id, source_id, entity_type, payload_json, recorded_at, prev_hash, row_hash),
            )

    def get_circuit_state(self, source_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT source_id, state, reason, opened_at, updated_at
                FROM connector_circuit_breaker
                WHERE source_id = ?
                """,
                (source_id,),
            ).fetchone()
        if not row:
            return {
                "source_id": source_id,
                "state": "closed",
                "reason": None,
                "opened_at": None,
                "updated_at": None,
            }
        return {
            "source_id": row["source_id"],
            "state": row["state"],
            "reason": row["reason"],
            "opened_at": row["opened_at"],
            "updated_at": row["updated_at"],
        }

    def set_circuit_state(self, *, source_id: str, state: str, reason: str | None = None) -> dict[str, Any]:
        now = _utcnow_iso()
        opened_at = now if state == "open" else None

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO connector_circuit_breaker (source_id, state, reason, opened_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id)
                DO UPDATE SET
                    state = excluded.state,
                    reason = excluded.reason,
                    opened_at = excluded.opened_at,
                    updated_at = excluded.updated_at
                """,
                (source_id, state, reason, opened_at, now),
            )

        self.append_audit_event(
            event_type="action.circuit.state_change",
            action_id=None,
            source_id=source_id,
            entity_type=None,
            payload={"state": state, "reason": reason},
        )
        return self.get_circuit_state(source_id)

    def create_action_request(
        self,
        *,
        action_id: str,
        source_id: str,
        entity_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
        risk_level: str,
        policy_version: str,
        policy_decision: dict[str, Any],
        requires_approval: bool,
        requested_by: str | None,
    ) -> dict[str, Any]:
        now = _utcnow_iso()
        payload_json = _canonical_json(payload)
        payload_hash = _sha256(payload_json)
        status = "pending_approval" if requires_approval else "approved"

        with self._connect() as conn:
            existing = conn.execute(
                """
                SELECT action_id, status, result_json
                FROM action_request
                WHERE source_id = ? AND entity_type = ? AND idempotency_key = ?
                """,
                (source_id, entity_type, idempotency_key),
            ).fetchone()

            if existing:
                result_payload = None
                if existing["result_json"]:
                    try:
                        result_payload = json.loads(existing["result_json"])
                    except Exception:
                        result_payload = {"raw": existing["result_json"]}
                return {
                    "duplicate": True,
                    "action_id": existing["action_id"],
                    "status": existing["status"],
                    "result": result_payload,
                }

            conn.execute(
                """
                INSERT INTO action_request (
                    action_id, source_id, entity_type, payload_json, payload_hash,
                    idempotency_key, status, risk_level, policy_version,
                    policy_decision_json, requires_approval,
                    approved_by, approved_at, rejection_reason,
                    created_at, updated_at, result_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?, NULL)
                """,
                (
                    action_id,
                    source_id,
                    entity_type,
                    payload_json,
                    payload_hash,
                    idempotency_key,
                    status,
                    risk_level,
                    policy_version,
                    _canonical_json(policy_decision),
                    1 if requires_approval else 0,
                    now,
                    now,
                ),
            )

            if requires_approval:
                conn.execute(
                    """
                    INSERT INTO approval_queue (
                        action_id, source_id, entity_type, reason,
                        status, requested_by, requested_at,
                        decided_by, decided_at, decision_note
                    ) VALUES (?, ?, ?, ?, 'pending', ?, ?, NULL, NULL, NULL)
                    """,
                    (
                        action_id,
                        source_id,
                        entity_type,
                        str(policy_decision.get("reason", "High-risk write requires approval")),
                        requested_by,
                        now,
                    ),
                )

        self.append_audit_event(
            event_type="action.write.intent",
            action_id=action_id,
            source_id=source_id,
            entity_type=entity_type,
            payload={
                "idempotency_key": idempotency_key,
                "risk_level": risk_level,
                "status": status,
                "requires_approval": requires_approval,
                "payload_hash": payload_hash,
            },
        )

        return {
            "duplicate": False,
            "action_id": action_id,
            "status": status,
            "requires_approval": requires_approval,
        }

    def update_action_result(
        self,
        *,
        action_id: str,
        status: str,
        result: dict[str, Any],
        approved_by: str | None = None,
        rejection_reason: str | None = None,
    ) -> dict[str, Any] | None:
        now = _utcnow_iso()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT action_id, source_id, entity_type
                FROM action_request
                WHERE action_id = ?
                """,
                (action_id,),
            ).fetchone()
            if not row:
                return None

            conn.execute(
                """
                UPDATE action_request
                SET status = ?,
                    result_json = ?,
                    approved_by = COALESCE(?, approved_by),
                    approved_at = CASE WHEN ? IS NOT NULL THEN ? ELSE approved_at END,
                    rejection_reason = COALESCE(?, rejection_reason),
                    updated_at = ?
                WHERE action_id = ?
                """,
                (
                    status,
                    _canonical_json(result),
                    approved_by,
                    approved_by,
                    now,
                    rejection_reason,
                    now,
                    action_id,
                ),
            )

            if status in {"approved", "rejected", "completed", "failed"}:
                queue_status = "approved" if status in {"approved", "completed"} else "rejected"
                conn.execute(
                    """
                    UPDATE approval_queue
                    SET status = ?,
                        decided_by = COALESCE(?, decided_by),
                        decided_at = COALESCE(decided_at, ?),
                        decision_note = COALESCE(?, decision_note)
                    WHERE action_id = ?
                    """,
                    (queue_status, approved_by, now, rejection_reason, action_id),
                )

            payload = {
                "status": status,
                "result": result,
                "approved_by": approved_by,
                "rejection_reason": rejection_reason,
            }

        self.append_audit_event(
            event_type="action.write.result",
            action_id=action_id,
            source_id=row["source_id"],
            entity_type=row["entity_type"],
            payload=payload,
        )

        return self.get_action_request(action_id)

    def get_action_request(self, action_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT action_id, source_id, entity_type, payload_json, payload_hash,
                       idempotency_key, status, risk_level, policy_version,
                       policy_decision_json, requires_approval,
                       approved_by, approved_at, rejection_reason,
                       created_at, updated_at, result_json
                FROM action_request
                WHERE action_id = ?
                """,
                (action_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "action_id": row["action_id"],
            "source_id": row["source_id"],
            "entity_type": row["entity_type"],
            "payload": json.loads(row["payload_json"]),
            "payload_hash": row["payload_hash"],
            "idempotency_key": row["idempotency_key"],
            "status": row["status"],
            "risk_level": row["risk_level"],
            "policy_version": row["policy_version"],
            "policy_decision": json.loads(row["policy_decision_json"]),
            "requires_approval": bool(row["requires_approval"]),
            "approved_by": row["approved_by"],
            "approved_at": row["approved_at"],
            "rejection_reason": row["rejection_reason"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "result": (json.loads(row["result_json"]) if row["result_json"] else None),
        }

    def list_approval_queue(self, status: str = "pending", limit: int = 100) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT action_id, source_id, entity_type, reason,
                       status, requested_by, requested_at,
                       decided_by, decided_at, decision_note
                FROM approval_queue
                WHERE status = ?
                ORDER BY requested_at DESC
                LIMIT ?
                """,
                (status, _parse_limit(limit, max_value=1000)),
            ).fetchall()

        return [
            {
                "action_id": r["action_id"],
                "source_id": r["source_id"],
                "entity_type": r["entity_type"],
                "reason": r["reason"],
                "status": r["status"],
                "requested_by": r["requested_by"],
                "requested_at": r["requested_at"],
                "decided_by": r["decided_by"],
                "decided_at": r["decided_at"],
                "decision_note": r["decision_note"],
            }
            for r in rows
        ]

    def list_actions(self, *, status: str | None = None, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = """
            SELECT action_id, source_id, entity_type, payload_json, payload_hash,
                   idempotency_key, status, risk_level, policy_version,
                   policy_decision_json, requires_approval,
                   approved_by, approved_at, rejection_reason,
                   created_at, updated_at, result_json
            FROM action_request
            WHERE 1 = 1
        """
        params: list[Any] = []
        if status:
            query += " AND status = ?"
            params.append(status)
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(_parse_limit(limit, max_value=1000))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "action_id": row["action_id"],
                    "source_id": row["source_id"],
                    "entity_type": row["entity_type"],
                    "payload": json.loads(row["payload_json"]),
                    "payload_hash": row["payload_hash"],
                    "idempotency_key": row["idempotency_key"],
                    "status": row["status"],
                    "risk_level": row["risk_level"],
                    "policy_version": row["policy_version"],
                    "policy_decision": json.loads(row["policy_decision_json"]),
                    "requires_approval": bool(row["requires_approval"]),
                    "approved_by": row["approved_by"],
                    "approved_at": row["approved_at"],
                    "rejection_reason": row["rejection_reason"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "result": (json.loads(row["result_json"]) if row["result_json"] else None),
                }
            )
        return out

    def list_audit_events(self, limit: int = 100, action_id: str | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, event_type, action_id, source_id, entity_type,
                   payload_json, recorded_at, prev_hash, row_hash
            FROM actions_audit_ledger
            WHERE 1 = 1
        """
        params: list[Any] = []
        if action_id:
            query += " AND action_id = ?"
            params.append(action_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(_parse_limit(limit, max_value=2000))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return [
            {
                "id": int(r["id"]),
                "event_type": r["event_type"],
                "action_id": r["action_id"],
                "source_id": r["source_id"],
                "entity_type": r["entity_type"],
                "payload": json.loads(r["payload_json"]),
                "recorded_at": r["recorded_at"],
                "prev_hash": r["prev_hash"],
                "row_hash": r["row_hash"],
            }
            for r in rows
        ]


def get_actions_store() -> ActionsStore:
    db_path = os.getenv("ACTIONS_DB_PATH", "/tmp/evieai_actions.db")
    return ActionsStore(db_path=db_path)
