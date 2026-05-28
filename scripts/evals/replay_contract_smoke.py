#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Any

import httpx


def _base_url() -> str:
    return os.getenv("ORCHESTRATOR_BASE_URL", "http://localhost:8000").rstrip("/")


def _request(method: str, path: str, payload: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    url = f"{_base_url()}{path}"
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        resp = client.request(method, url, json=payload)
    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text[:500]}
    return resp.status_code, body


def main() -> int:
    source_id = os.getenv("EVAL_SOURCE_ID", "propexo")
    entity_type = os.getenv("EVAL_ENTITY_TYPE", "resident")

    status, body = _request(
        "POST",
        f"/connectors/{source_id}/sync",
        {
            "entity_type": entity_type,
            "limit": 5,
            "use_saved_cursor": False,
            "idempotency_key": "eval-replay-contract-1",
        },
    )

    if status != 200:
        print(f"[replay-contract] sync failed status={status} body={body}")
        return 1

    required = {"run_id", "source_id", "entity_type", "count", "persisted", "duplicate", "records"}
    missing = sorted(required - set(body.keys()))
    if missing:
        print(f"[replay-contract] missing fields: {missing}")
        return 1

    status2, dead = _request("GET", "/connectors/sync/runs?status=pending&limit=5")
    if status2 != 200:
        print(f"[replay-contract] dead-letter list failed status={status2} body={dead}")
        return 1

    if "dead_letters" not in dead:
        print(f"[replay-contract] invalid dead-letter payload: {dead}")
        return 1

    print(
        json.dumps(
            {
                "pass": True,
                "sync_contract": {"status": status, "fields": sorted(body.keys())},
                "dead_letter_contract": {"status": status2, "keys": sorted(dead.keys())},
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
