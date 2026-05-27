from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


class EventSignalStore:
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
                CREATE TABLE IF NOT EXISTS connector_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    received_at TEXT NOT NULL,
                    signature_valid INTEGER NOT NULL DEFAULT 1
                );

                CREATE INDEX IF NOT EXISTS idx_connector_event_source
                    ON connector_event(source_id, entity_type, received_at DESC);

                CREATE TABLE IF NOT EXISTS signal_entity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER NOT NULL,
                    source_id TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    reason_chain_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(event_id) REFERENCES connector_event(id)
                );

                CREATE INDEX IF NOT EXISTS idx_signal_entity_source
                    ON signal_entity(source_id, signal_type, created_at DESC);
                """
            )

    def ingest_event(
        self,
        *,
        source_id: str,
        event_type: str,
        entity_type: str,
        source_record_id: str,
        payload: dict[str, Any],
        occurred_at: str,
        signature_valid: bool,
    ) -> dict[str, Any]:
        now = _utcnow_iso()
        generated = self._generate_signals(entity_type=entity_type, payload=payload)

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO connector_event (
                    source_id, event_type, entity_type, source_record_id,
                    payload_json, occurred_at, received_at, signature_valid
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source_id,
                    event_type,
                    entity_type,
                    source_record_id,
                    json.dumps(payload, separators=(",", ":")),
                    occurred_at,
                    now,
                    1 if signature_valid else 0,
                ),
            )
            event_id = int(cur.lastrowid)

            signal_ids: list[int] = []
            for item in generated:
                signal_cur = conn.execute(
                    """
                    INSERT INTO signal_entity (
                        event_id, source_id, signal_type, severity, confidence,
                        reason_chain_json, payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        source_id,
                        item["signal_type"],
                        item["severity"],
                        float(item["confidence"]),
                        json.dumps(item["reason_chain"], separators=(",", ":")),
                        json.dumps(item["payload"], separators=(",", ":")),
                        now,
                    ),
                )
                signal_ids.append(int(signal_cur.lastrowid))

        return {
            "event_id": event_id,
            "signal_ids": signal_ids,
            "signal_count": len(signal_ids),
            "received_at": now,
        }

    def list_events(self, *, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = """
            SELECT id, source_id, event_type, entity_type, source_record_id,
                   payload_json, occurred_at, received_at, signature_valid
            FROM connector_event
        """
        params: list[Any] = []
        if source_id:
            query += " WHERE source_id = ?"
            params.append(source_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": int(row["id"]),
                    "source_id": row["source_id"],
                    "event_type": row["event_type"],
                    "entity_type": row["entity_type"],
                    "source_record_id": row["source_record_id"],
                    "payload": json.loads(row["payload_json"]),
                    "occurred_at": row["occurred_at"],
                    "received_at": row["received_at"],
                    "signature_valid": bool(row["signature_valid"]),
                }
            )
        return out

    def list_signals(self, *, source_id: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = """
            SELECT id, event_id, source_id, signal_type, severity, confidence,
                   reason_chain_json, payload_json, created_at
            FROM signal_entity
        """
        params: list[Any] = []
        if source_id:
            query += " WHERE source_id = ?"
            params.append(source_id)
        query += " ORDER BY id DESC LIMIT ?"
        params.append(max(1, min(limit, 500)))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        out: list[dict[str, Any]] = []
        for row in rows:
            out.append(
                {
                    "id": int(row["id"]),
                    "event_id": int(row["event_id"]),
                    "source_id": row["source_id"],
                    "signal_type": row["signal_type"],
                    "severity": row["severity"],
                    "confidence": float(row["confidence"]),
                    "reason_chain": json.loads(row["reason_chain_json"]),
                    "payload": json.loads(row["payload_json"]),
                    "created_at": row["created_at"],
                }
            )
        return out

    def metrics(self) -> dict[str, Any]:
        with self._connect() as conn:
            events = conn.execute("SELECT COUNT(1) AS c FROM connector_event").fetchone()
            signals = conn.execute("SELECT COUNT(1) AS c FROM signal_entity").fetchone()
        return {
            "events_total": int(events["c"] if events else 0),
            "signals_total": int(signals["c"] if signals else 0),
        }

    def _generate_signals(self, *, entity_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []

        if entity_type == "lease":
            days_to_expiry = payload.get("days_to_expiry")
            if isinstance(days_to_expiry, (int, float)) and days_to_expiry <= 30:
                signals.append(
                    {
                        "signal_type": "lease_expiring_soon",
                        "severity": "high" if days_to_expiry <= 14 else "medium",
                        "confidence": 0.92,
                        "reason_chain": ["lease", "days_to_expiry<=30"],
                        "payload": {"days_to_expiry": days_to_expiry, "entity_type": entity_type},
                    }
                )

        if entity_type == "resident":
            balance = payload.get("balance")
            if isinstance(balance, (int, float)) and balance > 0:
                signals.append(
                    {
                        "signal_type": "resident_balance_due",
                        "severity": "medium" if balance < 1000 else "high",
                        "confidence": 0.9,
                        "reason_chain": ["resident", "balance>0"],
                        "payload": {"balance": balance, "entity_type": entity_type},
                    }
                )

        if not signals:
            signals.append(
                {
                    "signal_type": "entity_change_observed",
                    "severity": "low",
                    "confidence": 0.8,
                    "reason_chain": [entity_type, "default_change_detection"],
                    "payload": {"entity_type": entity_type},
                }
            )

        return signals


def get_event_signal_store() -> EventSignalStore:
    db_path = os.getenv("EVENT_SIGNAL_DB_PATH", "/tmp/evieai_event_signal.db")
    return EventSignalStore(db_path=db_path)
