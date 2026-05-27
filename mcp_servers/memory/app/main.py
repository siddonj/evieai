"""Memory / Personal Context MCP Server — Per-user context, preferences, and history."""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mcp-memory", version="0.1.0")

# ═══════════════════════════════════════════════════════════════════════
#  IN-MEMORY USER CONTEXT STORE  —  Rich Demo Data
# ═══════════════════════════════════════════════════════════════════════

_USER_CONTEXTS: dict[str, dict[str, Any]] = {
    "admin": {
        "user_id": "admin",
        "profile": {
            "name": "Alex Chen",
            "role": "Chief Financial Officer",
            "department": "Finance & Executive Leadership",
            "reports_to": "CEO",
            "direct_reports": ["VP Finance", "Controller", "Head of Investor Relations"],
            "location": "Northeast HQ",
            "timezone": "America/New_York",
        },
        "preferences": {
            "data_focus": ["revenue", "cash_flow", "margin_analysis", "board_metrics", "investor_kpis"],
            "preferred_format": "executive_summary_with_charts",
            "alert_thresholds": {
                "cash_runway_months": 12,
                "churn_rate_pct": 4.0,
                "pipeline_coverage_ratio": 3.0,
            },
            "language": "en-US",
            "communication_style": "concise_bullet_points",
        },
        "recent_topics": [
            "Q2-2026 earnings preparation",
            "Series B term sheet review",
            "Board meeting May 15",
            "Northwind Traders $450K deal close",
            "Adventure Works churn risk mitigation",
            "FY2027 budget planning",
            "Security audit readiness",
        ],
        "bookmarks": [
            {"type": "file", "name": "Board-Deck-Q2-Review.pptx", "reason": "Board meeting May 15"},
            {"type": "file", "name": "Q2-2026-Revenue-Report.xlsx", "reason": "Earnings prep"},
            {"type": "sop", "id": "sop-005", "reason": "Security audit prep"},
            {"type": "email_thread", "subject": "RE: Board Presentation — May Financials", "reason": "Pending board approval"},
        ],
        "frequent_queries": [
            "Show me the sales pipeline",
            "What is our cash runway",
            "Find unread revenue emails",
            "Q2 board deck status",
            "At-risk customer accounts",
        ],
        "role_based_defaults": {
            "default_tool": "query_sql",
            "dashboard_widgets": ["pipeline_funnel", "cash_forecast", "churn_risk_matrix", "nrr_trend"],
            "morning_briefing": True,
            "weekly_digest_day": "Monday",
        },
    },
    "demo-user": {
        "user_id": "demo-user",
        "profile": {
            "name": "Jordan Smith",
            "role": "Sales Director",
            "department": "Sales",
            "reports_to": "VP Sales",
            "direct_reports": ["Enterprise AE", "Mid-Market AE", "Sales Development Rep"],
            "location": "West Coast",
            "timezone": "America/Los_Angeles",
        },
        "preferences": {
            "data_focus": ["sales_pipeline", "deal_velocity", "win_rates", "territory_performance", "competitor_intel"],
            "preferred_format": "tabular_with_action_items",
            "alert_thresholds": {
                "deal_stagnant_days": 21,
                "pipeline_coverage_ratio": 2.5,
                "quota_attainment_pct": 75,
            },
            "language": "en-US",
            "communication_style": "conversational_with_examples",
        },
        "recent_topics": [
            "Northwind Traders deal negotiation",
            "Q2 territory rebalancing",
            "Fabrikam churn risk — competitor pricing",
            "Blue Yonder Airlines $390K enterprise deal",
            "Sales kickoff agenda July",
            "New rep onboarding — Tailspin Toys",
        ],
        "bookmarks": [
            {"type": "file", "name": "Sales-Pipeline-Q2.xlsx", "reason": "Daily pipeline review"},
            {"type": "file", "name": "Enterprise-Deal-Northwind-Traders.docx", "reason": "Closing next week"},
            {"type": "email_thread", "subject": "Customer Churn Alert — Adventure Works", "reason": "Retention action needed"},
        ],
        "frequent_queries": [
            "Show me the sales pipeline",
            "What deals are closing this month",
            "Find customer churn alerts",
            "Territory performance Q2",
            "Competitor pricing intel",
        ],
        "role_based_defaults": {
            "default_tool": "query_sql",
            "dashboard_widgets": ["pipeline_funnel", "deal_timeline", "win_rate_by_rep", "territory_heatmap"],
            "morning_briefing": True,
            "weekly_digest_day": "Monday",
        },
    },
    "engineer1": {
        "user_id": "engineer1",
        "profile": {
            "name": "Taylor Park",
            "role": "Engineering Lead",
            "department": "Engineering",
            "reports_to": "VP Engineering",
            "direct_reports": ["Senior Backend Engineer", "DevOps Engineer", "QA Lead"],
            "location": "Remote — Midwest",
            "timezone": "America/Chicago",
        },
        "preferences": {
            "data_focus": ["incident_response", "sprint_velocity", "system_uptime", "technical_debt", "security_posture"],
            "preferred_format": "detailed_with_logs",
            "alert_thresholds": {
                "uptime_sla_pct": 99.9,
                "p1_incident_response_min": 15,
                "security_scan_critical": 0,
            },
            "language": "en-US",
            "communication_style": "technical_precise",
        },
        "recent_topics": [
            "Project Phoenix — 68% complete, under budget $80K",
            "Security incident response drill — May 20",
            "SOP-007 review — Incident Response protocol",
            "Disaster recovery failover test",
            "Azure Container Apps scaling configuration",
            "Data Classification policy update — SOP-002",
        ],
        "bookmarks": [
            {"type": "sop", "id": "sop-007", "reason": "Incident response reference"},
            {"type": "sop", "id": "sop-002", "reason": "Data classification guide"},
            {"type": "file", "name": "Project-Phoenix-Status-Report-May.docx", "reason": "Weekly status"},
            {"type": "email_thread", "subject": "Security Incident Response Drill — May 20", "reason": "Preparation"},
        ],
        "frequent_queries": [
            "Show me incident response SOPs",
            "Project Phoenix status",
            "Security compliance documents",
            "Recent system incidents",
            "Disaster recovery procedures",
        ],
        "role_based_defaults": {
            "default_tool": "query_knowledge_base",
            "dashboard_widgets": ["sprint_burndown", "incident_timeline", "uptime_dashboard", "security_scan_status"],
            "morning_briefing": False,
            "weekly_digest_day": "Friday",
        },
    },
}

