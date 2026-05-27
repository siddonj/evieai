from pathlib import Path

from orchestrator.app.connector_sync_store import ConnectorSyncStore


def test_reliability_metrics_basics(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    # no data yet: default-safe metrics
    base = store.get_reliability_metrics()
    assert base["schedules_enabled"] == 0
    assert base["run_success_rate_last_200"] == 1.0

    store.upsert_schedule(
        source_id="propexo",
        entity_type="resident",
        limit_value=100,
        interval_seconds=60,
        enabled=True,
    )

    run_id = store.start_run("run-1", "propexo", "resident")
    store.finish_run(run_id, status="success", fetched_count=2, persisted_count=2, duplicate=False)

    run_id2 = store.start_run("run-2", "propexo", "resident")
    store.finish_run(run_id2, status="failed", fetched_count=0, persisted_count=0, duplicate=False, error_text="boom")

    dead_id = store.add_dead_letter(
        source_id="propexo",
        entity_type="resident",
        cursor_value="c1",
        payload={"limit": 10},
        error_text="failed",
    )
    assert isinstance(dead_id, int)

    metrics = store.get_reliability_metrics()
    assert metrics["schedules_enabled"] == 1
    assert metrics["pending_dead_letters"] == 1
    # 1 success + 1 failed => 0.5
    assert metrics["run_success_rate_last_200"] == 0.5


def test_list_recent_runs_returns_latest_first(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    r1 = store.start_run("run-1", "propexo", "resident")
    store.finish_run(r1, status="success", fetched_count=1, persisted_count=1, duplicate=False)

    r2 = store.start_run("run-2", "propexo", "resident")
    store.finish_run(r2, status="failed", fetched_count=0, persisted_count=0, duplicate=False, error_text="oops")

    rows = store.list_recent_runs(limit=10)
    assert len(rows) == 2
    assert rows[0]["run_id"] == "run-2"
    assert rows[1]["run_id"] == "run-1"
