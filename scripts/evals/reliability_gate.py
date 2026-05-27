#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
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
        },
        "failures": failures,
    }
    return len(failures) == 0, failures, summary


def main() -> int:
    metrics_file = Path(os.getenv("EVIEAI_RELIABILITY_METRICS_FILE", "scripts/evals/sample_metrics.json"))
    summary_out = Path(os.getenv("EVIEAI_RELIABILITY_SUMMARY_FILE", "scripts/evals/reliability_summary.json"))

    try:
        metrics = _load_json(metrics_file)
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
