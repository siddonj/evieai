from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

from .base import Connector
from .types import Capability, HealthStatus


@dataclass
class ConnectorRegistration:
    connector: Connector
    enabled: bool = True
    tenant_id: Optional[str] = None


class ConnectorRegistry:
    """In-memory registry; replace with DB-backed registry for production."""

    def __init__(self) -> None:
        self._items: Dict[str, ConnectorRegistration] = {}

    def register(self, connector: Connector, *, enabled: bool = True, tenant_id: str | None = None) -> None:
        self._items[connector.source_id] = ConnectorRegistration(
            connector=connector,
            enabled=enabled,
            tenant_id=tenant_id,
        )

    def get(self, source_id: str) -> Connector:
        reg = self._items[source_id]
        return reg.connector

    def list_enabled(self) -> List[Connector]:
        return [r.connector for r in self._items.values() if r.enabled]

    def by_capability(self, capability: Capability) -> List[Connector]:
        return [
            r.connector
            for r in self._items.values()
            if r.enabled and capability in r.connector.capabilities
        ]

    def health_report(self) -> Dict[str, HealthStatus]:
        report: Dict[str, HealthStatus] = {}
        for source_id, reg in self._items.items():
            if not reg.enabled:
                continue
            report[source_id] = reg.connector.health_check()
        return report

    def bulk_register(self, connectors: Iterable[Connector]) -> None:
        for connector in connectors:
            self.register(connector)
