from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

from mcp_servers.common.graph_client import GraphClient

app = FastAPI(title="mcp-o365-mail", version="0.2.0")
graph_client = GraphClient.from_env()


class QueryRequest(BaseModel):
    query: str


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-o365-mail", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "o365_mail"}


@app.post("/mcp/query")
async def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    # Real Graph calls are used only when credentials are configured.
    _demo_messages = [
        # Finance & Revenue
        {
            "subject": "Q2-2026 Revenue Report — $12.4M (+18% YoY)",
            "from": "cfo@contoso.com",
            "receivedDateTime": "2026-05-06T09:00:00Z",
            "bodyPreview": "Q2 revenue exceeded target by 8%. Key drivers: Enterprise segment (+32%), APAC region (+45%). Gross margin held steady at 74%. Attached: detailed breakdown and revised FY2026 forecast.",
            "isRead": False,
            "importance": "high",
        },
        {
            "subject": "RE: Board Presentation — May Financials",
            "from": "finance@contoso.com",
            "receivedDateTime": "2026-05-05T14:22:00Z",
            "bodyPreview": "Board deck is finalized. Key slides: $12.4M Q2 revenue, 22% operating margin, $1.8M net income, ARR $38.2M (+24%). Project Phoenix on track to add $2M ARR by Q4. Need your review by 5pm.",
            "isRead": False,
            "importance": "high",
        },
        {
            "subject": "Cash Flow Alert — Runway Extended to 14 Months",
            "from": "treasury@contoso.com",
            "receivedDateTime": "2026-05-05T11:30:00Z",
            "bodyPreview": "Strong collections in April ($4.1M vs $3.2M target) extended cash runway to 14 months. CapEx for Project Phoenix ($1.2M) approved. No immediate funding needs.",
            "isRead": True,
            "importance": "normal",
        },
        {
            "subject": "Budget Variance Analysis — April 2026",
            "from": "finance@contoso.com",
            "receivedDateTime": "2026-05-04T08:15:00Z",
            "bodyPreview": "April actuals: Revenue $4.1M (102% of plan), COGS under by $120K, Marketing overspend $45K (digital campaigns). YTD operating margin: 22.3%.",
            "isRead": True,
            "importance": "normal",
        },
        {
            "subject": "Investor Update — May 2026 Newsletter",
            "from": "investor-relations@contoso.com",
            "receivedDateTime": "2026-05-03T16:00:00Z",
            "bodyPreview": "This month's highlights: ARR $38.2M, NRR 118%, churn 3.2%, Net Promoter Score 52. Series B discussions progressing with 3 term sheets received. Board meeting scheduled May 15.",
            "isRead": False,
            "importance": "high",
        },
        # Sales
        {
            "subject": "Enterprise Deal — Northwind Traders $450K ARR",
            "from": "sales-ops@contoso.com",
            "receivedDateTime": "2026-05-06T07:45:00Z",
            "bodyPreview": "Northwind Traders signed! 3-year deal at $450K ARR with 95% gross margin. Implementation kickoff June 1. Expansion potential to $800K in Year 2 (multi-division rollout).",
            "isRead": False,
            "importance": "high",
        },
        {
            "subject": "Q2 Sales Pipeline — $8.7M across 42 opportunities",
            "from": "vp-sales@contoso.com",
            "receivedDateTime": "2026-05-05T10:00:00Z",
            "bodyPreview": "Pipeline health check: 3 deals >$500K in final stage (close probability 70%), 12 mid-market deals $50-200K. Risk: 2 enterprise deals pushed to Q3 due to procurement delays.",
            "isRead": True,
            "importance": "normal",
        },
        {
            "subject": "Customer Churn Alert — 2 At-Risk Accounts",
            "from": "customer-success@contoso.com",
            "receivedDateTime": "2026-05-04T13:20:00Z",
            "bodyPreview": "Adventure Works ($85K ARR) and Fabrikam ($120K ARR) flagged at-risk. Root cause: competitor pricing 15% below us. Proposed retention: 10% discount + premium support upgrade. Need approval.",
            "isRead": False,
            "importance": "high",
        },
        # Projects
        {
            "subject": "Project Phoenix Status — 68% Complete, Under Budget",
            "from": "pmo@contoso.com",
            "receivedDateTime": "2026-05-06T08:00:00Z",
            "bodyPreview": "Weekly update: Cloud migration 68% complete (2 weeks ahead). Budget consumed $720K of $1.2M allocated. Remaining work: data migration (2 weeks), UAT (1 week), go-live June 15.",
            "isRead": True,
            "importance": "normal",
        },
        {
            "subject": "Project Atlas — AI Analytics Module Requirements",
            "from": "product@contoso.com",
            "receivedDateTime": "2026-05-03T11:00:00Z",
            "bodyPreview": "PRD approved by steering committee. Budget $850K, timeline 5 months. Key features: predictive churn, revenue forecasting, natural language querying. Launch target Q4 2026.",
            "isRead": True,
            "importance": "normal",
        },
        # Operations
        {
            "subject": "All-Hands — May 5 Recap & Recording",
            "from": "ceo@contoso.com",
            "receivedDateTime": "2026-05-05T18:00:00Z",
            "bodyPreview": "Thanks to everyone who joined. Key themes: $12.4M Q2 beat, hiring 28 new roles, Project Phoenix ahead of schedule, Series B term sheets in hand. Recording and slides attached.",
            "isRead": True,
            "importance": "normal",
        },
        {
            "subject": "Headcount Plan FY2026 — 28 New Roles Approved",
            "from": "hr@contoso.com",
            "receivedDateTime": "2026-05-02T09:30:00Z",
            "bodyPreview": "Board approved 28 new hires: Engineering (12), Sales (8), Customer Success (5), Finance (2), HR (1). Loaded cost $3.1M annually. Priority roles: 3 senior backend engineers, 2 enterprise AEs.",
            "isRead": True,
            "importance": "normal",
        },
        {
            "subject": "Security Audit Complete — 2 Medium Findings Resolved",
            "from": "security@contoso.com",
            "receivedDateTime": "2026-05-01T10:00:00Z",
            "bodyPreview": "Q1 penetration test complete. 2 medium severity findings (SSRF in reporting API, weak password policy) have been patched. No critical or high issues. SOC 2 Type II audit on track for July.",
            "isRead": True,
            "importance": "normal",
        },
    ]

    if not graph_client.configured:
        return {
            "service": "o365_mail",
            "summary": "Demo mode: returning sample mailbox data",
            "query": payload.query,
            "messages": _demo_messages,
        }

    try:
        data = await graph_client.get(f"/users/{graph_client.user_upn}/messages?$top=5")
        items = data.get("value", [])
        return {
            "service": "o365_mail",
            "summary": f"Fetched {len(items)} messages from Microsoft Graph",
            "query": payload.query,
            "messages": items,
        }
    except Exception as exc:  # noqa: BLE001
        # Fallback to demo data when Graph API fails (e.g. personal M365)
        return {
            "service": "o365_mail",
            "summary": f"Demo mode (Graph unavailable: {type(exc).__name__}): returning sample mailbox",
            "query": payload.query,
            "messages": _demo_messages,
        }
