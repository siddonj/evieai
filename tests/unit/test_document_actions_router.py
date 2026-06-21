from __future__ import annotations

import pytest
from fastapi import HTTPException

from orchestrator.app.document_actions_router import (
    _authorize_document_access,
    _resolve_effective_user,
    download_document_artifact,
)
from orchestrator.app.document_actions_service import DocumentActionsService
from orchestrator.app.document_actions_store import DocumentActionsStore


def test_resolve_effective_user_uses_actor_email_for_non_admin():
    actor = {"email": "alice@example.com", "role": "user"}

    assert _resolve_effective_user(actor, "bob@example.com") == "alice@example.com"


def test_resolve_effective_user_allows_admin_override():
    actor = {"email": "admin@example.com", "role": "admin"}

    assert _resolve_effective_user(actor, "bob@example.com") == "bob@example.com"


def test_authorize_document_access_blocks_non_owner():
    actor = {"email": "alice@example.com", "role": "user"}
    record = {"user_id": "bob@example.com"}

    with pytest.raises(HTTPException) as exc_info:
        _authorize_document_access(actor, record)

    assert exc_info.value.status_code == 403


def test_authorize_document_access_allows_admin():
    actor = {"email": "admin@example.com", "role": "admin"}
    record = {"user_id": "bob@example.com"}

    _authorize_document_access(actor, record)


@pytest.mark.asyncio
async def test_download_document_artifact_serves_local_file(tmp_path, monkeypatch):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    artifact_root = tmp_path / "document_artifacts"
    service = DocumentActionsService(store=store, artifact_root=artifact_root)

    draft = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="board_report",
        title="Board Report",
        source_summary="Board summary",
    )
    store.mark_approved(
        document_action_id=draft["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Board",
        output_formats=["pdf"],
    )
    finalized = service.finalize(document_action_id=draft["id"])
    artifact_name = finalized["artifacts"][0]["file_name"]

    monkeypatch.setattr("orchestrator.app.document_actions_router.get_document_actions_store", lambda: store)
    monkeypatch.setattr(
        "orchestrator.app.document_actions_router.DOCUMENT_ACTIONS_SERVICE",
        service,
    )

    response = await download_document_artifact(
        document_action_id=draft["id"],
        file_name=artifact_name,
        actor=None,
    )

    assert response.status_code == 200
    assert response.headers["content-disposition"].startswith("attachment;")
    assert artifact_name in response.headers["content-disposition"]