# Generic template for users created via Settings page
_DEFAULT_CONTEXT: dict[str, Any] = {
    "user_id": "",
    "profile": {
        "name": "",
        "role": "User",
        "department": "General",
        "reports_to": "",
        "direct_reports": [],
        "location": "Remote",
        "timezone": "America/New_York",
    },
    "preferences": {
        "data_focus": ["general_business"],
        "preferred_format": "summary",
        "alert_thresholds": {},
        "language": "en-US",
        "communication_style": "balanced",
    },
    "recent_topics": [],
    "bookmarks": [],
    "frequent_queries": [],
    "role_based_defaults": {
        "default_tool": "query_knowledge_base",
        "dashboard_widgets": [],
        "morning_briefing": False,
        "weekly_digest_day": "Monday",
    },
}


class QueryRequest(BaseModel):
    query: str
    user_id: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-memory", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "memory"}


def _get_context(user_id: str | None) -> dict[str, Any]:
    """Retrieve user context, falling back to default template."""
    if user_id and user_id in _USER_CONTEXTS:
        return _USER_CONTEXTS[user_id]
    # Return a generic context with user_id filled in
    ctx = _DEFAULT_CONTEXT.copy()
    ctx["user_id"] = user_id or "anonymous"
    return ctx


def _extract_relevant(ctx: dict[str, Any], query: str) -> dict[str, Any]:
    """Extract query-relevant snippets from the full context."""
    q = query.lower()
    snippets: list[dict[str, Any]] = []

    # Check recent topics
    for topic in ctx.get("recent_topics", []):
        if any(w in topic.lower() for w in q.split() if len(w) > 2):
            snippets.append({"type": "recent_topic", "content": topic})

    # Check bookmarks
    for bm in ctx.get("bookmarks", []):
        reason = bm.get("reason", "")
        name = bm.get("name", bm.get("id", ""))
        if any(w in (reason + " " + name).lower() for w in q.split() if len(w) > 2):
            snippets.append({"type": "bookmark", "content": bm})

    # Check frequent queries
    for fq in ctx.get("frequent_queries", []):
        if any(w in fq.lower() for w in q.split() if len(w) > 2):
            snippets.append({"type": "frequent_query", "content": fq})

    return {
        "profile_summary": _profile_summary(ctx.get("profile", {})),
        "preferences": ctx.get("preferences", {}),
        "role_based_defaults": ctx.get("role_based_defaults", {}),
        "relevant_snippets": snippets,
        "total_topics": len(ctx.get("recent_topics", [])),
        "total_bookmarks": len(ctx.get("bookmarks", [])),
    }


