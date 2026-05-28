from __future__ import annotations

from datetime import datetime
from typing import Any


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _map_property(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "property_id": raw.get("property_id") or raw.get("id"),
        "name": raw.get("name") or raw.get("property_name"),
        "address": raw.get("address") or raw.get("street"),
        "city": raw.get("city"),
        "state": raw.get("state"),
        "postal_code": raw.get("postal_code") or raw.get("zip"),
        "unit_count": _safe_int(raw.get("unit_count") or raw.get("total_units")),
        "occupancy_rate": _safe_float(raw.get("occupancy_rate")),
        "average_rent": _safe_float(raw.get("average_rent")),
        "status": raw.get("status"),
    }


def _map_resident(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "resident_id": raw.get("resident_id") or raw.get("id"),
        "first_name": raw.get("first_name"),
        "last_name": raw.get("last_name"),
        "full_name": raw.get("full_name")
        or " ".join([v for v in [raw.get("first_name"), raw.get("last_name")] if v]).strip()
        or None,
        "email": raw.get("email"),
        "phone": raw.get("phone") or raw.get("phone_number"),
        "property_id": raw.get("property_id"),
        "unit_id": raw.get("unit_id") or raw.get("unit_number"),
        "lease_id": raw.get("lease_id"),
        "status": raw.get("status"),
        "move_in_date": _to_iso(raw.get("move_in_date")),
        "move_out_date": _to_iso(raw.get("move_out_date")),
    }


def _map_lease(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "lease_id": raw.get("lease_id") or raw.get("id"),
        "resident_id": raw.get("resident_id"),
        "property_id": raw.get("property_id"),
        "unit_id": raw.get("unit_id") or raw.get("unit_number"),
        "start_date": _to_iso(raw.get("start_date") or raw.get("lease_start")),
        "end_date": _to_iso(raw.get("end_date") or raw.get("lease_end")),
        "rent": _safe_float(raw.get("rent") or raw.get("base_rent")),
        "deposit": _safe_float(raw.get("deposit") or raw.get("security_deposit")),
        "status": raw.get("status"),
        "renewal_offer": _to_iso(raw.get("renewal_offer_date")),
    }


def map_propexo_record(entity_type: str, raw: dict[str, Any]) -> dict[str, Any]:
    """Map Propexo payloads into EvieAI canonical ingest envelope."""
    source_record_id = raw.get("id") or raw.get("record_id") or raw.get("uuid")
    updated_at = (
        raw.get("updated_at")
        or raw.get("modified_at")
        or raw.get("last_modified")
        or raw.get("timestamp")
    )

    canonical: dict[str, Any]
    if entity_type == "property":
        canonical = _map_property(raw)
    elif entity_type == "resident":
        canonical = _map_resident(raw)
    elif entity_type == "lease":
        canonical = _map_lease(raw)
    else:
        canonical = {"id": source_record_id}

    return {
        "entity_type": entity_type,
        "source_id": "propexo",
        "source_record_id": str(source_record_id) if source_record_id is not None else None,
        "updated_at": _to_iso(updated_at),
        "canonical": canonical,
        "payload": raw,
    }
