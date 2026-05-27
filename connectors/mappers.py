from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def map_propexo_record(entity_type: str, raw: Dict[str, Any]) -> Dict[str, Any]:
    """Minimal canonical mapping stub for initial ingestion path.

    This intentionally preserves raw payload while setting core metadata fields.
    Rich per-entity transforms will follow in Phase 2.
    """
    source_record_id = raw.get("id") or raw.get("record_id") or raw.get("uuid")
    updated_at = (
        raw.get("updated_at")
        or raw.get("modified_at")
        or raw.get("last_modified")
        or raw.get("timestamp")
    )

    return {
        "entity_type": entity_type,
        "source_id": "propexo",
        "source_record_id": str(source_record_id) if source_record_id is not None else None,
        "updated_at": _to_iso(updated_at),
        "payload": raw,
    }
