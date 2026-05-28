"""Unit tests for the orchestrator security module."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "orchestrator"))

import pytest
from app.security import CircuitBreaker, CircuitOpenError, RateLimiter, validate_and_sanitize


class TestRateLimiter:
    def test_allows_requests_within_limit(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.is_allowed("user-1")
        assert limiter.is_allowed("user-1")
        assert limiter.is_allowed("user-1")

    def test_blocks_requests_over_limit(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("user-2")
        assert limiter.is_allowed("user-2")
        assert not limiter.is_allowed("user-2")

    def test_separate_buckets_per_key(self):
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        assert limiter.is_allowed("user-a")
        assert limiter.is_allowed("user-a")
        assert limiter.is_allowed("user-b")  # different key, should be allowed

    def test_remaining_counts_down(self):
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.remaining("user-3") == 3
        limiter.is_allowed("user-3")
        assert limiter.remaining("user-3") == 2


class TestCircuitBreaker:
    def test_passes_through_on_success(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_seconds=30)
        result = cb.call("svc", lambda: 42)
        assert result == 42

    def test_opens_after_failures(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_seconds=30)

        def fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            cb.call("svc", fail)
        with pytest.raises(RuntimeError):
            cb.call("svc", fail)

        with pytest.raises(CircuitOpenError):
            cb.call("svc", lambda: 42)

    def test_resets_after_recovery(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_seconds=0)

        def fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            cb.call("svc", fail)
        with pytest.raises(RuntimeError):
            cb.call("svc", fail)

        time.sleep(0.1)
        result = cb.call("svc", lambda: 99)  # recovery time = 0, should reset
        assert result == 99


class TestInputValidation:
    def test_passes_clean_message(self):
        result = validate_and_sanitize("Show me the sales pipeline")
        assert result == "Show me the sales pipeline"

    def test_rejects_empty_message(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException, match="cannot be empty"):
            validate_and_sanitize("   ")

    def test_rejects_too_long_message(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException, match="too long"):
            validate_and_sanitize("x" * 5000)

    def test_allows_message_at_limit(self):
        msg = "x" * 4000
        result = validate_and_sanitize(msg)
        assert len(result) == 4000
