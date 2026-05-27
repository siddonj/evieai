from pathlib import Path

from orchestrator.app.bitemporal_store import SqliteBitemporalStore


def test_bitemporal_store_persists_records(tmp_path: Path):
    db_path = tmp_path / "bitemporal.db"
    store = SqliteBitemporalStore(str(db_path))

    records = [
        {
            "source_record_id": "res-1",
            "updated_at": "2026-05-27T12:00:00Z",
            "canonical": {"resident_id": "res-1", "status": "active"},
            "payload": {"id": "res-1", "status": "active"},
        },
        {
            "source_record_id": "res-2",
            "updated_at": "2026-05-27T12:00:01Z",
            "canonical": {"resident_id": "res-2", "status": "notice"},
            "payload": {"id": "res-2", "status": "notice"},
        },
    ]

    result = store.persist_page(source_id="propexo", entity_type="resident", records=records)
    assert result["persisted"] == 2
    assert result["duplicate"] is False
    assert result["backend"] == "sqlite"


def test_bitemporal_store_supersedes_previous_snapshot(tmp_path: Path):
    db_path = tmp_path / "bitemporal.db"
    store = SqliteBitemporalStore(str(db_path))

    first = [
        {
            "source_record_id": "res-1",
            "updated_at": "2026-05-27T12:00:00Z",
            "canonical": {"resident_id": "res-1", "status": "active"},
            "payload": {"id": "res-1", "status": "active"},
        }
    ]
    second = [
        {
            "source_record_id": "res-1",
            "updated_at": "2026-05-27T13:00:00Z",
            "canonical": {"resident_id": "res-1", "status": "notice"},
            "payload": {"id": "res-1", "status": "notice"},
        }
    ]

    result1 = store.persist_page(source_id="propexo", entity_type="resident", records=first)
    result2 = store.persist_page(source_id="propexo", entity_type="resident", records=second)
    assert result1["persisted"] == 1
    assert result2["persisted"] == 1


def test_idempotency_key_dedupes_repeat_ingest(tmp_path: Path):
    db_path = tmp_path / "bitemporal.db"
    store = SqliteBitemporalStore(str(db_path))

    records = [
        {
            "source_record_id": "res-1",
            "updated_at": "2026-05-27T12:00:00Z",
            "canonical": {"resident_id": "res-1", "status": "active"},
            "payload": {"id": "res-1", "status": "active"},
        }
    ]

    key = "ingest-resident-page-001"
    first = store.persist_page(source_id="propexo", entity_type="resident", records=records, idempotency_key=key)
    second = store.persist_page(source_id="propexo", entity_type="resident", records=records, idempotency_key=key)

    assert first["persisted"] == 1
    assert first["duplicate"] is False
    assert second["persisted"] == 0
    assert second["duplicate"] is True
