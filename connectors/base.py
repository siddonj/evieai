from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Protocol, Set

from .types import Capability, ConnectorEvent, HealthStatus, Page, RateLimit, SyncCursor, WriteResult


class Connector(Protocol):
    """Canonical interface for all EvieAI source connectors."""

    source_id: str
    display_name: str
    capabilities: Set[Capability]
    rate_limit: RateLimit

    def discover_entities(self) -> List[str]:
        """Return canonical entity types this connector can provide."""
        ...

    def schema(self, entity_type: str) -> Dict[str, Any]:
        """Return JSON-schema-like object for entity payloads."""
        ...

    def fetch(self, entity_type: str, cursor: SyncCursor | None = None, limit: int = 500) -> Page:
        """Fetch a page of records for batch/incremental sync."""
        ...

    async def stream(self) -> AsyncIterator[ConnectorEvent]:
        """Yield events for streaming/webhook connectors."""
        ...

    def write(self, entity_type: str, payload: Dict[str, Any], *, idempotency_key: str) -> WriteResult:
        """Write-back operation to upstream system with idempotency guard."""
        ...

    def health_check(self) -> HealthStatus:
        """Fast liveness/auth check used by registry scheduler."""
        ...
