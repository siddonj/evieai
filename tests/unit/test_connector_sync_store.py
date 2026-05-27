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
