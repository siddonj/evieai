from __future__ import annotations

from typing import Annotated
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.actions_store import get_actions_store
from app.auth_router import require_auth_optional
from app.document_actions_service import DocumentActionsService
from app.document_actions_store import get_document_actions_store


router = APIRouter(prefix="/document-actions", tags=["document-actions"])
DOCUMENT_ACTIONS_SERVICE = DocumentActionsService(
    store=get_document_actions_store(),
    actions_store=get_actions_store(),
)


class CreateDraftRequest(BaseModel):
    user_id: str
    work_packet_id: str
    document_type: str
    title: str
    source_summary: str


class ApproveDraftRequest(BaseModel):
    destination_type: str
    destination_ref: str
    output_formats: list[str]


def _resolve_effective_user(actor: dict[str, Any] | None, requested_user_id: str | None) -> str:
    if actor:
        if actor.get("role") == "admin" and requested_user_id:
            return requested_user_id
        return str(actor.get("email") or requested_user_id or "")
    return str(requested_user_id or "")


def _authorize_document_access(actor: dict[str, Any] | None, record: dict[str, Any]) -> None:
    if not actor:
        return
    if actor.get("role") == "admin":
        return
    if str(actor.get("email") or "") != str(record.get("user_id") or ""):
        raise HTTPException(status_code=403, detail="Document workflow access denied")


def _get_document_action_or_404(document_action_id: int) -> dict[str, Any]:
    try:
        return get_document_actions_store().get(document_action_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Document workflow not found") from exc


@router.post("/draft")
def create_draft(
    payload: CreateDraftRequest,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)],
) -> dict[str, Any]:
    return DOCUMENT_ACTIONS_SERVICE.create_draft(
        user_id=_resolve_effective_user(actor, payload.user_id),
        work_packet_id=payload.work_packet_id,
        document_type=payload.document_type,
        title=payload.title,
        source_summary=payload.source_summary,
    )


@router.get("")
def list_document_actions(
    user_id: str | None = None,
    limit: int = 50,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)] = None,
) -> dict[str, Any]:
    return {
        "items": get_document_actions_store().list_actions(
            user_id=_resolve_effective_user(actor, user_id),
            limit=limit,
        ),
    }


@router.get("/{document_action_id}")
def get_document_action(
    document_action_id: int,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)] = None,
) -> dict[str, Any]:
    record = _get_document_action_or_404(document_action_id)
    _authorize_document_access(actor, record)
    return record


@router.post("/{document_action_id}/approve")
def approve_draft(
    document_action_id: int,
    payload: ApproveDraftRequest,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)] = None,
) -> dict[str, Any]:
    record = _get_document_action_or_404(document_action_id)
    _authorize_document_access(actor, record)
    return DOCUMENT_ACTIONS_SERVICE.approve(
        document_action_id=document_action_id,
        approved_by=str(actor.get("email") if actor else record.get("user_id")),
        destination_type=payload.destination_type,
        destination_ref=payload.destination_ref,
        output_formats=payload.output_formats,
    )


@router.post("/{document_action_id}/finalize")
def finalize_draft(
    document_action_id: int,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)] = None,
) -> dict[str, Any]:
    record = _get_document_action_or_404(document_action_id)
    _authorize_document_access(actor, record)
    return DOCUMENT_ACTIONS_SERVICE.finalize(document_action_id=document_action_id)


@router.post("/{document_action_id}/export-package")
def export_package(
    document_action_id: int,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)] = None,
) -> dict[str, Any]:
    record = _get_document_action_or_404(document_action_id)
    _authorize_document_access(actor, record)
    return DOCUMENT_ACTIONS_SERVICE.export_package(document_action_id=document_action_id)
