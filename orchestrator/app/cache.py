"""Redis-backed caching layer with in-memory fallback.

Caches:
  - MCP tool results per {service}:{query_hash} (TTL 60s)
  - OpenAI responses per prompt hash (TTL 300s)
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any


REDIS_URL = os.getenv("REDIS_URL", "")

_redis_client: Any = None


def _get_redis():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if REDIS_URL:
        try:
            import redis
            _redis_client = redis.from_url(REDIS_URL, socket_timeout=3, decode_responses=True)
            _redis_client.ping()
            return _redis_client
        except Exception:
            pass
    return None


# In-memory fallback
_mem_cache: dict[str, tuple[float, Any]] = {}


def _hash_key(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{digest}"


def _now() -> float:
    return time.monotonic()


def get(prefix: str, *key_parts: str) -> Any | None:
    """Retrieve a cached value by prefix and composite key parts."""
    key = _hash_key(prefix, *key_parts)
    r = _get_redis()
    if r:
        try:
            raw = r.get(key)
            if raw:
                return json.loads(raw)
        except Exception:
            pass

    entry = _mem_cache.get(key)
    if entry and entry[0] > _now():
        return entry[1]
    return None


def set(prefix: str, value: Any, ttl: int, *key_parts: str) -> None:
    """Store a value with composite key and TTL in seconds."""
    key = _hash_key(prefix, *key_parts)
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, default=str))
        except Exception:
            pass

    _mem_cache[key] = (_now() + ttl, value)
    _prune_mem()


def _prune_mem() -> None:
    now = _now()
    expired = [k for k, v in _mem_cache.items() if v[0] <= now]
    for k in expired:
        del _mem_cache[k]
    if len(_mem_cache) > 500:
        oldest = sorted(_mem_cache.items(), key=lambda x: x[1][0])[:100]
        for k, _ in oldest:
            del _mem_cache[k]


def invalidate(prefix: str, *key_parts: str) -> None:
    """Remove a cached entry."""
    key = _hash_key(prefix, *key_parts)
    r = _get_redis()
    if r:
        try:
            r.delete(key)
        except Exception:
            pass
    _mem_cache.pop(key, None)
