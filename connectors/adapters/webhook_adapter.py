from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import hmac
import json
from typing import Any, Dict

from ..types import ConnectorEvent


@dataclass
class WebhookEnvelope:
    headers: Dict[str, str]
    payload: Dict[str, Any]
    received_at: datetime


class WebhookAdapter:
    """Generic webhook parser/validator skeleton for event-driven integrations."""

    def __init__(self, source_id: str) -> None:
        self.source_id = source_id

    def verify_signature(self, envelope: WebhookEnvelope, secret: str) -> bool:
        provided = envelope.headers.get("x-webhook-signature", "")
        if not secret:
            return True
        if not provided:
            return False

        payload_json = json.dumps(envelope.payload, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided, expected)

    def to_event(
        self,
        envelope: WebhookEnvelope,
        *,
        event_type: str,
        entity_type: str,
        source_record_id: str,
        occurred_at: datetime | None = None,
    ) -> ConnectorEvent:
        return ConnectorEvent(
            source_id=self.source_id,
            event_type=event_type,
            entity_type=entity_type,
            source_record_id=source_record_id,
            payload=envelope.payload,
            occurred_at=occurred_at or envelope.received_at,
            received_at=envelope.received_at,
        )
