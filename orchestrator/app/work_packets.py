from __future__ import annotations

from typing import Any


def _result_title(result: dict[str, Any]) -> str:
    service = str(result.get("service") or "source")
    acronyms = {"sql": "SQL", "kb": "KB"}
    return " ".join(acronyms.get(part, part.title()) for part in service.split("_"))


def _extract_signals(result: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    metrics = result.get("metrics") or {}
    if isinstance(metrics, dict) and "active_deals_count" in metrics:
        signals.append(f"active_deals_count:{metrics['active_deals_count']}")

    cards = result.get("kpi_cards") or []
    for card in cards if isinstance(cards, list) else []:
        if isinstance(card, dict) and card.get("name") == "Active Deals":
            signals.append(f"active_deals_count:{card.get('value')}")
    return signals


def build_work_packet(
    reply: str,
    tool_calls: list[dict[str, Any]],
    mcp_results: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence = [
        {
            "source": str(result.get("service") or "unknown"),
            "title": _result_title(result),
            "summary": str(result.get("summary") or "Data retrieved"),
            "signals": _extract_signals(result),
            "raw": result,
        }
        for result in mcp_results
    ]
    comparable_signals = [tuple(item["signals"]) for item in evidence if item["signals"]]
    unique_signals = set(comparable_signals)
    if len(comparable_signals) >= 2 and len(unique_signals) > 1:
        reconciliation_status = "conflicting"
    elif len(comparable_signals) >= 2 and len(unique_signals) == 1:
        reconciliation_status = "confirmed"
    else:
        reconciliation_status = "partial"
    return {
        "answer": {"summary": reply},
        "reconciliation": {
            "status": reconciliation_status,
            "source_count": len(evidence),
            "notes": [],
        },
        "evidence": evidence,
        "suggested_actions": [],
        "suggested_exports": ["pdf", "docx", "xlsx"],
        "tool_calls": tool_calls,
    }
