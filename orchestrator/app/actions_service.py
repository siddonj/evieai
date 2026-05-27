from __future__ import annotations

import os
import uuid
from typing import Any

from fastapi import HTTPException

from app.actions_store import ActionsStore
from connectors.registry import ConnectorRegistry


HIGH_RISK_ENTITY_TYPES = {
    "lease",
    "resident",
    "payment",
    "invoice",
    "work_order",
}


class ActionsService:
    def __init__(self, *, store: ActionsStore, registry: ConnectorRegistry) -> None:
        self.store = store
        self.registry = registry
        self.policy_version = os.getenv("ACTIONS_POLICY_VERSION", "v1")

    def _resolve_risk_level(self, entity_type: str, payload: dict[str, Any]) -> str:
        explicit = payload.get("risk_level")
        if isinstance(explicit, str) and explicit.strip().lower() in {"low", "medium", "high"}:
            return explicit.strip().lower()

        if entity_type in HIGH_RISK_ENTITY_TYPES:
            return "high"

        score = payload.get("amount")
        if isinstance(score, (int, float)) and float(score) >= float(os.getenv("ACTIONS_HIGH_RISK_AMOUNT", "10000")):
            return "high"

        return "medium" if entity_type in {"property", "prospect"} else "low"

    def _requires_approval(self, risk_level: str) -> bool:
        approval_levels = {x.strip().lower() for x in os.getenv("ACTIONS_APPROVAL_LEVELS", "high").split(",") if x.strip()}
        if not approval_levels:
            approval_levels = {"high"}
        return risk_level in approval_levels

    def _policy_decision(self, *, source_id: str, entity_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not self.registry.has(source_id):
            raise HTTPException(status_code=404, detail=f"Unknown connector '{source_id}'.")

        reg = self.registry.get_registration(source_id)
        if not reg.enabled:
            raise HTTPException(status_code=409, detail=f"Connector '{source_id}' is disabled.")

        circuit = self.store.get_circuit_state(source_id)
        if circuit["state"] == "open":
            raise HTTPException(status_code=409, detail=f"Connector '{source_id}' circuit is open.")

        connector = reg.connector
        caps = {c.value for c in connector.capabilities}
        if "write" not in caps:
            raise HTTPException(status_code=400, detail=f"Connector '{source_id}' does not support write capability.")

        risk_level = self._resolve_risk_level(entity_type, payload)
        requires_approval = self._requires_approval(risk_level)

        reason = "High-risk write requires human approval" if requires_approval else "Auto-approved by policy"
        return {
            "allow": True,
            "risk_level": risk_level,
            "requires_approval": requires_approval,
            "reason": reason,
            "connector_enabled": reg.enabled,
            "connector_capabilities": sorted(caps),
            "policy_version": self.policy_version,
        }

    def request_action(
        self,
        *,
        source_id: str,
        entity_type: str,
        payload: dict[str, Any],
        idempotency_key: str,
        requested_by: str | None,
    ) -> dict[str, Any]:
        action_id = str(uuid.uuid4())
        decision = self._policy_decision(source_id=source_id, entity_type=entity_type, payload=payload)
        created = self.store.create_action_request(
            action_id=action_id,
            source_id=source_id,
            entity_type=entity_type,
            payload=payload,
            idempotency_key=idempotency_key,
            risk_level=str(decision["risk_level"]),
            policy_version=self.policy_version,
            policy_decision=decision,
            requires_approval=bool(decision["requires_approval"]),
            requested_by=requested_by,
        )

        if created["duplicate"]:
            return {
                "duplicate": True,
                "action_id": created["action_id"],
                "status": created["status"],
                "result": created.get("result"),
            }

        action = self.store.get_action_request(created["action_id"])
        return {
            "duplicate": False,
            "action_id": created["action_id"],
            "status": created["status"],
            "requires_approval": bool(created["requires_approval"]),
            "action": action,
        }

    def approve_action(self, *, action_id: str, approved_by: str) -> dict[str, Any]:
        action = self.store.get_action_request(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")

        if action["status"] not in {"pending_approval", "approved"}:
            raise HTTPException(status_code=409, detail=f"Action '{action_id}' is not pending approval")

        updated = self.store.update_action_result(
            action_id=action_id,
            status="approved",
            result={"approved": True},
            approved_by=approved_by,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")
        return updated

    def reject_action(self, *, action_id: str, rejected_by: str, reason: str | None = None) -> dict[str, Any]:
        action = self.store.get_action_request(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")

        if action["status"] not in {"pending_approval", "approved"}:
            raise HTTPException(status_code=409, detail=f"Action '{action_id}' is not pending approval")

        updated = self.store.update_action_result(
            action_id=action_id,
            status="rejected",
            result={"approved": False, "reason": reason or "Rejected by reviewer"},
            approved_by=rejected_by,
            rejection_reason=reason or "Rejected by reviewer",
        )
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")
        return updated

    def execute_action(self, *, action_id: str) -> dict[str, Any]:
        action = self.store.get_action_request(action_id)
        if action is None:
            raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")

        if action["status"] == "completed":
            return action

        if bool(action.get("requires_approval")) and action["status"] != "approved":
            raise HTTPException(status_code=409, detail=f"Action '{action_id}' requires approval before execution")

        source_id = str(action["source_id"])
        entity_type = str(action["entity_type"])
        payload = action.get("payload") or {}
        idempotency_key = str(action["idempotency_key"])

        reg = self.registry.get_registration(source_id)
        if not reg.enabled:
            raise HTTPException(status_code=409, detail=f"Connector '{source_id}' is disabled.")

        circuit = self.store.get_circuit_state(source_id)
        if circuit["state"] == "open":
            raise HTTPException(status_code=409, detail=f"Connector '{source_id}' circuit is open.")

        result_obj = reg.connector.write(entity_type=entity_type, payload=payload, idempotency_key=idempotency_key)
        result_payload = {
            "success": bool(result_obj.success),
            "source_record_id": result_obj.source_record_id,
            "status_code": result_obj.status_code,
            "message": result_obj.message,
        }

        status = "completed" if bool(result_obj.success) else "failed"
        updated = self.store.update_action_result(action_id=action_id, status=status, result=result_payload)
        if updated is None:
            raise HTTPException(status_code=404, detail=f"Action '{action_id}' not found")

        if not bool(result_obj.success):
            self.store.set_circuit_state(
                source_id=source_id,
                state="open",
                reason=f"write_failed:{result_obj.status_code or 'unknown'}",
            )

        return updated
