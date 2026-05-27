from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger("orchestrator.bitemporal")


PersistResult = Dict[str, Any]


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class BaseBitemporalStore:
    backend = "base"

    def persist_page(
        self,
        *,
        source_id: str,
        entity_type: str,
        records: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> PersistResult:
        raise NotImplementedError


class SqliteBitemporalStore(BaseBitemporalStore):
    backend = "sqlite"

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
                CREATE TABLE IF NOT EXISTS ingest_dedupe (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    source_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    payload_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

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

    def _is_duplicate(
        self,
        conn: sqlite3.Connection,
        *,
        source_id: str,
        entity_type: str,
        idempotency_key: str | None,
        payload_hash: str,
    ) -> bool:
        if not idempotency_key:
            return False

        row = conn.execute(
            "SELECT id FROM ingest_dedupe WHERE idempotency_key = ?",
            (idempotency_key,),
        ).fetchone()
        if row:
            return True

        conn.execute(
            """
            INSERT INTO ingest_dedupe (idempotency_key, source_id, entity_type, payload_hash, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (idempotency_key, source_id, entity_type, payload_hash, _utcnow_iso()),
        )
        return False

    def persist_page(
        self,
        *,
        source_id: str,
        entity_type: str,
        records: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> PersistResult:
        if not records:
            return {"persisted": 0, "duplicate": False, "backend": self.backend}

        payload_hash = _digest({"source_id": source_id, "entity_type": entity_type, "records": records})
        inserted = 0

        with self._connect() as conn:
            if self._is_duplicate(
                conn,
                source_id=source_id,
                entity_type=entity_type,
                idempotency_key=idempotency_key,
                payload_hash=payload_hash,
            ):
                return {
                    "persisted": 0,
                    "duplicate": True,
                    "backend": self.backend,
                    "idempotency_key": idempotency_key,
                }

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

        return {
            "persisted": inserted,
            "duplicate": False,
            "backend": self.backend,
            "idempotency_key": idempotency_key,
        }


class PostgresBitemporalStore(BaseBitemporalStore):
    backend = "postgres"

    def __init__(self, dsn: str, migration_sql_path: str | None = None, auto_migrate: bool = True) -> None:
        try:
            import psycopg  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("psycopg is required for Postgres bitemporal backend") from exc

        self.psycopg = psycopg
        self.dsn = dsn
        self.migration_sql_path = migration_sql_path
        self.auto_migrate = auto_migrate
        if auto_migrate:
            self._run_migrations()

    def _connect(self):
        return self.psycopg.connect(self.dsn)

    def _run_migrations(self) -> None:
        sql_path = self.migration_sql_path
        if not sql_path:
            return
        file_path = Path(sql_path)
        if not file_path.exists():
            raise RuntimeError(f"Bitemporal migration file not found: {sql_path}")

        sql_text = file_path.read_text(encoding="utf-8")
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
            conn.commit()

    def _is_duplicate(
        self,
        cur,
        *,
        source_id: str,
        entity_type: str,
        idempotency_key: str | None,
        payload_hash: str,
    ) -> bool:
        if not idempotency_key:
            return False

        cur.execute("SELECT 1 FROM ingest_dedupe WHERE idempotency_key = %s", (idempotency_key,))
        if cur.fetchone():
            return True

        cur.execute(
            """
            INSERT INTO ingest_dedupe (idempotency_key, source_id, entity_type, payload_hash, created_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (idempotency_key, source_id, entity_type, payload_hash),
        )
        return False

    def persist_page(
        self,
        *,
        source_id: str,
        entity_type: str,
        records: list[dict[str, Any]],
        idempotency_key: str | None = None,
    ) -> PersistResult:
        if not records:
            return {"persisted": 0, "duplicate": False, "backend": self.backend}

        payload_hash = _digest({"source_id": source_id, "entity_type": entity_type, "records": records})
        inserted = 0

        with self._connect() as conn:
            with conn.cursor() as cur:
                if self._is_duplicate(
                    cur,
                    source_id=source_id,
                    entity_type=entity_type,
                    idempotency_key=idempotency_key,
                    payload_hash=payload_hash,
                ):
                    conn.commit()
                    return {
                        "persisted": 0,
                        "duplicate": True,
                        "backend": self.backend,
                        "idempotency_key": idempotency_key,
                    }

                for record in records:
                    source_record_id = record.get("source_record_id")
                    if not source_record_id:
                        continue

                    canonical = record.get("canonical") or {}
                    payload = record.get("payload") or {}
                    valid_from = record.get("updated_at") or _utcnow_iso()
                    recorded_at = _utcnow_iso()

                    cur.execute(
                        """
                        UPDATE entity_snapshot
                           SET superseded_at = %s
                         WHERE source_id = %s
                           AND entity_type = %s
                           AND source_record_id = %s
                           AND superseded_at IS NULL
                        """,
                        (recorded_at, source_id, entity_type, str(source_record_id)),
                    )

                    cur.execute(
                        """
                        INSERT INTO entity_snapshot (
                            source_id, entity_type, source_record_id,
                            canonical_json, payload_json, confidence,
                            valid_from, valid_to, recorded_at, superseded_at, created_at
                        ) VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s::timestamptz, NULL, %s::timestamptz, NULL, %s::timestamptz)
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
                        cur.execute(
                            """
                            INSERT INTO entity_fact (
                                source_id, entity_type, source_record_id,
                                fact_key, fact_value_json,
                                valid_from, valid_to, recorded_at, superseded_at, created_at
                            ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::timestamptz, NULL, %s::timestamptz, NULL, %s::timestamptz)
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

                    cur.execute("SELECT row_hash FROM audit_ledger ORDER BY id DESC LIMIT 1")
                    row = cur.fetchone()
                    prev_hash = str(row[0]) if row else None
                    ledger_payload = {
                        "canonical": canonical,
                        "payload": payload,
                        "valid_from": valid_from,
                        "recorded_at": recorded_at,
                    }
                    payload_json = json.dumps(ledger_payload, sort_keys=True, separators=(",", ":"))
                    digest_input = (
                        f"connector.fetch.persist|{source_id}|{entity_type}|{source_record_id}|{recorded_at}|{prev_hash or ''}|{payload_json}"
                    )
                    row_hash = hashlib.sha256(digest_input.encode("utf-8")).hexdigest()

                    cur.execute(
                        """
                        INSERT INTO audit_ledger (
                            event_type, source_id, entity_type, source_record_id,
                            payload_json, recorded_at, prev_hash, row_hash
                        ) VALUES (%s, %s, %s, %s, %s::jsonb, %s::timestamptz, %s, %s)
                        """,
                        (
                            "connector.fetch.persist",
                            source_id,
                            entity_type,
                            str(source_record_id),
                            payload_json,
                            recorded_at,
                            prev_hash,
                            row_hash,
                        ),
                    )
                    inserted += 1

            conn.commit()

        return {
            "persisted": inserted,
            "duplicate": False,
            "backend": self.backend,
            "idempotency_key": idempotency_key,
        }


def get_bitemporal_store() -> BaseBitemporalStore:
    backend = os.getenv("BITEMPORAL_BACKEND", "sqlite").strip().lower()

    if backend == "postgres":
        dsn = os.getenv("BITEMPORAL_POSTGRES_DSN") or os.getenv("DATABASE_URL")
        if not dsn:
            raise RuntimeError("BITEMPORAL_BACKEND=postgres but no BITEMPORAL_POSTGRES_DSN/DATABASE_URL provided")
        migration_sql_path = os.getenv(
            "BITEMPORAL_MIGRATION_SQL_PATH",
            str(Path(__file__).resolve().parents[2] / "db" / "migrations" / "0002_bitemporal_runtime_postgres.sql"),
        )
        auto_migrate = os.getenv("BITEMPORAL_AUTO_MIGRATE", "true").lower() in {"1", "true", "yes", "on"}
        return PostgresBitemporalStore(dsn=dsn, migration_sql_path=migration_sql_path, auto_migrate=auto_migrate)

    db_path = os.getenv("BITEMPORAL_DB_PATH", "/tmp/evieai_bitemporal.db")
    return SqliteBitemporalStore(db_path=db_path)
