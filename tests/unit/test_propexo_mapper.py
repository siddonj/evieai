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


def test_map_property_canonical_fields():
    raw = {
        "id": "prop-1",
        "property_name": "Main Street Apartments",
        "address": "100 Main St",
        "city": "Memphis",
        "state": "TN",
        "zip": "38103",
        "total_units": "210",
        "occupancy_rate": "95.5",
        "average_rent": "1450.75",
    }

    mapped = map_propexo_record("property", raw)
    canonical = mapped["canonical"]

    assert canonical["property_id"] == "prop-1"
    assert canonical["name"] == "Main Street Apartments"
    assert canonical["unit_count"] == 210
    assert canonical["occupancy_rate"] == 95.5
    assert canonical["average_rent"] == 1450.75


def test_map_lease_canonical_fields():
    raw = {
        "id": "lease-9",
        "resident_id": "res-4",
        "property_id": "prop-1",
        "unit_number": "1203",
        "lease_start": "2026-01-01",
        "lease_end": "2026-12-31",
        "base_rent": "1800",
        "security_deposit": "500",
        "status": "active",
    }

    mapped = map_propexo_record("lease", raw)
    canonical = mapped["canonical"]

    assert canonical["lease_id"] == "lease-9"
    assert canonical["resident_id"] == "res-4"
    assert canonical["unit_id"] == "1203"
    assert canonical["rent"] == 1800.0
    assert canonical["deposit"] == 500.0
    assert canonical["status"] == "active"
