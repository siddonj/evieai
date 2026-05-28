from __future__ import annotations

import os
import urllib.parse
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Response
from pydantic import BaseModel

app = FastAPI(title="mcp-file-share", version="0.2.0")
DEFAULT_ROOT = Path(os.getenv("LOCAL_SHARE_ROOT", "/tmp"))


class QueryRequest(BaseModel):
    query: str


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-file-share", "status": "ok"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "file_share"}


_demo_files = [
    {"name": "Q2-2026-Revenue-Report.xlsx", "size": 485760, "modified": "2026-05-05T09:15:00Z", "category": "Finance"},
    {"name": "FY2026-Budget-Master.xlsx", "size": 892100, "modified": "2026-05-03T14:22:00Z", "category": "Finance"},
    {"name": "Q1-Profit-and-Loss-Statement.pdf", "size": 1248576, "modified": "2026-04-15T11:00:00Z", "category": "Finance"},
    {"name": "Cash-Flow-Projection-May-2026.xlsx", "size": 356200, "modified": "2026-05-06T08:45:00Z", "category": "Finance"},
    {"name": "Board-Deck-Q2-Review.pptx", "size": 2150400, "modified": "2026-05-02T16:30:00Z", "category": "Finance"},
    {"name": "Investor-Update-May-2026.docx", "size": 189600, "modified": "2026-05-01T10:15:00Z", "category": "Finance"},
    {"name": "Tax-Preparation-2025-Final.xlsx", "size": 1048576, "modified": "2026-03-20T09:00:00Z", "category": "Finance"},
    {"name": "Sales-Pipeline-Q2.xlsx", "size": 433120, "modified": "2026-05-05T08:30:00Z", "category": "Sales"},
    {"name": "Enterprise-Deal-Northwind-Traders.docx", "size": 156800, "modified": "2026-05-04T13:20:00Z", "category": "Sales"},
    {"name": "Customer-Churn-Analysis-Q1-2026.pptx", "size": 1843200, "modified": "2026-04-25T11:00:00Z", "category": "Sales"},
    {"name": "Territory-Assignment-2026.xlsx", "size": 224560, "modified": "2026-01-10T09:00:00Z", "category": "Sales"},
    {"name": "Project-Phoenix-Scope-of-Work.docx", "size": 189600, "modified": "2026-05-03T10:00:00Z", "category": "Projects"},
    {"name": "Project-Phoenix-Status-Report-May.docx", "size": 142000, "modified": "2026-05-06T07:30:00Z", "category": "Projects"},
    {"name": "Project-Atlas-Requirements.pdf", "size": 987136, "modified": "2026-04-20T15:45:00Z", "category": "Projects"},
    {"name": "Employee-Handbook-2026.pdf", "size": 2048576, "modified": "2026-01-15T09:00:00Z", "category": "HR"},
    {"name": "Headcount-Plan-FY2026.xlsx", "size": 312400, "modified": "2026-04-10T10:00:00Z", "category": "HR"},
    {"name": "System-Architecture-Diagram-v3.vsdx", "size": 712000, "modified": "2026-04-29T16:45:00Z", "category": "Engineering"},
    {"name": "Security-Audit-Report-Q1-2026.pdf", "size": 1536000, "modified": "2026-04-05T09:00:00Z", "category": "Engineering"},
    {"name": "API-Documentation-v2.4.md", "size": 89000, "modified": "2026-05-01T14:00:00Z", "category": "Engineering"},
    {"name": "All-Hands-Slides-May-2026.pptx", "size": 2560000, "modified": "2026-05-05T12:00:00Z", "category": "General"},
    {"name": "Strategic-Plan-2026-2028.docx", "size": 356000, "modified": "2026-03-01T09:00:00Z", "category": "General"},
]


@app.post("/mcp/query")
def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    # Try to list real files; fall back to demo data if empty or error
    entries = []
    try:
        entries = sorted(p.name for p in DEFAULT_ROOT.iterdir())
    except Exception:
        pass

    if entries:
        limited = entries[:20]
        return {
            "service": "file_share",
            "summary": f"Found {len(entries)} entries under {DEFAULT_ROOT}",
            "query": payload.query,
            "items": limited,
        }

    # Demo mode: return rich file listing when no real files exist
    return {
        "service": "file_share",
        "summary": f"Demo mode: returning {len(_demo_files)} sample files from shared storage",
        "query": payload.query,
        "items": _demo_files,
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

    placeholder = f"Demo file: {decoded}\n\nThis is placeholder content for the '{decoded}' file.\nThe actual file would be served from Azure Files in production.\n"
    return Response(
        content=placeholder.encode("utf-8"),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{decoded}"'},
    )
