from __future__ import annotations

from datetime import datetime

from connectors.adapters.propexo_adapter import PropexoAdapter
from connectors.types import Capability, HealthStatus, Page, RateLimit, SyncCursor, WriteResult


def test_propexo_adapter_contract_surface():
    adapter = PropexoAdapter(api_key="test-key", base_url="https://api.example.test/v1")

    # identity + capability contract
    assert adapter.source_id == "propexo"
    assert adapter.display_name
    assert Capability.READ in adapter.capabilities
    assert Capability.SCHEMA in adapter.capabilities
    assert isinstance(adapter.rate_limit, RateLimit)

    # discover entities contract
    entities = adapter.discover_entities()
    assert isinstance(entities, list)
    assert "resident" in entities

    # schema contract
    resident_schema = adapter.schema("resident")
    assert resident_schema["type"] == "object"
    assert "properties" in resident_schema


def test_propexo_fetch_contract(monkeypatch):
    adapter = PropexoAdapter(api_key="test-key", base_url="https://api.example.test/v1")

    def fake_request_json(endpoint: str, params: dict | None = None):
        assert endpoint.endswith("/residents")
        assert params is not None
        assert "limit" in params
        return {
            "data": [
                {
                    "id": "r-1",
                    "firstName": "Jane",
                    "lastName": "Doe",
                    "email": "jane@example.com",
                    "updatedAt": "2026-01-01T00:00:00Z",
                }
            ],
            "paging": {"next_cursor": "cursor-2"},
        }

    monkeypatch.setattr(adapter, "_request_json", fake_request_json)

    page = adapter.fetch(entity_type="resident", cursor=SyncCursor(value="cursor-1"), limit=50)

    assert isinstance(page, Page)
    assert len(page.records) == 1
    assert page.next_cursor is not None
    assert page.next_cursor.value == "cursor-2"
    assert page.records[0]["entity_type"] == "resident"
    assert page.records[0]["source_record_id"] == "r-1"


def test_propexo_health_and_write_contract(monkeypatch):
    adapter = PropexoAdapter(api_key="test-key", base_url="https://api.example.test/v1")

    monkeypatch.setattr(adapter, "_request_json", lambda endpoint, params=None: {"status": "ok"})
    status = adapter.health_check()
    assert isinstance(status, HealthStatus)
    assert status.ok is True
    assert isinstance(status.checked_at, datetime)

    write_result = adapter.write("resident", {"id": "r-1"}, idempotency_key="idem-1")
    assert isinstance(write_result, WriteResult)
    assert write_result.success is False
    assert write_result.status_code == 501
