from __future__ import annotations

from datetime import datetime, timedelta
from time import sleep
from typing import Any, AsyncIterator, Dict, List, Set

import httpx

from ..base import Connector
from ..mappers import map_propexo_record
from ..types import Capability, ConnectorEvent, HealthStatus, Page, RateLimit, SyncCursor, WriteResult


class PropexoAdapter(Connector):
    """Propexo Unified API connector with retry/backoff and simple circuit breaker."""

    source_id = "propexo"
    display_name = "Propexo Unified API"
    capabilities: Set[Capability] = {Capability.READ, Capability.WRITE, Capability.SCHEMA}
    rate_limit = RateLimit(requests_per_minute=150, burst=300)

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.propexo.com/v1",
        max_retries: int = 3,
        backoff_seconds: float = 0.5,
        failure_threshold: int = 4,
        circuit_cooldown_seconds: int = 30,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.failure_threshold = failure_threshold
        self.circuit_cooldown_seconds = circuit_cooldown_seconds

        self._consecutive_failures = 0
        self._circuit_open_until: datetime | None = None

    def _circuit_open(self) -> bool:
        if self._circuit_open_until is None:
            return False
        if datetime.utcnow() >= self._circuit_open_until:
            self._circuit_open_until = None
            self._consecutive_failures = 0
            return False
        return True

    def _record_success(self) -> None:
        self._consecutive_failures = 0
        self._circuit_open_until = None

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self._circuit_open_until = datetime.utcnow() + timedelta(seconds=self.circuit_cooldown_seconds)

    def _request_json(self, endpoint: str, params: Dict[str, Any] | None = None) -> Any:
        if self._circuit_open():
            raise RuntimeError("Propexo circuit is open; retry later")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                    resp = client.get(endpoint, params=params, headers=headers)

                if resp.status_code >= 500:
                    raise httpx.HTTPStatusError(
                        f"server error {resp.status_code}", request=resp.request, response=resp
                    )
                resp.raise_for_status()

                self._record_success()
                return resp.json()
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                self._record_failure()
                if attempt < self.max_retries and not self._circuit_open():
                    sleep(self.backoff_seconds * attempt)

        assert last_exc is not None
        raise last_exc

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
        data = self._request_json(endpoint, params=params)

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

        try:
            data = self._request_json(endpoint)
            detail = "ok" if not isinstance(data, dict) else str(data.get("status") or "ok")
            return HealthStatus(ok=True, detail=detail)
        except Exception as exc:
            return HealthStatus(ok=False, detail=f"health check failed: {exc}")
