from __future__ import annotations

from pathlib import Path

from scripts.evals import reliability_gate


def test_collect_action_metrics_from_db(tmp_path: Path):
    db = tmp_path / "actions.db"

    import sqlite3

    with sqlite3.connect(str(db)) as conn:
        conn.executescript(
            """
            CREATE TABLE action_request (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL
            );
            CREATE TABLE approval_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL
            );
            INSERT INTO action_request(status) VALUES ('completed');
            INSERT INTO action_request(status) VALUES ('failed');
            INSERT INTO action_request(status) VALUES ('approved');
            INSERT INTO approval_queue(status) VALUES ('pending');
            """
        )

    metrics = reliability_gate._collect_action_metrics_from_db(db)
    assert metrics["actions_total"] == 3
    assert metrics["actions_completed"] == 1
    assert metrics["actions_failed"] == 1
    assert metrics["actions_pending_approval"] == 1
    assert metrics["action_success_rate"] == 0.5
    assert metrics["write_failures"] == 1


def test_inject_live_action_metrics_overrides_thresholds(tmp_path: Path, monkeypatch):
    db = tmp_path / "actions.db"

    import sqlite3

    with sqlite3.connect(str(db)) as conn:
        conn.executescript(
            """
            CREATE TABLE action_request (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL
            );
            CREATE TABLE approval_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                status TEXT NOT NULL
            );
            INSERT INTO action_request(status) VALUES ('completed');
            INSERT INTO action_request(status) VALUES ('completed');
            INSERT INTO approval_queue(status) VALUES ('pending');
            """
        )

    base = {
        "thresholds": {
            "max_sync_lag_seconds": 1800,
            "max_event_lag_seconds": 600,
            "min_action_success_rate": 0.95,
            "max_hallucination_rate": 0.02,
            "min_citation_accuracy": 0.95,
            "max_write_failures": 5,
        },
        "current": {
            "sync_lag_seconds": 10,
            "event_lag_seconds": 5,
            "hallucination_rate": 0.0,
            "citation_accuracy": 1.0,
        },
    }

    monkeypatch.setenv("ACTIONS_DB_PATH", str(db))
    monkeypatch.setenv("SLO_MIN_ACTION_SUCCESS_RATE", "0.97")
    monkeypatch.setenv("SLO_MAX_WRITE_FAILURES", "2")

    merged = reliability_gate._inject_live_action_metrics(base)
    assert merged["thresholds"]["min_action_success_rate"] == 0.97
    assert merged["thresholds"]["max_write_failures"] == 2
    assert merged["current"]["action_success_rate"] == 1.0
    assert merged["current"]["write_failures"] == 0
    assert merged["current"]["actions_total"] == 2
    assert merged["current"]["actions_pending_approval"] == 1

    ok, failures, _ = reliability_gate._evaluate(merged)
    assert ok is True
    assert failures == []
