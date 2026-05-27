from connectors.mappers import map_propexo_record


def test_map_propexo_record_preserves_payload_and_metadata():
    raw = {
        "id": 123,
        "updated_at": "2026-05-27T12:00:00Z",
        "name": "Resident A",
    }

    mapped = map_propexo_record("resident", raw)

    assert mapped["entity_type"] == "resident"
    assert mapped["source_id"] == "propexo"
    assert mapped["source_record_id"] == "123"
    assert mapped["updated_at"] == "2026-05-27T12:00:00Z"
    assert mapped["payload"] == raw