def _profile_summary(profile: dict[str, Any]) -> str:
    """Create a concise profile string for the LLM system prompt."""
    parts = []
    if profile.get("name"):
        parts.append(f"Name: {profile['name']}")
    if profile.get("role"):
        parts.append(f"Role: {profile['role']}")
    if profile.get("department"):
        parts.append(f"Department: {profile['department']}")
    if profile.get("data_focus"):
        parts.append(f"Focus areas: {', '.join(profile['data_focus'])}")
    if profile.get("communication_style"):
        parts.append(f"Communication style: {profile['communication_style']}")
    return " | ".join(parts) if parts else "General user"


@app.post("/mcp/query")
def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    ctx = _get_context(payload.user_id)
    relevant = _extract_relevant(ctx, payload.query)

    # Determine query intent
    intent = "context_retrieval"
    q = payload.query.lower()
    if any(w in q for w in ("profile", "who am i", "my role", "about me")):
        intent = "profile_summary"
    elif any(w in q for w in ("bookmark", "saved", "favorite", "pinned")):
        intent = "bookmarks"
    elif any(w in q for w in ("recent", "history", "last time", "what did i")):
        intent = "recent_history"
    elif any(w in q for w in ("preference", "setting", "config", "default")):
        intent = "preferences"

    return {
        "service": "memory",
        "query": payload.query,
        "user_id": payload.user_id or "anonymous",
        "intent": intent,
        "profile": ctx.get("profile", {}),
        "preferences": ctx.get("preferences", {}),
        "recent_topics": ctx.get("recent_topics", []),
        "bookmarks": ctx.get("bookmarks", []),
        "frequent_queries": ctx.get("frequent_queries", []),
        "role_based_defaults": ctx.get("role_based_defaults", {}),
        "relevant_snippets": relevant["relevant_snippets"],
        "summary": f"Retrieved context for {ctx.get('profile', {}).get('name', 'user')} ({ctx.get('profile', {}).get('role', 'unknown')}). {relevant['total_topics']} recent topics, {relevant['total_bookmarks']} bookmarks.",
    }


@app.get("/admin/data")
def admin_get_data() -> dict[str, Any]:
    return {
        "service": "memory",
        "total_users": len(_USER_CONTEXTS),
        "users": list(_USER_CONTEXTS.keys()),
        "contexts": _USER_CONTEXTS,
    }


@app.post("/admin/data")
def admin_post_data(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = payload.get("user_id")
    ctx = payload.get("context")
    if not user_id or not ctx or not isinstance(ctx, dict):
        return {"error": "Missing 'user_id' or 'context' field"}
    _USER_CONTEXTS[user_id] = ctx
    return {"service": "memory", "action": "upserted", "user_id": user_id, "total_users": len(_USER_CONTEXTS)}
