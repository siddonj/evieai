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


PersistResult = dict[str, Any]


def _utcnow_iso() -> str:
    return datetime.utcnow().isoformat(timespec="microseconds") + "Z"


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _iso_to_epoch(value: str | None) -> float | None:
    if not value:
        return None
    try:
        v = value
        if v.endswith("Z"):
            v = v[:-1] + "+00:00"
        return datetime.fromisoformat(v).timestamp()
    except Exception:
        return None


def _now_epoch() -> float:
    return datetime.utcnow().timestamp()


def _json_loads(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return value
    return value


def _stable_json_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_limit(value: int, *, default: int = 100, min_value: int = 1, max_value: int = 1000) -> int:
    return max(min_value, min(max_value, value if isinstance(value, int) else default))


def _to_freshness(rows: list[dict[str, Any]]) -> dict[str, Any]:
    now = _now_epoch()
    out_rows: list[dict[str, Any]] = []
    max_lag = 0.0
    for row in rows:
        latest = row.get("latest_recorded_at")
        epoch = _iso_to_epoch(latest)
        lag = max(0.0, now - epoch) if epoch is not None else None
        if lag is not None and lag > max_lag:
            max_lag = lag
        out_rows.append(
            {
                "source_id": row.get("source_id"),
                "entity_type": row.get("entity_type"),
                "latest_recorded_at": latest,
                "record_count": int(row.get("record_count", 0)),
                "freshness_lag_seconds": lag,
            }
        )

    return {
        "count": len(out_rows),
        "max_freshness_lag_seconds": max_lag,
        "rows": out_rows,
    }


def _build_diff(
    *,
    before_rows: list[dict[str, Any]],
    after_rows: list[dict[str, Any]],
    t1: str,
    t2: str,
) -> dict[str, Any]:
    before_map = {str(r.get("source_record_id")): r for r in before_rows}
    after_map = {str(r.get("source_record_id")): r for r in after_rows}

    added: list[str] = []
    removed: list[str] = []
    changed: list[dict[str, Any]] = []

    for key in sorted(set(before_map.keys()) | set(after_map.keys())):
        b = before_map.get(key)
        a = after_map.get(key)
        if b is None and a is not None:
            added.append(key)
            continue
        if a is None and b is not None:
            removed.append(key)
            continue

        assert a is not None and b is not None
        b_hash = _stable_json_hash(b.get("canonical") or {})
        a_hash = _stable_json_hash(a.get("canonical") or {})
        if b_hash != a_hash:
            changed.append(
                {
                    "source_record_id": key,
                    "before_hash": b_hash,
                    "after_hash": a_hash,
                    "before": b.get("canonical") or {},
                    "after": a.get("canonical") or {},
                }
            )

    return {
        "t1": t1,
        "t2": t2,
        "added": added,
        "removed": removed,
        "changed": changed,
        "counts": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
        },
    }


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

    def get_connector_freshness(
        self,
        *,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_entity_lineage(
        self,
        *,
        source_id: str,
        entity_type: str,
        source_record_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def get_confidence_breakdown(
        self,
        *,
        source_id: str | None = None,
        entity_type: str | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def query_as_of(
        self,
        *,
        as_of: str,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        raise NotImplementedError

    def diff_between(
        self,
        *,
        t1: str,
        t2: str,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
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


    def get_connector_freshness(
        self,
        *,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        query = """
            SELECT source_id,
                   entity_type,
                   MAX(recorded_at) AS latest_recorded_at,
                   COUNT(1) AS record_count
            FROM entity_snapshot
            WHERE 1 = 1
        """
        params: list[Any] = []
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        query += " GROUP BY source_id, entity_type ORDER BY latest_recorded_at DESC LIMIT ?"
        params.append(_parse_limit(limit))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        return _to_freshness([dict(r) for r in rows])

    def get_entity_lineage(
        self,
        *,
        source_id: str,
        entity_type: str,
        source_record_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            snapshots = conn.execute(
                """
                SELECT source_id, entity_type, source_record_id,
                       canonical_json, payload_json, confidence,
                       valid_from, valid_to, recorded_at, superseded_at, created_at
                FROM entity_snapshot
                WHERE source_id = ? AND entity_type = ? AND source_record_id = ?
                ORDER BY recorded_at DESC
                LIMIT ?
                """,
                (source_id, entity_type, source_record_id, _parse_limit(limit, max_value=500)),
            ).fetchall()

            ledger = conn.execute(
                """
                SELECT event_type, recorded_at, row_hash, prev_hash, payload_json
                FROM audit_ledger
                WHERE source_id = ? AND entity_type = ? AND source_record_id = ?
                ORDER BY recorded_at DESC
                LIMIT ?
                """,
                (source_id, entity_type, source_record_id, _parse_limit(limit, max_value=500)),
            ).fetchall()

        snapshot_rows = []
        for row in snapshots:
            snapshot_rows.append(
                {
                    "source_id": row["source_id"],
                    "entity_type": row["entity_type"],
                    "source_record_id": row["source_record_id"],
                    "canonical": _json_loads(row["canonical_json"]),
                    "payload": _json_loads(row["payload_json"]),
                    "confidence": float(row["confidence"]),
                    "valid_from": row["valid_from"],
                    "valid_to": row["valid_to"],
                    "recorded_at": row["recorded_at"],
                    "superseded_at": row["superseded_at"],
                    "created_at": row["created_at"],
                }
            )

        ledger_rows = []
        for row in ledger:
            ledger_rows.append(
                {
                    "event_type": row["event_type"],
                    "recorded_at": row["recorded_at"],
                    "row_hash": row["row_hash"],
                    "prev_hash": row["prev_hash"],
                    "payload": _json_loads(row["payload_json"]),
                }
            )

        return {
            "source_id": source_id,
            "entity_type": entity_type,
            "source_record_id": source_record_id,
            "snapshot_versions": snapshot_rows,
            "audit_events": ledger_rows,
        }

    def get_confidence_breakdown(
        self,
        *,
        source_id: str | None = None,
        entity_type: str | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT source_id,
                   entity_type,
                   COUNT(1) AS sample_size,
                   AVG(confidence) AS avg_confidence,
                   MIN(confidence) AS min_confidence,
                   MAX(confidence) AS max_confidence
            FROM entity_snapshot
            WHERE superseded_at IS NULL
        """
        params: list[Any] = []
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        query += " GROUP BY source_id, entity_type ORDER BY source_id, entity_type"

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        groups = []
        for row in rows:
            groups.append(
                {
                    "source_id": row["source_id"],
                    "entity_type": row["entity_type"],
                    "sample_size": int(row["sample_size"]),
                    "avg_confidence": float(row["avg_confidence"]),
                    "min_confidence": float(row["min_confidence"]),
                    "max_confidence": float(row["max_confidence"]),
                }
            )
        return {"count": len(groups), "groups": groups}

    def query_as_of(
        self,
        *,
        as_of: str,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        query = """
            SELECT source_id, entity_type, source_record_id,
                   canonical_json, payload_json, confidence,
                   valid_from, valid_to, recorded_at, superseded_at, created_at
            FROM entity_snapshot
            WHERE recorded_at <= ?
              AND (superseded_at IS NULL OR superseded_at > ?)
        """
        params: list[Any] = [as_of, as_of]
        if source_id:
            query += " AND source_id = ?"
            params.append(source_id)
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        query += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(_parse_limit(limit, max_value=1000))

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()

        records = []
        for row in rows:
            records.append(
                {
                    "source_id": row["source_id"],
                    "entity_type": row["entity_type"],
                    "source_record_id": row["source_record_id"],
                    "canonical": _json_loads(row["canonical_json"]),
                    "payload": _json_loads(row["payload_json"]),
                    "confidence": float(row["confidence"]),
                    "valid_from": row["valid_from"],
                    "valid_to": row["valid_to"],
                    "recorded_at": row["recorded_at"],
                    "superseded_at": row["superseded_at"],
                    "created_at": row["created_at"],
                }
            )

        return {"as_of": as_of, "count": len(records), "records": records}

    def diff_between(
        self,
        *,
        t1: str,
        t2: str,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        before = self.query_as_of(as_of=t1, source_id=source_id, entity_type=entity_type, limit=limit)
        after = self.query_as_of(as_of=t2, source_id=source_id, entity_type=entity_type, limit=limit)
        return _build_diff(
            before_rows=before.get("records", []),
            after_rows=after.get("records", []),
            t1=t1,
            t2=t2,
        )


class PostgresBitemporalStore(BaseBitemporalStore):
    backend = "postgres"

    def get_connector_freshness(
        self,
        *,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        query = """
            SELECT source_id,
                   entity_type,
                   MAX(recorded_at) AS latest_recorded_at,
                   COUNT(1) AS record_count
            FROM entity_snapshot
            WHERE 1 = 1
        """
        params: list[Any] = []
        if source_id:
            query += " AND source_id = %s"
            params.append(source_id)
        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)
        query += " GROUP BY source_id, entity_type ORDER BY latest_recorded_at DESC LIMIT %s"
        params.append(_parse_limit(limit))

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = [
                    {
                        "source_id": r[0],
                        "entity_type": r[1],
                        "latest_recorded_at": r[2].isoformat() if hasattr(r[2], "isoformat") else str(r[2]),
                        "record_count": int(r[3]),
                    }
                    for r in cur.fetchall()
                ]

        return _to_freshness(rows)

    def get_entity_lineage(
        self,
        *,
        source_id: str,
        entity_type: str,
        source_record_id: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT source_id, entity_type, source_record_id,
                           canonical_json, payload_json, confidence,
                           valid_from, valid_to, recorded_at, superseded_at, created_at
                    FROM entity_snapshot
                    WHERE source_id = %s AND entity_type = %s AND source_record_id = %s
                    ORDER BY recorded_at DESC
                    LIMIT %s
                    """,
                    (source_id, entity_type, source_record_id, _parse_limit(limit, max_value=500)),
                )
                snapshots = cur.fetchall()

                cur.execute(
                    """
                    SELECT event_type, recorded_at, row_hash, prev_hash, payload_json
                    FROM audit_ledger
                    WHERE source_id = %s AND entity_type = %s AND source_record_id = %s
                    ORDER BY recorded_at DESC
                    LIMIT %s
                    """,
                    (source_id, entity_type, source_record_id, _parse_limit(limit, max_value=500)),
                )
                ledger = cur.fetchall()

        snapshot_rows = [
            {
                "source_id": r[0],
                "entity_type": r[1],
                "source_record_id": r[2],
                "canonical": _json_loads(r[3]),
                "payload": _json_loads(r[4]),
                "confidence": float(r[5]),
                "valid_from": r[6].isoformat() if hasattr(r[6], "isoformat") else str(r[6]),
                "valid_to": (r[7].isoformat() if hasattr(r[7], "isoformat") and r[7] is not None else r[7]),
                "recorded_at": r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8]),
                "superseded_at": (r[9].isoformat() if hasattr(r[9], "isoformat") and r[9] is not None else r[9]),
                "created_at": r[10].isoformat() if hasattr(r[10], "isoformat") else str(r[10]),
            }
            for r in snapshots
        ]

        ledger_rows = [
            {
                "event_type": r[0],
                "recorded_at": r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1]),
                "row_hash": r[2],
                "prev_hash": r[3],
                "payload": _json_loads(r[4]),
            }
            for r in ledger
        ]

        return {
            "source_id": source_id,
            "entity_type": entity_type,
            "source_record_id": source_record_id,
            "snapshot_versions": snapshot_rows,
            "audit_events": ledger_rows,
        }

    def get_confidence_breakdown(
        self,
        *,
        source_id: str | None = None,
        entity_type: str | None = None,
    ) -> dict[str, Any]:
        query = """
            SELECT source_id,
                   entity_type,
                   COUNT(1) AS sample_size,
                   AVG(confidence) AS avg_confidence,
                   MIN(confidence) AS min_confidence,
                   MAX(confidence) AS max_confidence
            FROM entity_snapshot
            WHERE superseded_at IS NULL
        """
        params: list[Any] = []
        if source_id:
            query += " AND source_id = %s"
            params.append(source_id)
        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)
        query += " GROUP BY source_id, entity_type ORDER BY source_id, entity_type"

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        groups = [
            {
                "source_id": r[0],
                "entity_type": r[1],
                "sample_size": int(r[2]),
                "avg_confidence": float(r[3]),
                "min_confidence": float(r[4]),
                "max_confidence": float(r[5]),
            }
            for r in rows
        ]
        return {"count": len(groups), "groups": groups}

    def query_as_of(
        self,
        *,
        as_of: str,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        query = """
            SELECT source_id, entity_type, source_record_id,
                   canonical_json, payload_json, confidence,
                   valid_from, valid_to, recorded_at, superseded_at, created_at
            FROM entity_snapshot
            WHERE recorded_at <= %s::timestamptz
              AND (superseded_at IS NULL OR superseded_at > %s::timestamptz)
        """
        params: list[Any] = [as_of, as_of]
        if source_id:
            query += " AND source_id = %s"
            params.append(source_id)
        if entity_type:
            query += " AND entity_type = %s"
            params.append(entity_type)
        query += " ORDER BY recorded_at DESC LIMIT %s"
        params.append(_parse_limit(limit, max_value=1000))

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(params))
                rows = cur.fetchall()

        records = [
            {
                "source_id": r[0],
                "entity_type": r[1],
                "source_record_id": r[2],
                "canonical": _json_loads(r[3]),
                "payload": _json_loads(r[4]),
                "confidence": float(r[5]),
                "valid_from": r[6].isoformat() if hasattr(r[6], "isoformat") else str(r[6]),
                "valid_to": (r[7].isoformat() if hasattr(r[7], "isoformat") and r[7] is not None else r[7]),
                "recorded_at": r[8].isoformat() if hasattr(r[8], "isoformat") else str(r[8]),
                "superseded_at": (r[9].isoformat() if hasattr(r[9], "isoformat") and r[9] is not None else r[9]),
                "created_at": r[10].isoformat() if hasattr(r[10], "isoformat") else str(r[10]),
            }
            for r in rows
        ]

        return {"as_of": as_of, "count": len(records), "records": records}

    def diff_between(
        self,
        *,
        t1: str,
        t2: str,
        source_id: str | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        before = self.query_as_of(as_of=t1, source_id=source_id, entity_type=entity_type, limit=limit)
        after = self.query_as_of(as_of=t2, source_id=source_id, entity_type=entity_type, limit=limit)
        return _build_diff(
            before_rows=before.get("records", []),
            after_rows=after.get("records", []),
            t1=t1,
            t2=t2,
        )

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
