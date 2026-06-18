"""Unit tests for the orchestrator auth router."""

from __future__ import annotations

import asyncio
import importlib
import sys
from pathlib import Path

import pytest


def _load_auth_router(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    monkeypatch.setenv("AUTH_DB_PATH", str(tmp_path / "auth.db"))
    monkeypatch.setenv("JWT_SECRET_FILE", str(tmp_path / "jwt.secret"))
    monkeypatch.setenv("DEFAULT_ADMIN_EMAIL", "admin@evie.ai.local")
    monkeypatch.setenv("DEFAULT_ADMIN_PASSWORD", "admin")

    sys.modules.pop("app.auth_router", None)
    module = importlib.import_module("app.auth_router")
    return importlib.reload(module)


def test_dev_login_seeds_secret_and_returns_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    auth_router = _load_auth_router(monkeypatch, tmp_path)

    async def run_login():
        return await auth_router.login(auth_router.UserLogin(email="admin@evie.ai.local", password="admin"))

    result = asyncio.run(run_login())

    assert result.access_token
    assert result.user["email"] == "admin@evie.ai.local"
    assert result.user["role"] == "admin"
    assert (tmp_path / "jwt.secret").exists()
