from __future__ import annotations

from pathlib import Path

import pytest

from app.actions_service import ActionsService
from app.actions_store import ActionsStore
from connectors.adapters.propexo_adapter import PropexoAdapter
from connectors.registry import ConnectorRegistry
from connectors.types import Capability, WriteResult


class WriteStubConnector(PropexoAdapter):
    def __init__(self) -> None:
        super().__init__(api_key="test", base_url="https://example.invalid")
        self.capabilities = {Capability.READ, Capability.WRITE}

    def write(self, entity_type: str, payload: dict, *, idempotency_key: str) -> WriteResult:  # type: ignore[override]
        if payload.get("force_fail"):
            return WriteResult(success=False, status_code=500, message="forced failure")
        return WriteResult(success=True, source_record_id=payload.get("id", "new-id"), status_code=200, message="ok")


@pytest.fixture
def service(tmp_path: Path) -> ActionsService:
    store = ActionsStore(str(tmp_path / "actions.db"))
    registry = ConnectorRegistry()
    connector = WriteStubConnector()
    registry.register(connector)
    return ActionsService(store=store, registry=registry)


def test_request_action_idempotency(service: ActionsService):
    one = service.request_action(
        source_id="propexo",
        entity_type="property",
        payload={"id": "p1", "name": "A"},
        idempotency_key="idem-1",
        requested_by="josh",
    )
    two = service.request_action(
        source_id="propexo",
        entity_type="property",
        payload={"id": "p1", "name": "A"},
        idempotency_key="idem-1",
        requested_by="josh",
    )

    assert one["duplicate"] is False
    assert two["duplicate"] is True
    assert two["action_id"] == one["action_id"]


def test_high_risk_requires_approval(service: ActionsService):
    res = service.request_action(
        source_id="propexo",
        entity_type="lease",
        payload={"id": "l1", "amount": 15000},
        idempotency_key="idem-lease",
        requested_by="josh",
    )

    assert res["duplicate"] is False
    assert res["requires_approval"] is True
    assert res["status"] == "pending_approval"


def test_approve_then_execute(service: ActionsService):
    req = service.request_action(
        source_id="propexo",
        entity_type="lease",
        payload={"id": "l2"},
        idempotency_key="idem-l2",
        requested_by="josh",
    )
    action_id = req["action_id"]

    approved = service.approve_action(action_id=action_id, approved_by="approver")
    assert approved["status"] == "approved"

    done = service.execute_action(action_id=action_id)
    assert done["status"] == "completed"
    assert done["result"]["success"] is True


def test_failed_execution_opens_circuit(service: ActionsService):
    req = service.request_action(
        source_id="propexo",
        entity_type="property",
        payload={"id": "p9", "force_fail": True},
        idempotency_key="idem-fail",
        requested_by="josh",
    )
    action_id = req["action_id"]

    # medium/low should be auto-approved by default policy
    done = service.execute_action(action_id=action_id)
    assert done["status"] == "failed"

    circuit = service.store.get_circuit_state("propexo")
    assert circuit["state"] == "open"
