"""Authentication router for EvieAI web UI.

Provides email/password registration and login with JWT tokens,
and a dependency to protect orchestrator routes.
Uses SQLite for local-dev consistency with the rest of the orchestrator stores.
"""

from __future__ import annotations

import os
import secrets
import sqlite3
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Annotated

import bcrypt
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

router = APIRouter(prefix="/auth", tags=["auth"])

# Config from environment
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

# Seed credentials (only used when DB is empty)
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@evieai.local")
DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin")
AUTH_DB_PATH = os.getenv("AUTH_DB_PATH", "./data/evieai_auth.db")
JWT_SECRET_FILE = Path(os.getenv("JWT_SECRET_FILE", "./data/evieai_jwt_secret"))
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev").strip().lower()

security = HTTPBearer(auto_error=False)


class UserCreate(BaseModel):
    email: str
    password: str = Field(..., min_length=4)
    role: str = Field(default="user", pattern="^(admin|user)$")


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: str
    email: str
    role: str


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _is_local_environment() -> bool:
    return ENVIRONMENT in {"", "dev", "development", "local", "test"}


def _load_or_create_jwt_secret() -> str:
    configured = os.getenv("JWT_SECRET", os.getenv("AUTH_SECRET", "")).strip()
    if configured:
        return configured

    if not _is_local_environment():
        raise RuntimeError("JWT_SECRET environment variable is not set")

    JWT_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if JWT_SECRET_FILE.exists():
        secret = JWT_SECRET_FILE.read_text(encoding="utf-8").strip()
        if secret:
            return secret

    secret = secrets.token_urlsafe(48)
    JWT_SECRET_FILE.write_text(secret, encoding="utf-8")
    try:
        JWT_SECRET_FILE.chmod(0o600)
    except OSError:
        pass
    return secret


def _normalize_email(email: str) -> str:
    normalized = (email or "").strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email format")
    return normalized


def _create_access_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.now(UTC) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, _load_or_create_jwt_secret(), algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, _load_or_create_jwt_secret(), algorithms=[JWT_ALGORITHM])


def _connect() -> sqlite3.Connection:
    Path(AUTH_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(AUTH_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_schema() -> None:
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user' CHECK(role IN ('admin', 'user')),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        conn.commit()


def _seed_default_admin() -> None:
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM users").fetchone()
        if row and row[0] == 0:
            conn.execute(
                "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), DEFAULT_ADMIN_EMAIL, _hash_password(DEFAULT_ADMIN_PASSWORD), "admin"),
            )
            conn.commit()


@router.post("/register", response_model=TokenResponse)
async def register(body: UserCreate) -> TokenResponse:
    _ensure_schema()
    _seed_default_admin()
    email = _normalize_email(body.email)
    with _connect() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO users (id, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (user_id, email, _hash_password(body.password), body.role),
        )
        conn.commit()
    token = _create_access_token(user_id, email, body.role)
    return TokenResponse(
        access_token=token,
        user={"id": user_id, "email": email, "role": body.role},
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: UserLogin) -> TokenResponse:
    _ensure_schema()
    _seed_default_admin()
    email = _normalize_email(body.email)
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, role FROM users WHERE email = ?", (email,)
        ).fetchone()
    if not row or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = _create_access_token(row["id"], row["email"], row["role"])
    return TokenResponse(
        access_token=token,
        user={"id": row["id"], "email": row["email"], "role": row["role"]},
    )


@router.get("/me", response_model=UserOut)
async def me(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]) -> UserOut:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = _decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None

    with _connect() as conn:
        row = conn.execute("SELECT id, email, role FROM users WHERE id = ?", (payload["sub"],)).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return UserOut(id=row["id"], email=row["email"], role=row["role"])


# Dependency for protecting other routes
async def require_auth(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]) -> dict:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    try:
        payload = _decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from None
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from None
    return payload


async def require_auth_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> dict | None:
    if not credentials:
        return None
    return await require_auth(credentials)


async def require_admin(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)]) -> dict:
    payload = await require_auth(credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return payload
