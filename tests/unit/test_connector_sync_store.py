from pathlib import Path

from orchestrator.app.connector_sync_store import ConnectorSyncStore


def test_cursor_roundtrip(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    assert store.get_cursor("propexo", "resident") is None
    store.upsert_cursor("propexo", "resident", "cursor-1")
    assert store.get_cursor("propexo", "resident") == "cursor-1"


def test_dead_letter_lifecycle(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    dead_id = store.add_dead_letter(
        source_id="propexo",
        entity_type="resident",
        cursor_value="cursor-2",
        payload={"limit": 100},
        error_text="boom",
    )

    pending = store.list_dead_letters(status="pending", limit=10)
    assert len(pending) == 1
    assert pending[0]["id"] == dead_id

    store.mark_dead_letter_replayed(dead_id, success=False, error_text="still boom")
    row = store.get_dead_letter(dead_id)
    assert row is not None
    assert row["attempts"] == 2
    assert row["status"] == "pending"

    store.mark_dead_letter_replayed(dead_id, success=True)
    row2 = store.get_dead_letter(dead_id)
    assert row2 is not None
    assert row2["status"] == "replayed"


def test_run_tracking(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    run_row_id = store.start_run(run_id="run-1", source_id="propexo", entity_type="property")
    assert isinstance(run_row_id, int)

    store.finish_run(
        run_row_id,
        status="success",
        fetched_count=12,
        persisted_count=10,
        duplicate=False,
    )


def test_schedule_upsert_and_list(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    row = store.upsert_schedule(
        source_id="propexo",
        entity_type="resident",
        limit_value=150,
        interval_seconds=120,
        enabled=True,
    )
    assert row["source_id"] == "propexo"
    assert row["entity_type"] == "resident"
    assert row["enabled"] is True

    rows = store.list_schedules(enabled_only=True)
    assert len(rows) == 1
    assert rows[0]["interval_seconds"] == 120


def test_schedule_claim_and_complete(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    created = store.upsert_schedule(
        source_id="propexo",
        entity_type="lease",
        limit_value=100,
        interval_seconds=30,
        enabled=True,
    )

    claimed = store.claim_due_schedule(worker_id="worker-a", lease_seconds=60)
    assert claimed is not None
    assert claimed["id"] == created["id"]
    assert claimed["lease_owner"] == "worker-a"

    # second worker should not be able to claim same leased schedule
    claimed_again = store.claim_due_schedule(worker_id="worker-b", lease_seconds=60)
    assert claimed_again is None

    ok = store.complete_claimed_schedule(
        schedule_id=int(claimed["id"]),
        worker_id="worker-a",
        success=True,
    )
    assert ok is True

    post = store.get_schedule("propexo", "lease")
    assert post is not None
    assert post["lease_owner"] is None
    assert post["last_status"] == "success"


def test_schedule_toggle_and_delete(tmp_path: Path):
    db_path = tmp_path / "sync.db"
    store = ConnectorSyncStore(str(db_path))

    store.upsert_schedule(
        source_id="propexo",
        entity_type="property",
        limit_value=100,
        interval_seconds=45,
        enabled=True,
    )

    changed = store.set_schedule_enabled("propexo", "property", enabled=False)
    assert changed is True
    row = store.get_schedule("propexo", "property")
    assert row is not None and row["enabled"] is False

    removed = store.delete_schedule("propexo", "property")
    assert removed is True
    assert store.get_schedule("propexo", "property") is None
