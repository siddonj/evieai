from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class Capability(StrEnum):
    READ = "read"
    WRITE = "write"
    STREAM = "stream"
    WEBHOOK = "webhook"
    SCHEMA = "schema"


class SyncMode(StrEnum):
    FULL = "full"
    INCREMENTAL = "incremental"
    WEBHOOK = "webhook"


@dataclass
class RateLimit:
    requests_per_minute: int
    burst: int = 0


@dataclass
class SyncCursor:
    value: str
    mode: SyncMode = SyncMode.INCREMENTAL


@dataclass
class Page:
    records: list[dict[str, Any]]
    next_cursor: SyncCursor | None = None
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConnectorEvent:
    source_id: str
    event_type: str
    entity_type: str
    source_record_id: str
    payload: dict[str, Any]
    occurred_at: datetime
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WriteResult:
    success: bool
    source_record_id: str | None = None
    status_code: int | None = None
    message: str | None = None


@dataclass
class HealthStatus:
    ok: bool
    detail: str
    checked_at: datetime = field(default_factory=datetime.utcnow)
