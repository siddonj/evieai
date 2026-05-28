import hashlib
import hmac
import json
from datetime import datetime

from connectors.adapters.webhook_adapter import WebhookAdapter, WebhookEnvelope


def _sig(payload: dict, secret: str) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hmac.new(secret.encode("utf-8"), payload_json.encode("utf-8"), hashlib.sha256).hexdigest()


def test_verify_signature_valid():
    payload = {"id": "r-1", "balance": 123.45}
    secret = "topsecret"
    envelope = WebhookEnvelope(
        headers={"x-webhook-signature": _sig(payload, secret)},
        payload=payload,
        received_at=datetime.utcnow(),
    )
    adapter = WebhookAdapter(source_id="webhook")
    assert adapter.verify_signature(envelope, secret) is True


def test_verify_signature_invalid():
    payload = {"id": "r-1", "balance": 123.45}
    envelope = WebhookEnvelope(
        headers={"x-webhook-signature": "bad"},
        payload=payload,
        received_at=datetime.utcnow(),
    )
    adapter = WebhookAdapter(source_id="webhook")
    assert adapter.verify_signature(envelope, "topsecret") is False


def test_to_event_sets_fields():
    payload = {"id": "l-1", "days_to_expiry": 12}
    now = datetime.utcnow()
    envelope = WebhookEnvelope(headers={}, payload=payload, received_at=now)

    adapter = WebhookAdapter(source_id="webhook")
    event = adapter.to_event(
        envelope,
        event_type="updated",
        entity_type="lease",
        source_record_id="l-1",
        occurred_at=now,
    )

    assert event.source_id == "webhook"
    assert event.event_type == "updated"
    assert event.entity_type == "lease"
    assert event.source_record_id == "l-1"
    assert event.payload == payload
