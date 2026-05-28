from __future__ import annotations

import os
from typing import Any

import asyncpg
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mcp-postgresql", version="0.1.0")

POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://postgres:postgres@postgres:5432/evieai")
MAX_ROWS = int(os.getenv("POSTGRES_MAX_ROWS", "200"))

_BLOCKED_SQL = (
    "insert ",
    "update ",
    "delete ",
    "drop ",
    "alter ",
    "truncate ",
    "create ",
    "grant ",
    "revoke ",
    "comment ",
)


class QueryRequest(BaseModel):
    query: str
    user_id: str | None = None


def _ensure_read_only(sql: str) -> str:
    clean = " ".join(sql.strip().split())
    lowered = clean.lower()
    if ";" in lowered:
        raise ValueError("Only single-statement read queries are allowed.")
    if not lowered.startswith(("select ", "with ")):
        raise ValueError("Only SELECT/CTE queries are allowed.")
    if any(token in lowered for token in _BLOCKED_SQL):
        raise ValueError("Query contains a blocked SQL keyword.")
    return clean


async def _run_query(sql: str) -> list[dict[str, Any]]:
    conn = await asyncpg.connect(dsn=POSTGRES_DSN)
    try:
        rows = await conn.fetch(sql)
        if len(rows) > MAX_ROWS:
            rows = rows[:MAX_ROWS]
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def _nl_to_query(query: str) -> str:
    q = query.lower()

    if q.startswith("sql:"):
        return _ensure_read_only(query[4:].strip())

    if any(word in q for word in ("table", "tables", "schema")):
        return (
            "SELECT table_name "
            "FROM information_schema.tables "
            "WHERE table_schema = 'public' "
            "ORDER BY table_name"
        )

    if any(word in q for word in ("extension", "extensions")):
        return "SELECT extname FROM pg_extension ORDER BY extname"

    if any(word in q for word in ("connection", "connections", "sessions")):
        return (
            "SELECT state, COUNT(*) AS connection_count "
            "FROM pg_stat_activity "
            "GROUP BY state "
            "ORDER BY connection_count DESC"
        )

    if any(word in q for word in ("leases", "residents", "work order", "work_orders", "charges", "units")):
        return (
            "SELECT table_name, n_live_tup AS estimated_rows "
            "FROM pg_stat_user_tables "
            "WHERE table_name IN ('leases','residents','work_orders','charges','units') "
            "ORDER BY table_name"
        )

    return (
        "SELECT schemaname, relname AS table_name, n_live_tup AS estimated_rows "
        "FROM pg_stat_user_tables "
        "ORDER BY n_live_tup DESC, relname "
        "LIMIT 25"
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-postgresql", "status": "ok"}


@app.get("/health")
async def health() -> dict[str, Any]:
    try:
        rows = await _run_query("SELECT current_database() AS database_name, version() AS pg_version")
        return {"status": "healthy", "database": rows[0] if rows else {}}
    except Exception as exc:  # noqa: BLE001
        return {"status": "unhealthy", "error": str(exc)}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "postgresql"}


@app.get("/admin/data")
async def admin_data() -> dict[str, Any]:
    rows = await _run_query(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema='public' ORDER BY table_name"
    )
    return {"service": "postgresql", "tables": rows}


@app.post("/mcp/query")
async def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    try:
        sql = await _nl_to_query(payload.query)
        rows = await _run_query(sql)
        return {
            "service": "postgresql",
            "query": payload.query,
            "sql": sql,
            "row_count": len(rows),
            "rows": rows,
            "summary": f"Returned {len(rows)} row(s) from PostgreSQL.",
        }
    except Exception as exc:  # noqa: BLE001
        return {"service": "postgresql", "query": payload.query, "error": str(exc)}
