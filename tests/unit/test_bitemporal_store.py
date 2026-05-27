from pathlib import Path

from orchestrator.app.bitemporal_store import BitemporalStore


def test_bitemporal_store_persists_records(tmp_path: Path):
    db_path = tmp_path / "bitemporal.db"
    store = BitemporalStore(str(db_path))

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

    inserted = store.persist_page(source_id="propexo", entity_type="resident", records=records)
    assert inserted == 2


def test_bitemporal_store_supersedes_previous_snapshot(tmp_path: Path):
    db_path = tmp_path / "bitemporal.db"
    store = BitemporalStore(str(db_path))

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

    assert store.persist_page(source_id="propexo", entity_type="resident", records=first) == 1
    assert store.persist_page(source_id="propexo", entity_type="resident", records=second) == 1
