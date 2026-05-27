from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("orchestrator.bitemporal")


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


class BitemporalStore:
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
                CREATE TABLE IF NOT EXISTS entity_snapshot (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    canonical_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    confidence REAL NOT NULL DEFAULT 1.0,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    recorded_at TEXT NOT NULL,
                    superseded_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_id, entity_type, source_record_id, recorded_at)
                );

                CREATE INDEX IF NOT EXISTS idx_entity_snapshot_lookup
                ON entity_snapshot(source_id, entity_type, source_record_id, recorded_at DESC);

                CREATE TABLE IF NOT EXISTS entity_fact (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    fact_key TEXT NOT NULL,
                    fact_value_json TEXT,
                    valid_from TEXT NOT NULL,
                    valid_to TEXT,
                    recorded_at TEXT NOT NULL,
                    superseded_at TEXT,
                    created_at TEXT NOT NULL,
                    UNIQUE(source_id, entity_type, source_record_id, fact_key, recorded_at)
                );

                CREATE INDEX IF NOT EXISTS idx_entity_fact_lookup
                ON entity_fact(source_id, entity_type, source_record_id, fact_key, recorded_at DESC);

                CREATE TABLE IF NOT EXISTS audit_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    source_id TEXT,
                    entity_type TEXT,
                    source_record_id TEXT,
                    payload_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    prev_hash TEXT,
                    row_hash TEXT NOT NULL
                );
                """
            )

    def _last_ledger_hash(self, conn: sqlite3.Connection) -> str | None:
        row = conn.execute("SELECT row_hash FROM audit_ledger ORDER BY id DESC LIMIT 1").fetchone()
        return str(row["row_hash"]) if row else None

    def _insert_ledger(
        self,
        conn: sqlite3.Connection,
        *,
        event_type: str,
        source_id: str,
        entity_type: str,
        source_record_id: str,
        payload: dict[str, Any],
    ) -> None:
        recorded_at = _utcnow_iso()
        prev_hash = self._last_ledger_hash(conn)
        payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest_input = f"{event_type}|{source_id}|{entity_type}|{source_record_id}|{recorded_at}|{prev_hash or ''}|{payload_json}"
        row_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

        conn.execute(
            """
            INSERT INTO audit_ledger (event_type, source_id, entity_type, source_record_id, payload_json, recorded_at, prev_hash, row_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (event_type, source_id, entity_type, source_record_id, payload_json, recorded_at, prev_hash, row_hash),
        )

    def persist_page(self, *, source_id: str, entity_type: str, records: list[dict[str, Any]]) -> int:
        if not records:
            return 0

        inserted = 0
        with self._connect() as conn:
            for record in records:
                source_record_id = record.get("source_record_id")
                if not source_record_id:
                    continue

                canonical = record.get("canonical") or {}
                payload = record.get("payload") or {}
                valid_from = record.get("updated_at") or _utcnow_iso()
                recorded_at = _utcnow_iso()

                existing = conn.execute(
                    """
                    SELECT id
                    FROM entity_snapshot
                    WHERE source_id = ? AND entity_type = ? AND source_record_id = ? AND superseded_at IS NULL
                    ORDER BY recorded_at DESC
                    LIMIT 1
                    """,
                    (source_id, entity_type, str(source_record_id)),
                ).fetchone()

                if existing:
                    conn.execute(
                        "UPDATE entity_snapshot SET superseded_at = ? WHERE id = ?",
                        (recorded_at, int(existing["id"])),
                    )

                conn.execute(
                    """
                    INSERT INTO entity_snapshot (
                        source_id, entity_type, source_record_id,
                        canonical_json, payload_json, confidence,
                        valid_from, valid_to, recorded_at, superseded_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?)
                    """,
                    (
                        source_id,
                        entity_type,
                        str(source_record_id),
                        json.dumps(canonical, separators=(",", ":")),
                        json.dumps(payload, separators=(",", ":")),
                        float(record.get("confidence", 1.0)),
                        str(valid_from),
                        recorded_at,
                        recorded_at,
                    ),
                )

                for fact_key, fact_value in canonical.items():
                    conn.execute(
                        """
                        INSERT INTO entity_fact (
                            source_id, entity_type, source_record_id,
                            fact_key, fact_value_json,
                            valid_from, valid_to, recorded_at, superseded_at, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?)
                        """,
                        (
                            source_id,
                            entity_type,
                            str(source_record_id),
                            str(fact_key),
                            json.dumps(fact_value, separators=(",", ":")),
                            str(valid_from),
                            recorded_at,
                            recorded_at,
                        ),
                    )

                self._insert_ledger(
                    conn,
                    event_type="connector.fetch.persist",
                    source_id=source_id,
                    entity_type=entity_type,
                    source_record_id=str(source_record_id),
                    payload={
                        "canonical": canonical,
                        "payload": payload,
                        "valid_from": valid_from,
                        "recorded_at": recorded_at,
                    },
                )
                inserted += 1

        return inserted


def get_bitemporal_store() -> BitemporalStore:
    db_path = os.getenv("BITEMPORAL_DB_PATH", "/tmp/evieai_bitemporal.db")
    return BitemporalStore(db_path=db_path)
