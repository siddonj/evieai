from __future__ import annotations

import mimetypes
import urllib.parse
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
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


def _iter_document_artifacts(record: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for key in ("artifacts", "export_package"):
        value = record.get(key)
        if key == "artifacts" and isinstance(value, list):
            artifacts.extend(item for item in value if isinstance(item, dict))
        elif key == "export_package" and isinstance(value, dict):
            nested = value.get("artifacts")
            if isinstance(nested, list):
                artifacts.extend(item for item in nested if isinstance(item, dict))
    return artifacts


def _find_document_artifact(record: dict[str, Any], file_name: str) -> dict[str, Any] | None:
    for artifact in _iter_document_artifacts(record):
        if str(artifact.get("file_name") or "") == file_name:
            return artifact
    return None


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


@router.get("/{document_action_id}/artifacts/{file_name:path}")
async def download_document_artifact(
    document_action_id: int,
    file_name: str,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)] = None,
) -> Response:
    record = _get_document_action_or_404(document_action_id)
    _authorize_document_access(actor, record)
    artifact = _find_document_artifact(record, file_name)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Document artifact not found")

    local_path = DOCUMENT_ACTIONS_SERVICE.artifact_root / str(document_action_id) / file_name
    if local_path.is_file():
        media_type = mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return FileResponse(path=local_path, filename=file_name, media_type=media_type)

    blob_url = artifact.get("blob_url")
    if isinstance(blob_url, str) and blob_url:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(blob_url)
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text[:500])

        headers: dict[str, str] = {}
        disposition = resp.headers.get("content-disposition")
        if disposition:
            headers["Content-Disposition"] = disposition
        else:
            safe_name = file_name.replace('"', '\\"')
            headers["Content-Disposition"] = f'attachment; filename="{safe_name}"'

        return Response(
            content=resp.content,
            media_type=resp.headers.get("content-type", "application/octet-stream"),
            headers=headers,
        )

    raise HTTPException(status_code=404, detail="Document artifact unavailable")
