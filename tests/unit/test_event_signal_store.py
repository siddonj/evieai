from pathlib import Path

from orchestrator.app.event_signal_store import EventSignalStore


def test_ingest_event_generates_signal(tmp_path: Path):
    db_path = tmp_path / "event_signal.db"
    store = EventSignalStore(str(db_path))

    out = store.ingest_event(
        source_id="webhook",
        event_type="updated",
        entity_type="lease",
        source_record_id="lease-1",
        payload={"days_to_expiry": 10},
        occurred_at="2026-01-01T00:00:00Z",
        signature_valid=True,
    )

    assert out["event_id"] > 0
    assert out["signal_count"] == 1

    events = store.list_events(limit=10)
    assert len(events) == 1
    assert events[0]["entity_type"] == "lease"

    signals = store.list_signals(limit=10)
    assert len(signals) == 1
    assert signals[0]["signal_type"] == "lease_expiring_soon"
    assert signals[0]["severity"] in {"high", "medium"}


def test_metrics_counts(tmp_path: Path):
    db_path = tmp_path / "event_signal.db"
    store = EventSignalStore(str(db_path))

    m0 = store.metrics()
    assert m0["events_total"] == 0
    assert m0["signals_total"] == 0

    store.ingest_event(
        source_id="webhook",
        event_type="updated",
        entity_type="resident",
        source_record_id="resident-1",
        payload={"balance": 250.0},
        occurred_at="2026-01-01T00:00:00Z",
        signature_valid=True,
    )

    m1 = store.metrics()
    assert m1["events_total"] == 1
    assert m1["signals_total"] == 1
