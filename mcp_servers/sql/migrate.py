"""Simple SQL migration runner for the SQL MCP server.

Reads .up.sql files from mcp_servers/sql/migrations/ and applies them in order.
Tracks applied migrations in a _migrations table. Safe to run repeatedly — each
migration runs at most once.

Usage:
    python mcp_servers/sql/migrate.py          # apply all pending migrations
    python mcp_servers/sql/migrate.py --down   # revert the last migration

Requires:
    DATABASE_CONNECTION_STRING environment variable (same format as seed.py)
"""

from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path
from typing import Any

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def _parse_conn(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _connect(raw: str) -> Any:
    parms = _parse_conn(raw)
    server = parms.get("Server", "").replace("tcp:", "")
    database = parms.get("Initial Catalog", "")
    uid = parms.get("User ID", "")
    pwd = parms.get("Password", "")
    driver = "{ODBC Driver 18 for SQL Server}"

    odbc = (
        f"DRIVER={driver};"
        f"SERVER={server},1433;DATABASE={database};UID={uid};PWD={pwd};"
        f"Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
    )

    import pyodbc

    for attempt in range(1, 7):
        try:
            return pyodbc.connect(odbc, timeout=60)
        except pyodbc.Error as e:
            print(f"Connection attempt {attempt}/6 failed: {e}")
            time.sleep(15)
    raise RuntimeError("Could not connect after 6 attempts.")


def ensure_migrations_table(cursor: Any) -> None:
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '_migrations')
        CREATE TABLE _migrations (
            id INT IDENTITY(1,1) PRIMARY KEY,
            name NVARCHAR(200) NOT NULL UNIQUE,
            applied_at DATETIME2 DEFAULT SYSUTCDATETIME()
        )
    """)


def applied_migrations(cursor: Any) -> set[str]:
    cursor.execute("SELECT name FROM _migrations ORDER BY id")
    return {row[0] for row in cursor.fetchall()}


def run_migrations(conn: Any, direction: str = "up") -> bool:
    cursor = conn.cursor()
    ensure_migrations_table(cursor)
    conn.commit()

    applied = applied_migrations(cursor)
    suffix = f".{direction}.sql"
    migrations = sorted(
        (f for f in MIGRATIONS_DIR.iterdir() if f.name.endswith(suffix)),
        key=lambda f: f.name,
    )

    if direction == "down":
        migrations = list(reversed(migrations))

    for mfile in migrations:
        name = mfile.name
        base = name.replace(suffix, "")
        if direction == "up" and base in applied:
            continue
        if direction == "down" and base not in applied:
            continue

        print(f"Applying: {name}")
        sql = mfile.read_text(encoding="utf-8")
        for stmt in re.split(r";\s*\n", sql):
            stmt = stmt.strip()
            if stmt and not stmt.startswith("--"):
                try:
                    cursor.execute(stmt)
                except Exception as exc:
                    print(f"  ERROR: {exc}")
                    conn.rollback()
                    return False

        if direction == "up":
            cursor.execute("INSERT INTO _migrations (name) VALUES (?)", base)
        elif direction == "down":
            cursor.execute("DELETE FROM _migrations WHERE name = ?", base)
        conn.commit()
    return True


def main() -> None:
    raw = os.environ.get("DATABASE_CONNECTION_STRING", "")
    if not raw:
        print("DATABASE_CONNECTION_STRING not set.")
        sys.exit(1)

    direction = "down" if "--down" in sys.argv else "up"
    conn = _connect(raw)
    try:
        ok = run_migrations(conn, direction)
        sys.exit(0 if ok else 1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
