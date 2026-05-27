from __future__ import annotations

from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Set

import httpx

from ..base import Connector
from ..mappers import map_propexo_record
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
        """Fetch records from Propexo Unified API and map to canonical ingest stubs."""
        if entity_type not in self.discover_entities():
            raise ValueError(f"Unsupported entity_type for Propexo: {entity_type}")

        params: Dict[str, Any] = {"limit": max(1, min(limit, 1000))}
        if cursor is not None:
            params["cursor"] = cursor.value

        endpoint = f"{self.base_url.rstrip('/')}/{entity_type}s"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            resp = client.get(endpoint, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        records = data.get("data") if isinstance(data, dict) else data
        if not isinstance(records, list):
            records = []

        mapped = [map_propexo_record(entity_type, r) for r in records if isinstance(r, dict)]

        next_token = None
        if isinstance(data, dict):
            paging = data.get("paging") or data.get("meta") or {}
            next_token = paging.get("next_cursor") or paging.get("next") or data.get("next_cursor")

        next_cursor = SyncCursor(value=str(next_token)) if next_token else None
        return Page(records=mapped, next_cursor=next_cursor)

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
        endpoint = f"{self.base_url.rstrip('/')}/health"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = client.get(endpoint, headers=headers)
            if resp.status_code == 200:
                return HealthStatus(ok=True, detail="ok")
            return HealthStatus(ok=False, detail=f"health status={resp.status_code}")
        except Exception as exc:
            return HealthStatus(ok=False, detail=f"health check failed: {exc}")
