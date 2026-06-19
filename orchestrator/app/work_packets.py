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


def _normalize_evidence(result: dict[str, Any]) -> dict[str, Any]:
    messages = result.get("messages") if isinstance(result.get("messages"), list) else []
    files = result.get("files") if isinstance(result.get("files"), list) else []
    documents = result.get("generated_documents") if isinstance(result.get("generated_documents"), list) else []

    snippets: list[str] = []
    if messages:
        snippets.append(f"{len(messages)} email(s)")
    if files:
        snippets.append(f"{len(files)} file(s)")
    if documents:
        snippets.append(f"{len(documents)} generated document(s)")

    return {
        "source": str(result.get("service") or "unknown"),
        "title": _result_title(result),
        "summary": str(result.get("summary") or "Data retrieved"),
        "signals": _extract_signals(result),
        "snippets": snippets,
        "raw": result,
    }


def _reconciliation_status(evidence: list[dict[str, Any]]) -> str:
    populated = [item for item in evidence if item.get("signals") or item.get("snippets")]
    if len(populated) <= 1:
        return "partial"

    statuses = {tuple(item.get("signals", [])) for item in populated if item.get("signals")}
    return "conflicting" if len(statuses) > 1 else "confirmed"


def _suggested_actions(mcp_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    for result in mcp_results:
        docs = result.get("generated_documents")
        if isinstance(docs, list) and docs:
            title = str((docs[0] or {}).get("title") or "Generated document")
            return [{"type": "review_document", "label": f"Review {title}"}]
    return []


def build_work_packet(
    reply: str,
    tool_calls: list[dict[str, Any]],
    mcp_results: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence = [_normalize_evidence(result) for result in mcp_results]
    return {
        "answer": {"summary": reply},
        "reconciliation": {
            "status": _reconciliation_status(evidence),
            "source_count": len(evidence),
            "notes": [],
        },
        "evidence": evidence,
        "suggested_actions": _suggested_actions(mcp_results),
        "suggested_exports": ["pdf", "docx", "xlsx"],
        "tool_calls": tool_calls,
    }
