from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from typing import Any, Callable

from fastapi import HTTPException, Request


logger = logging.getLogger("orchestrator.security")

# ─── Rate Limiter ────────────────────────────────────────────────────


class RateLimiter:
    """In-memory sliding-window rate limiter keyed by user_id or IP."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)

    def _prune(self, key: str, now: float) -> list[float]:
        cutoff = now - self._window
        bucket = self._buckets[key]
        while bucket and bucket[0] <= cutoff:
            bucket.pop(0)
        return bucket

    def is_allowed(self, key: str) -> bool:
        now = time.monotonic()
        bucket = self._prune(key, now)
        if len(bucket) >= self._max:
            return False
        bucket.append(now)
        return True

    def remaining(self, key: str) -> int:
        now = time.monotonic()
        bucket = self._prune(key, now)
        return max(0, self._max - len(bucket))


_limiter = RateLimiter(max_requests=20, window_seconds=60)


def get_rate_limit_key(request: Request) -> str:
    """Derive a rate-limit key from user_id (query/body) or client IP."""
    user_id = request.query_params.get("user_id") or ""
    if not user_id:
        body = getattr(request.state, "_body", None)
        if isinstance(body, dict):
            user_id = body.get("user_id", "")
    return user_id or request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request) -> None:
    key = get_rate_limit_key(request)
    if not _limiter.is_allowed(key):
        remaining = _limiter.remaining(key)
        logger.warning("Rate limit hit for key=%s", key[:20])
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Limit: {_limiter._max}/min. Remaining: {remaining}.",
        )


# ─── Circuit Breaker ─────────────────────────────────────────────────

_CIRCUIT_OPEN_ERROR = "Service temporarily unavailable — please try again shortly."


class CircuitBreaker:
    """Simple circuit breaker – opens after consecutive failures, auto-resets."""

    def __init__(self, failure_threshold: int = 3, recovery_seconds: float = 30) -> None:
        self._threshold = failure_threshold
        self._recovery = recovery_seconds
        self._failures: dict[str, int] = defaultdict(int)
        self._open_until: dict[str, float] = {}

    @property
    def _now(self) -> float:
        return time.monotonic()

    def call(self, name: str, fn: Callable[[], Any]) -> Any:
        """Execute fn(name) with circuit protection.  Returns result or raises."""
        if self._is_open(name):
            raise CircuitOpenError(_CIRCUIT_OPEN_ERROR)

        try:
            result = fn()
            self._reset(name)
            return result
        except Exception:
            self._record_failure(name)
            raise

    async def acall(self, name: str, fn: Callable[[], Any]) -> Any:
        """Async version of call."""
        if self._is_open(name):
            raise CircuitOpenError(_CIRCUIT_OPEN_ERROR)

        try:
            result = await fn()
            self._reset(name)
            return result
        except Exception:
            self._record_failure(name)
            raise

    def _is_open(self, name: str) -> bool:
        deadline = self._open_until.get(name, 0)
        if deadline and deadline > self._now:
            return True
        if deadline and deadline <= self._now:
            self._open_until.pop(name, None)
            self._failures[name] = 0
        return False

    def _record_failure(self, name: str) -> None:
        self._failures[name] += 1
        if self._failures[name] >= self._threshold:
            self._open_until[name] = self._now + self._recovery
            logger.warning("Circuit OPEN for %s (%d consecutive failures)", name, self._failures[name])

    def _reset(self, name: str) -> None:
        self._failures[name] = 0
        self._open_until.pop(name, None)


class CircuitOpenError(Exception):
    """Raised when circuit is open — caller should return a graceful message."""


_circuit = CircuitBreaker(failure_threshold=3, recovery_seconds=30)


def circuit_protected(name: str) -> CircuitBreaker:
    return _circuit


# ─── Input Validation / Prompt Injection Detection ───────────────────

_MESSAGE_MAX_LENGTH = 4000

_INJECTION_PATTERNS: list[tuple[str, str]] = [
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?", "instruction override"),
    (r"(you\s+are\s+now|you\s+shall\s+be|pretend\s+you\s+are)", "role reassignment"),
    (r"^\s*system\s*:", "system message injection"),
    (r"^\s*assistant\s*:", "assistant message injection"),
    (r"\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>", "token injection"),
    (r"DAN\s|jailbreak|developer\s*mode", "jailbreak attempt"),
    (r"<script|javascript\s*:|onerror\s*=|onload\s*=", "XSS attempt"),
]


def validate_and_sanitize(message: str, user_id: str | None = None) -> str:
    """Validate message length and check for prompt injection patterns."""
    sanitized = message.strip()

    if len(sanitized) > _MESSAGE_MAX_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Message too long. Maximum {_MESSAGE_MAX_LENGTH} characters.",
        )

    if not sanitized:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    for pattern, category in _INJECTION_PATTERNS:
        if re.search(pattern, sanitized, re.IGNORECASE):
            logger.warning(
                "Potential prompt injection (%s) from user=%s — message: %.200s",
                category,
                user_id or "anonymous",
                sanitized,
            )
            break

    return sanitized
