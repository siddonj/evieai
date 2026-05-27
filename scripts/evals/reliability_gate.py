#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing metrics file: {path}")
    return json.loads(path.read_text())


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _evaluate(metrics: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    thresholds = metrics.get("thresholds", {})
    current = metrics.get("current", {})

    max_sync_lag = _to_float(thresholds.get("max_sync_lag_seconds", 1800), 1800)
    max_event_lag = _to_float(thresholds.get("max_event_lag_seconds", 600), 600)
    min_action_success = _to_float(thresholds.get("min_action_success_rate", 0.95), 0.95)
    max_hallucination = _to_float(thresholds.get("max_hallucination_rate", 0.02), 0.02)
    min_citation_accuracy = _to_float(thresholds.get("min_citation_accuracy", 0.95), 0.95)
    max_write_failures = _to_int(thresholds.get("max_write_failures", 5), 5)

    sync_lag = _to_float(current.get("sync_lag_seconds", 0), 0)
    event_lag = _to_float(current.get("event_lag_seconds", 0), 0)
    action_success = _to_float(current.get("action_success_rate", 1), 1)
    hallucination = _to_float(current.get("hallucination_rate", 0), 0)
    citation_accuracy = _to_float(current.get("citation_accuracy", 1), 1)
    write_failures = _to_int(current.get("write_failures", 0), 0)

    failures: list[str] = []
    if sync_lag > max_sync_lag:
        failures.append(f"sync_lag_seconds {sync_lag} > {max_sync_lag}")
    if event_lag > max_event_lag:
        failures.append(f"event_lag_seconds {event_lag} > {max_event_lag}")
    if action_success < min_action_success:
        failures.append(f"action_success_rate {action_success} < {min_action_success}")
    if hallucination > max_hallucination:
        failures.append(f"hallucination_rate {hallucination} > {max_hallucination}")
    if citation_accuracy < min_citation_accuracy:
        failures.append(f"citation_accuracy {citation_accuracy} < {min_citation_accuracy}")
    if write_failures > max_write_failures:
        failures.append(f"write_failures {write_failures} > {max_write_failures}")

    summary = {
        "pass": len(failures) == 0,
        "thresholds": {
            "max_sync_lag_seconds": max_sync_lag,
            "max_event_lag_seconds": max_event_lag,
            "min_action_success_rate": min_action_success,
            "max_hallucination_rate": max_hallucination,
            "min_citation_accuracy": min_citation_accuracy,
            "max_write_failures": max_write_failures,
        },
        "current": {
            "sync_lag_seconds": sync_lag,
            "event_lag_seconds": event_lag,
            "action_success_rate": action_success,
            "hallucination_rate": hallucination,
            "citation_accuracy": citation_accuracy,
            "write_failures": write_failures,
            "actions_total": _to_int(current.get("actions_total", 0), 0),
            "actions_completed": _to_int(current.get("actions_completed", 0), 0),
            "actions_failed": _to_int(current.get("actions_failed", 0), 0),
            "actions_pending_approval": _to_int(current.get("actions_pending_approval", 0), 0),
        },
        "failures": failures,
    }
    return len(failures) == 0, failures, summary


def _collect_action_metrics_from_db(actions_db_path: Path) -> dict[str, Any]:
    if not actions_db_path.exists():
        return {
            "actions_total": 0,
            "actions_completed": 0,
            "actions_failed": 0,
            "actions_pending_approval": 0,
            "action_success_rate": 1.0,
            "write_failures": 0,
        }

    with sqlite3.connect(str(actions_db_path)) as conn:
        conn.row_factory = sqlite3.Row

        def _count(query: str) -> int:
            row = conn.execute(query).fetchone()
            if row is None:
                return 0
            return int(row[0])

        total = _count("SELECT COUNT(1) FROM action_request")
        completed = _count("SELECT COUNT(1) FROM action_request WHERE status = 'completed'")
        failed = _count("SELECT COUNT(1) FROM action_request WHERE status = 'failed'")
        pending_approval = _count("SELECT COUNT(1) FROM approval_queue WHERE status = 'pending'")

    resolved = completed + failed
    success_rate = (completed / resolved) if resolved else 1.0
    return {
        "actions_total": total,
        "actions_completed": completed,
        "actions_failed": failed,
        "actions_pending_approval": pending_approval,
        "action_success_rate": round(success_rate, 6),
        "write_failures": failed,
    }


def _inject_live_action_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(metrics))
    current = merged.setdefault("current", {})
    thresholds = merged.setdefault("thresholds", {})

    actions_db_path = Path(os.getenv("ACTIONS_DB_PATH", "./data/evieai_actions.db"))
    live = _collect_action_metrics_from_db(actions_db_path)

    current["actions_total"] = live["actions_total"]
    current["actions_completed"] = live["actions_completed"]
    current["actions_failed"] = live["actions_failed"]
    current["actions_pending_approval"] = live["actions_pending_approval"]

    current["action_success_rate"] = _to_float(
        os.getenv("EVIEAI_ACTION_SUCCESS_RATE", live["action_success_rate"]),
        live["action_success_rate"],
    )
    current["write_failures"] = _to_int(
        os.getenv("EVIEAI_WRITE_FAILURES", live["write_failures"]),
        live["write_failures"],
    )

    thresholds["min_action_success_rate"] = _to_float(
        os.getenv("SLO_MIN_ACTION_SUCCESS_RATE", thresholds.get("min_action_success_rate", 0.95)),
        0.95,
    )
    thresholds["max_write_failures"] = _to_int(
        os.getenv("SLO_MAX_WRITE_FAILURES", thresholds.get("max_write_failures", 5)),
        5,
    )

    return merged


def main() -> int:
    metrics_file = Path(os.getenv("EVIEAI_RELIABILITY_METRICS_FILE", "scripts/evals/sample_metrics.json"))
    summary_out = Path(os.getenv("EVIEAI_RELIABILITY_SUMMARY_FILE", "scripts/evals/reliability_summary.json"))

    try:
        metrics = _inject_live_action_metrics(_load_json(metrics_file))
        ok, failures, summary = _evaluate(metrics)
    except Exception as exc:  # noqa: BLE001
        print(f"[reliability-gate] ERROR: {exc}")
        return 2

    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")

    if ok:
        print("[reliability-gate] PASS")
        return 0

    print("[reliability-gate] FAIL")
    for item in failures:
        print(f" - {item}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
