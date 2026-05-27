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

    def get_registration(self, source_id: str) -> ConnectorRegistration:
        return self._items[source_id]

    def list_enabled(self) -> List[Connector]:
        return [r.connector for r in self._items.values() if r.enabled]

    def list_all(self) -> List[ConnectorRegistration]:
        return list(self._items.values())

    def is_enabled(self, source_id: str) -> bool:
        return self._items[source_id].enabled

    def set_enabled(self, source_id: str, enabled: bool) -> None:
        self._items[source_id].enabled = enabled

    def by_capability(self, capability: Capability) -> List[Connector]:
        return [
            r.connector
            for r in self._items.values()
            if r.enabled and capability in r.connector.capabilities
        ]

    def health_report(self, *, include_disabled: bool = False) -> Dict[str, HealthStatus]:
        report: Dict[str, HealthStatus] = {}
        for source_id, reg in self._items.items():
            if not reg.enabled and not include_disabled:
                continue
            report[source_id] = reg.connector.health_check()
        return report

    def bulk_register(self, connectors: Iterable[Connector]) -> None:
        for connector in connectors:
            self.register(connector)

    def has(self, source_id: str) -> bool:
        return source_id in self._items

    def total(self) -> int:
        return len(self._items)
