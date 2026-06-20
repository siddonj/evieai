from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.document_actions_service import DocumentActionsService
from app.document_actions_store import get_document_actions_store


router = APIRouter(prefix="/document-actions", tags=["document-actions"])
DOCUMENT_ACTIONS_SERVICE = DocumentActionsService(store=get_document_actions_store())


class CreateDraftRequest(BaseModel):
    user_id: str
    work_packet_id: str
    document_type: str
    title: str
    source_summary: str


class ApproveDraftRequest(BaseModel):
    approved_by: str
    destination_type: str
    destination_ref: str
    output_formats: list[str]


@router.post("/draft")
def create_draft(payload: CreateDraftRequest) -> dict[str, Any]:
    return DOCUMENT_ACTIONS_SERVICE.create_draft(
        user_id=payload.user_id,
        work_packet_id=payload.work_packet_id,
        document_type=payload.document_type,
        title=payload.title,
        source_summary=payload.source_summary,
    )


@router.post("/{document_action_id}/approve")
def approve_draft(document_action_id: int, payload: ApproveDraftRequest) -> dict[str, Any]:
    return DOCUMENT_ACTIONS_SERVICE.approve(
        document_action_id=document_action_id,
        approved_by=payload.approved_by,
        destination_type=payload.destination_type,
        destination_ref=payload.destination_ref,
        output_formats=payload.output_formats,
    )


@router.post("/{document_action_id}/finalize")
def finalize_draft(document_action_id: int) -> dict[str, Any]:
    return DOCUMENT_ACTIONS_SERVICE.finalize(document_action_id=document_action_id)
