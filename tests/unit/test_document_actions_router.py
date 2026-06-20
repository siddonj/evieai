from __future__ import annotations

import pytest
from fastapi import HTTPException

from orchestrator.app.document_actions_router import _authorize_document_access, _resolve_effective_user


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
