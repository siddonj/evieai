from __future__ import annotations

from pathlib import Path

from app.actions_store import ActionsStore


def test_action_store_create_and_queue(tmp_path: Path):
    store = ActionsStore(str(tmp_path / "actions.db"))

    created = store.create_action_request(
        action_id="a1",
        source_id="propexo",
        entity_type="lease",
        payload={"id": "l1", "amount": 25000},
        idempotency_key="idem-1",
        risk_level="high",
        policy_version="v1",
        policy_decision={"requires_approval": True, "reason": "risk"},
        requires_approval=True,
        requested_by="josh",
    )

    assert created["duplicate"] is False
    assert created["status"] == "pending_approval"

    approvals = store.list_approval_queue(status="pending", limit=20)
    assert len(approvals) == 1
    assert approvals[0]["action_id"] == "a1"


def test_action_store_idempotency(tmp_path: Path):
    store = ActionsStore(str(tmp_path / "actions.db"))

    one = store.create_action_request(
        action_id="a1",
        source_id="propexo",
        entity_type="property",
        payload={"id": "p1"},
        idempotency_key="idem-k",
        risk_level="low",
        policy_version="v1",
        policy_decision={"requires_approval": False},
        requires_approval=False,
        requested_by="josh",
    )
    two = store.create_action_request(
        action_id="a2",
        source_id="propexo",
        entity_type="property",
        payload={"id": "p1"},
        idempotency_key="idem-k",
        risk_level="low",
        policy_version="v1",
        policy_decision={"requires_approval": False},
        requires_approval=False,
        requested_by="josh",
    )

    assert one["duplicate"] is False
    assert two["duplicate"] is True
    assert two["action_id"] == "a1"


def test_action_store_audit_hash_chain(tmp_path: Path):
    store = ActionsStore(str(tmp_path / "actions.db"))

    store.append_audit_event(
        event_type="action.write.intent",
        action_id="a1",
        source_id="propexo",
        entity_type="property",
        payload={"x": 1},
    )
    store.append_audit_event(
        event_type="action.write.result",
        action_id="a1",
        source_id="propexo",
        entity_type="property",
        payload={"ok": True},
    )

    events = store.list_audit_events(limit=10)
    assert len(events) == 2
    latest = events[0]
    previous = events[1]
    assert latest["prev_hash"] == previous["row_hash"]
