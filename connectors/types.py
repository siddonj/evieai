from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class Capability(str, Enum):
    READ = "read"
    WRITE = "write"
    STREAM = "stream"
    WEBHOOK = "webhook"
    SCHEMA = "schema"


class SyncMode(str, Enum):
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
    records: List[Dict[str, Any]]
    next_cursor: Optional[SyncCursor] = None
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ConnectorEvent:
    source_id: str
    event_type: str
    entity_type: str
    source_record_id: str
    payload: Dict[str, Any]
    occurred_at: datetime
    received_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WriteResult:
    success: bool
    source_record_id: Optional[str] = None
    status_code: Optional[int] = None
    message: Optional[str] = None


@dataclass
class HealthStatus:
    ok: bool
    detail: str
    checked_at: datetime = field(default_factory=datetime.utcnow)
