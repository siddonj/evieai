from __future__ import annotations

import urllib.parse
from typing import Any

from fastapi import FastAPI, Response
from pydantic import BaseModel

from mcp_servers.common.graph_client import GraphClient


app = FastAPI(title="mcp-onedrive", version="0.2.0")
graph_client = GraphClient.from_env()


class QueryRequest(BaseModel):
    query: str


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-onedrive", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "onedrive"}


@app.post("/mcp/query")
async def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    # Real Graph calls are used only when credentials are configured.
    _demo_files = [
        # Finance
        {"name": "Q2-2026-Revenue-Report.xlsx", "size": 485760, "lastModifiedDateTime": "2026-05-05T09:15:00Z", "folder": "Finance", "description": "Q2 2026 revenue breakdown by region and product line. Total revenue: $12.4M (+18% YoY)."},
        {"name": "FY2026-Budget-Master.xlsx", "size": 892100, "lastModifiedDateTime": "2026-05-03T14:22:00Z", "folder": "Finance", "description": "Annual budget with department allocations, OPEX and CAPEX forecasts."},
        {"name": "Q1-Profit-and-Loss-Statement.pdf", "size": 1248576, "lastModifiedDateTime": "2026-04-15T11:00:00Z", "folder": "Finance", "description": "Q1 P&L: Gross profit $4.2M, operating margin 22%, net income $1.8M."},
        {"name": "Cash-Flow-Projection-May-2026.xlsx", "size": 356200, "lastModifiedDateTime": "2026-05-06T08:45:00Z", "folder": "Finance", "description": "30-day rolling cash flow forecast. Current runway: 14 months."},
        {"name": "Board-Deck-Q2-Review.pptx", "size": 2150400, "lastModifiedDateTime": "2026-05-02T16:30:00Z", "folder": "Finance", "description": "Executive board presentation with KPIs, revenue charts, and strategic initiatives."},
        {"name": "Investor-Update-May-2026.docx", "size": 189600, "lastModifiedDateTime": "2026-05-01T10:15:00Z", "folder": "Finance", "description": "Monthly investor newsletter: ARR growth, churn rate (3.2%), NRR (118%)."},
        {"name": "Tax-Preparation-2025-Final.xlsx", "size": 1048576, "lastModifiedDateTime": "2026-03-20T09:00:00Z", "folder": "Finance", "description": "Completed FY2025 tax filings and supporting schedules."},
        # Sales
        {"name": "Sales-Pipeline-Q2.xlsx", "size": 433120, "lastModifiedDateTime": "2026-05-05T08:30:00Z", "folder": "Sales", "description": "Active pipeline: $8.7M across 42 opportunities. 3 deals expected to close this month."},
        {"name": "Enterprise-Deal-Northwind-Traders.docx", "size": 156800, "lastModifiedDateTime": "2026-05-04T13:20:00Z", "folder": "Sales", "description": "Proposed $450K annual contract with Northwind Traders. Terms and pricing sheet attached."},
        {"name": "Customer-Churn-Analysis-Q1-2026.pptx", "size": 1843200, "lastModifiedDateTime": "2026-04-25T11:00:00Z", "folder": "Sales", "description": "Root cause analysis of 12 churned accounts. Primary driver: pricing sensitivity."},
        {"name": "Territory-Assignment-2026.xlsx", "size": 224560, "lastModifiedDateTime": "2026-01-10T09:00:00Z", "folder": "Sales", "description": "Regional rep assignments and quota targets for FY2026."},
        # Projects
        {"name": "Project-Phoenix-Scope-of-Work.docx", "size": 189600, "lastModifiedDateTime": "2026-05-03T10:00:00Z", "folder": "Projects", "description": "Scope document for cloud migration initiative. Budget: $1.2M, timeline 6 months."},
        {"name": "Project-Phoenix-Status-Report-May.docx", "size": 142000, "lastModifiedDateTime": "2026-05-06T07:30:00Z", "folder": "Projects", "description": "Weekly status: 68% complete, 2 weeks ahead of schedule, under budget by $80K."},
        {"name": "Project-Atlas-Requirements.pdf", "size": 987136, "lastModifiedDateTime": "2026-04-20T15:45:00Z", "folder": "Projects", "description": "Product requirements for AI-powered analytics module. Launch target: Q4 2026."},
        # HR
        {"name": "Employee-Handbook-2026.pdf", "size": 2048576, "lastModifiedDateTime": "2026-01-15T09:00:00Z", "folder": "HR", "description": "Updated company policies, remote work guidelines, and benefits overview."},
        {"name": "Headcount-Plan-FY2026.xlsx", "size": 312400, "lastModifiedDateTime": "2026-04-10T10:00:00Z", "folder": "HR", "description": "Hiring plan: 28 new roles, $3.1M loaded cost, prioritized by department."},
        # Engineering
        {"name": "System-Architecture-Diagram-v3.vsdx", "size": 712000, "lastModifiedDateTime": "2026-04-29T16:45:00Z", "folder": "Engineering", "description": "Updated microservices architecture with new data pipeline components."},
        {"name": "Security-Audit-Report-Q1-2026.pdf", "size": 1536000, "lastModifiedDateTime": "2026-04-05T09:00:00Z", "folder": "Engineering", "description": "Penetration test results: 2 medium severity findings, remediation complete."},
        {"name": "API-Documentation-v2.4.md", "size": 89000, "lastModifiedDateTime": "2026-05-01T14:00:00Z", "folder": "Engineering", "description": "Public API docs: 47 endpoints, OpenAPI 3.0 spec, authentication flows."},
        # General
        {"name": "All-Hands-Slides-May-2026.pptx", "size": 2560000, "lastModifiedDateTime": "2026-05-05T12:00:00Z", "folder": "General", "description": "Company-wide all-hands deck: hiring milestones, product roadmap, culture highlights."},
        {"name": "Meeting-Notes-Apr-28-Standup.docx", "size": 30480, "lastModifiedDateTime": "2026-04-28T17:30:00Z", "folder": "General", "description": "Weekly standup notes: deployment complete, backlog grooming Thursday."},
        {"name": "Strategic-Plan-2026-2028.docx", "size": 356000, "lastModifiedDateTime": "2026-03-01T09:00:00Z", "folder": "General", "description": "Three-year strategic plan: market expansion, product diversification, M&A targets."},
    ]

    if not graph_client.configured:
        return {
            "service": "onedrive",
            "summary": "Demo mode: returning sample OneDrive file listing",
            "query": payload.query,
            "files": _demo_files,
        }

    try:
        data = await graph_client.get(f"/users/{graph_client.user_upn}/drive/root/children?$top=10")
        items = data.get("value", [])
        return {
            "service": "onedrive",
            "summary": f"Fetched {len(items)} items from OneDrive",
            "query": payload.query,
            "files": items,
        }
    except Exception as exc:  # noqa: BLE001
        # Fallback to demo data when Graph API fails (e.g. personal M365)
        return {
            "service": "onedrive",
            "summary": f"Demo mode (Graph unavailable: {type(exc).__name__}): returning sample OneDrive files",
            "query": payload.query,
            "files": _demo_files,
        }


_content_types: dict[str, str] = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "xls": "application/vnd.ms-excel",
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "ppt": "application/vnd.ms-powerpoint",
    "csv": "text/csv",
    "txt": "text/plain",
    "md": "text/markdown",
    "json": "application/json",
    "vsdx": "application/octet-stream",
}


@app.get("/mcp/files/{file_name:path}/download")
def download_file(file_name: str) -> Response:
    decoded = urllib.parse.unquote(file_name)
    ext = decoded.rsplit(".", 1)[-1].lower() if "." in decoded else ""
    content_type = _content_types.get(ext, "application/octet-stream")

    placeholder = f"Demo file: {decoded}\n\nThis is placeholder content for the '{decoded}' file.\nThe actual file would be served from OneDrive in production.\n"
    return Response(
        content=placeholder.encode("utf-8"),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{decoded}"'},
    )
