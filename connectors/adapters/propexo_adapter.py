from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Set

from ..base import Connector
from ..types import Capability, ConnectorEvent, HealthStatus, Page, RateLimit, SyncCursor, WriteResult


class PropexoAdapter(Connector):
    """Draft adapter skeleton for Propexo Unified API."""

    source_id = "propexo"
    display_name = "Propexo Unified API"
    capabilities: Set[Capability] = {Capability.READ, Capability.WRITE, Capability.SCHEMA}
    rate_limit = RateLimit(requests_per_minute=150, burst=300)

    def __init__(self, *, api_key: str, base_url: str = "https://api.propexo.com/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url

    def discover_entities(self) -> List[str]:
        return [
            "property",
            "unit",
            "resident",
            "lease",
            "application",
            "work_order",
            "prospect",
        ]

    def schema(self, entity_type: str) -> Dict[str, Any]:
        # TODO: load from live OpenAPI / schema endpoint when available.
        return {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "source_system": {"type": "string"},
                "updated_at": {"type": "string", "format": "date-time"},
            },
            "required": ["id"],
            "x-entity-type": entity_type,
        }

    def fetch(self, entity_type: str, cursor: SyncCursor | None = None, limit: int = 500) -> Page:
        # TODO: replace with actual HTTP calls.
        # Expected shape: GET /{entity_type}?cursor=...&limit=...
        _ = (entity_type, cursor, limit)
        return Page(records=[], next_cursor=None)

    async def stream(self) -> AsyncIterator[ConnectorEvent]:
        # Propexo is primarily pull-based in this draft.
        if False:
            yield ConnectorEvent(
                source_id=self.source_id,
                event_type="noop",
                entity_type="resident",
                source_record_id="",
                payload={},
                occurred_at=datetime.utcnow(),
            )

    def write(self, entity_type: str, payload: Dict[str, Any], *, idempotency_key: str) -> WriteResult:
        # TODO: implement with headers: Idempotency-Key, Authorization
        _ = (entity_type, payload, idempotency_key)
        return WriteResult(success=False, status_code=501, message="Not implemented")

    def health_check(self) -> HealthStatus:
        # TODO: perform token validation / ping endpoint.
        return HealthStatus(ok=True, detail="Draft adapter health check placeholder")
