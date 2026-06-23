"""Document Generation MCP Server — Multifamily & Brokerage report templates + export (Excel/Word/PDF)."""
from __future__ import annotations

import io
import re
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

# Eager imports so Azure Container Apps doesn't time out on first request while
# packages are being loaded. weasyprint in particular scans fonts on first import
# which can take 10-30s on a cold container.
try:
    import openpyxl as _openpyxl  # noqa: F401
    import docx as _docx  # noqa: F401
    import weasyprint as _weasyprint  # noqa: F401
except ImportError:
    pass  # missing libs surface as HTTPException 500 when the endpoint is called

app = FastAPI(title="mcp-document-generation", version="0.3.0")

# ═══════════════════════════════════════════════════════════════════════
#  DEMO DATA  —  Multifamily & Brokerage Document Templates
# ═══════════════════════════════════════════════════════════════════════

_DOCUMENT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "doc-mf-001",
        "type": "portfolio_summary",
        "title": "Q2 2026 Portfolio Performance Summary",
        "generated_at": "2026-05-19T10:00:00Z",
        "author": "ResiQ Brokerage Analytics",
        "status": "Generated",
        "pages": 4,
        "word_count": 1450,
        "sections": [
            {
                "heading": "Portfolio Overview",
                "content": "The Memphis multifamily portfolio consists of 8 properties totaling 1,248 units with 92.8% occupancy. Total portfolio value estimated at $178.9M with aggregate NOI of $11.0M. Average cap rate of 6.0% across the portfolio. Rent growth of 4.8% YoY outpaces the Memphis MSA average of 3.2%.",
                "key_metrics": [
                    {"label": "Properties", "value": "8", "trend": "1,248 units"},
                    {"label": "Portfolio Value", "value": "$178.9M", "trend": "+12% YoY"},
                    {"label": "Occupancy", "value": "92.8%", "trend": "+1.2pp QoQ"},
                    {"label": "Avg Rent", "value": "$1,333", "trend": "+4.8% YoY"},
                    {"label": "Total NOI", "value": "$11.0M", "trend": "+8.2% TTM"},
                    {"label": "Avg Cap Rate", "value": "6.0%", "trend": "Stable"},
                ],
            },
            {
                "heading": "Class A Assets — Downtown & Germantown",
                "content": "The Emerson (312 units, $1,895 avg rent, 5.2% cap) and The Vue at Madison (240 units, $1,625 avg rent, 5.8% cap) represent the top of the portfolio. Combined value: $98.6M. These institutional-quality assets are attracting Blackstone and Invesco-level buyers. Average occupancy of 94.1% with 6.2% YoY rent growth in the downtown submarket.",
                "key_metrics": [
                    {"label": "The Emerson", "value": "$66.3M", "trend": "312 units, 5.2% cap"},
                    {"label": "The Vue at Madison", "value": "$32.3M", "trend": "240 units, 5.8% cap"},
                    {"label": "Village at Germantown", "value": "$23.1M", "trend": "156 units, Under Contract"},
                ],
            },
            {
                "heading": "Value-Add & Workforce Housing",
                "content": "Oakwood Crossings (96 units, $1,095 rent, 6.2% cap) presents the clearest value-add opportunity with current rents 18% below market. Highland Ridge (64 units, $975 rent, 6.8% cap) benefits from University of Memphis proximity. Southgate Village (128 units, $845 rent, 7.5% cap) maintains 98% occupancy with stable Section 8 voucher income.",
                "key_metrics": [
                    {"label": "Oakwood Crossings", "value": "$10.5M", "trend": "6.2% cap, value-add"},
                    {"label": "Highland Ridge", "value": "$5.6M", "trend": "6.8% cap, near U of M"},
                    {"label": "Southgate Village", "value": "$6.4M", "trend": "7.5% cap, workforce"},
                ],
            },
            {
                "heading": "Market Context",
                "content": "Memphis MSA continues to benefit from supply constraints — new deliveries down 15% YoY to 420 units. Job growth at 2.1% exceeds national average. Class A cap rates compressing to 5.0-5.8% as institutional capital targets Sunbelt secondary markets. Downtown submarket strongest with 6.2% YoY rent growth.",
                "key_metrics": [
                    {"label": "Market Occupancy", "value": "91.5%", "trend": "+0.8pp QoQ"},
                    {"label": "New Supply", "value": "420 units", "trend": "-15% YoY"},
                    {"label": "Class A Cap Rate", "value": "5.0-5.8%", "trend": "Tightening"},
                    {"label": "Job Growth", "value": "+2.1%", "trend": "Above national"},
                ],
            },
        ],
        "action_items": [
            "Schedule seller update for Village at Germantown — closing Q3 2026",
            "Prepare Oakwood Crossings value-add business plan for buyer tour follow-up",
            "Monitor Invesco LOI progress on The Emerson — backup offers if needed",
            "Update portfolio OM with Q2 2026 financial data by June 1",
        ],
        "tags": ["portfolio", "quarterly", "performance", "memphis"],
    },
    {
        "id": "doc-mf-002",
        "type": "offering_memorandum",
        "title": "Offering Memorandum — The Vue at Madison",
        "generated_at": "2026-05-19T14:00:00Z",
        "author": "ResiQ Brokerage",
        "status": "Draft",
        "pages": 18,
        "word_count": 3200,
        "sections": [
            {
                "heading": "Executive Summary",
                "content": "The Vue at Madison is a 240-unit Class A multifamily asset in downtown Memphis. Built in 2018, the property offers studio, one, and two-bedroom units with an average rent of $1,625. Current NOI of $1.87M at a 5.8% cap rate. Listed at $35.8M ($149K/unit). Current occupancy: 95% (228 of 240 units). Blackstone Real Estate under contract at $34M in due diligence.",
                "key_metrics": [
                    {"label": "Total Units", "value": "240", "trend": "Studio, 1BR, 2BR mix"},
                    {"label": "Year Built", "value": "2018", "trend": "Class A construction"},
                    {"label": "NOI", "value": "$1.87M", "trend": "5.8% cap rate"},
                    {"label": "List Price", "value": "$35.8M", "trend": "$149K/unit"},
                    {"label": "Occupancy", "value": "95%", "trend": "228 units occupied"},
                ],
            },
            {
                "heading": "Location & Demographics",
                "content": "Located at 123 Madison Ave in downtown Memphis's thriving core. Walking distance to Beale Street, FedExForum, AutoZone Park, and the Mississippi Riverfront. 5-minute drive to I-40/I-55. 15-minute drive to Memphis International Airport. Average household income within 3-mile radius: $82K. Population growth: +8% since 2020. Walk score: 92.",
                "key_metrics": [
                    {"label": "Walk Score", "value": "92", "trend": "Walker's Paradise"},
                    {"label": "3-Mile HH Income", "value": "$82K", "trend": "+12% since 2020"},
                    {"label": "Population Growth", "value": "+8%", "trend": "Since 2020"},
                    {"label": "Avg Rent Premium", "value": "22%", "trend": "vs market avg"},
                ],
            },
            {
                "heading": "Financial Summary",
                "content": "Stabilized NOI of $1.87M with 15% upside through rent growth and expense optimization. Current average rent $1,625 vs market comps of $1,850 ($225/unit upside). Expense ratio of 38% vs market average of 42%. Capital reserve funded at $250/unit/year. Roof (2018), HVAC (2018), parking garage (2018) — all near-new with minimal deferred maintenance.",
                "key_metrics": [
                    {"label": "Current NOI", "value": "$1.87M", "trend": "5.8% cap"},
                    {"label": "Pro Forma NOI", "value": "$2.15M", "trend": "6.7% cap stabilized"},
                    {"label": "Rent Upside", "value": "$225/unit", "trend": "14% below market"},
                    {"label": "Expense Ratio", "value": "38%", "trend": "vs 42% market"},
                ],
            },
            {
                "heading": "Unit Mix & Amenities",
                "content": "Mix: 48 studios ($1,295), 120 one-bedrooms ($1,595), 72 two-bedrooms ($1,895). Unit features: quartz countertops, stainless steel appliances, in-unit washer/dryer, smart locks, walk-in closets. Amenities: resort-style pool, fitness center, rooftop lounge with skyline views, covered parking, pet park with dog spa, co-working lounge, 24/7 package lockers.",
                "key_metrics": [
                    {"label": "Studio", "value": "48 units", "trend": "$1,295 avg"},
                    {"label": "1BR", "value": "120 units", "trend": "$1,595 avg"},
                    {"label": "2BR", "value": "72 units", "trend": "$1,895 avg"},
                    {"label": "Pet Units", "value": "60%", "trend": "Pet park + dog spa"},
                ],
            },
        ],
        "action_items": [
            "Update OM with final due diligence findings from purchaser's Phase I",
            "Prepare rent comp exhibits for Blackstone underwriting team",
            "Confirm closing timeline with title company for August 31 target",
        ],
        "tags": ["offering memorandum", "the vue", "downtown", "class a"],
    },
    {
        "id": "doc-mf-003",
        "type": "market_survey",
        "title": "Memphis Multifamily Market Survey — Q2 2026",
        "generated_at": "2026-05-19T09:00:00Z",
        "author": "ResiQ Research",
        "status": "Generated",
        "pages": 6,
        "word_count": 2100,
        "sections": [
            {
                "heading": "Market Overview",
                "content": "Memphis multifamily market continues to strengthen with 91.5% average occupancy (+0.8pp QoQ) and 3.2% YoY rent growth. Supply constraints support landlord fundamentals — only 420 new units delivered in 2025 vs 720 peak in 2022. Job growth of 2.1% driven by logistics (FedEx, Amazon), healthcare (St. Jude, Methodist), and technology sectors.",
                "key_metrics": [
                    {"label": "Market Occupancy", "value": "91.5%", "trend": "+0.8pp QoQ"},
                    {"label": "Avg Rent", "value": "$1,285", "trend": "+3.2% YoY"},
                    {"label": "New Supply", "value": "420 units", "trend": "-15% YoY"},
                    {"label": "Absorption", "value": "380 units", "trend": "92% leased"},
                ],
            },
            {
                "heading": "Submarket Analysis — Downtown",
                "content": "Downtown Memphis (38103) is the strongest submarket with 93.8% occupancy and 6.2% YoY rent growth. The Emerson (opened 2021) and The Vue (2018) anchor the luxury segment with rents averaging $1,750+. New supply limited to adaptive reuse projects. Walkable amenities, riverfront access, and entertainment district drive demand from young professionals.",
                "key_metrics": [
                    {"label": "Downtown Occupancy", "value": "93.8%", "trend": "+1.5pp QoQ"},
                    {"label": "Downtown Avg Rent", "value": "$1,750+", "trend": "+6.2% YoY"},
                    {"label": "Luxury Rent Premium", "value": "+42%", "trend": "vs portfolio avg"},
                    {"label": "Downtown Population", "value": "12,400", "trend": "+18% since 2020"},
                ],
            },
            {
                "heading": "Submarket Analysis — East Memphis / Germantown",
                "content": "East Memphis (38117, 38119) and Germantown (38138) represent stable suburban submarkets with 92.1% occupancy and 2.8% YoY rent growth. Strong school districts and corporate employment anchors. Average rent of $1,375 for Class B and $1,650 for Class A. Value-add opportunities in aging 1970s-1990s garden-style product.",
                "key_metrics": [
                    {"label": "Suburban Occupancy", "value": "92.1%", "trend": "+0.5pp QoQ"},
                    {"label": "Suburban Avg Rent", "value": "$1,375", "trend": "+2.8% YoY"},
                    {"label": "Value-Add Spread", "value": "18%", "trend": "Below market avg"},
                    {"label": "Avg Days on Market", "value": "24", "trend": "-3 days YoY"},
                ],
            },
            {
                "heading": "Sales & Cap Rate Trends",
                "content": "Class A cap rates compressed to 5.0-5.8% as institutional capital targets Memphis for higher yields vs primary markets (NYC 4.0%, LA 3.8%). Class B/C at 6.5-7.5% stable. Dollar volume Q1 2026: $185M (+35% YoY). Average price/unit: $145K Class A, $78K Class B, $52K Class C. Buyer mix: 40% institutional, 35% private equity, 25% local/regional.",
                "key_metrics": [
                    {"label": "Class A Cap Rate", "value": "5.0-5.8%", "trend": "Tightening"},
                    {"label": "Class B/C Cap Rate", "value": "6.5-7.5%", "trend": "Stable"},
                    {"label": "Q1 Sales Volume", "value": "$185M", "trend": "+35% YoY"},
                    {"label": "Avg Price/Unit A", "value": "$145K", "trend": "Class A"},
                ],
            },
        ],
        "action_items": [
            "Update market comps for The Emerson offering memorandum",
            "Prepare East Memphis value-add analysis for Oakwood Crossings buyer",
            "Monitor downtown luxury supply pipeline for competitive positioning",
        ],
        "tags": ["market survey", "memphis", "quarterly", "submarket"],
    },
    {
        "id": "doc-mf-004",
        "type": "broker_price_opinion",
        "title": "Broker Price Opinion — Oakwood Crossings",
        "generated_at": "2026-05-19T11:30:00Z",
        "author": "Linda Thornton, Cushman & Wakefield",
        "status": "Draft",
        "pages": 8,
        "word_count": 1800,
        "sections": [
            {
                "heading": "Property Overview",
                "content": "Oakwood Crossings is a 96-unit garden-style multifamily property at 4525 Oakwood Dr, Memphis, TN 38117. Built 1985 on 5.1 acres. Unit mix: 1BR/1BA (32 units, 685 SF), 2BR/1BA (40 units, 895 SF), 2BR/2BA (24 units, 1,050 SF). Currently 82 units occupied (85.4% occupancy). Average rent $1,095. Condition: B- (40% renovated, deferred maintenance on remaining 60%).",
                "key_metrics": [
                    {"label": "Total Units", "value": "96", "trend": "85.4% occupied"},
                    {"label": "Avg Rent", "value": "$1,095", "trend": "18% below market"},
                    {"label": "Year Built", "value": "1985", "trend": "Garden-style"},
                    {"label": "Lot", "value": "5.1 acres", "trend": "5.3 units/acre"},
                ],
            },
            {
                "heading": "Comparable Sales Analysis",
                "content": "Three recent comparable sales: (1) Highland Ridge (64 units, $5.6M, $87.5K/unit, 6.8% cap) — similar vintage and condition. (2) Poplar Pointe (72 units, $9.5M, $131.9K/unit, 5.9% cap) — renovated, better East Memphis location. (3) Midsouth Village (112 units, $8.2M, $73.2K/unit, 7.2% cap) — unrenovated, lower quality. Oakwood Crossings positioned between Highland Ridge and Poplar Pointe at an estimated $10.5-12.5M.",
                "key_metrics": [
                    {"label": "Highland Ridge", "value": "$87.5K/unit", "trend": "6.8% cap"},
                    {"label": "Poplar Pointe", "value": "$131.9K/unit", "trend": "5.9% cap, renovated"},
                    {"label": "Midsouth Village", "value": "$73.2K/unit", "trend": "7.2% cap, unrenovated"},
                    {"label": "Estimated Value", "value": "$10.5-12.5M", "trend": "$109-130K/unit"},
                ],
            },
            {
                "heading": "Value-Add Analysis",
                "content": "Current NOI of $648K at 6.2% pro forma cap rate. After $1.2M in capital improvements (roof, HVAC replacements, interior renovations in 60% unrenovated units), pro forma NOI of $845K achievable. Stabilized value: $12.8M at 6.6% cap. Value creation: $2.3M above current value. Renovation scope: new countertops, appliances, LVP flooring, lighting, fixtures ($18.7K/unit average).",
                "key_metrics": [
                    {"label": "Current NOI", "value": "$648K", "trend": "6.2% pro forma cap"},
                    {"label": "Pro Forma NOI", "value": "$845K", "trend": "+$197K upside"},
                    {"label": "Renovation Cost", "value": "$1.2M", "trend": "$18.7K/unit"},
                    {"label": "Stabilized Value", "value": "$12.8M", "trend": "$2.3M value-add"},
                ],
            },
            {
                "heading": "Recommendation",
                "content": "Recommended list price: $12.5M ($130K/unit) with a sell range of $11.0-12.5M. Optimal buyer profile: value-add private equity fund or experienced local operator. Target cap rate: 6.0-6.5%. Marketing strategy: targeted outreach to 1031 exchange buyers and SE value-add funds. Estimated DOM: 45-60 days at $12.5M list. Commission: 3% ($375K at $12.5M).",
                "key_metrics": [
                    {"label": "Recommended List", "value": "$12.5M", "trend": "$130K/unit"},
                    {"label": "Sell Range", "value": "$11.0-12.5M", "trend": "6.0-6.5% cap"},
                    {"label": "Est. DOM", "value": "45-60 days", "trend": "At $12.5M list"},
                    {"label": "Commission", "value": "$375K", "trend": "3% at list price"},
                ],
            },
        ],
        "action_items": [
            "Prepare full OM with renovation pro forma for buyer distribution",
            "Identify 1031 exchange buyers with Q3 2026 deadline",
            "Engage contractor for renovation cost verification",
            "Schedule BPO presentation with Oakwood Holdings LLC",
        ],
        "tags": ["broker price opinion", "bpo", "oakwood", "value-add"],
    },
    {
        "id": "doc-mf-005",
        "type": "commission_report",
        "title": "Q2 2026 Commission & Activity Report",
        "generated_at": "2026-05-19T16:00:00Z",
        "author": "ResiQ Brokerage Systems",
        "status": "Generated",
        "pages": 2,
        "word_count": 850,
        "sections": [
            {
                "heading": "YTD Commission Summary",
                "content": "Year-to-date gross commission income of $956.5K across 3 closed deals totaling $36.3M. Current active pipeline of 5 deals totaling $144.2M with $3.5M in projected commission. Average commission rate of 2.8% across all transactions. On pace for $2M+ annual GCI — 65% ahead of last year's pace.",
                "key_metrics": [
                    {"label": "GCI YTD", "value": "$956.5K", "trend": "+65% YoY"},
                    {"label": "Closed Volume YTD", "value": "$36.3M", "trend": "3 deals"},
                    {"label": "Pipeline Value", "value": "$144.2M", "trend": "5 deals"},
                    {"label": "Projected Pipeline Comm.", "value": "$3.5M", "trend": "2.4% avg"},
                    {"label": "Projected Annual GCI", "value": "$2.0M+", "trend": "+65% YoY pace"},
                ],
            },
            {
                "heading": "Closed Transactions",
                "content": "Two closed sales in Q2: (1) Riverside Heights — $26.5M sale price, $662.5K commission, 2.5% rate. Closed May 1. (2) Poplar Pointe — $9.8M sale price, $294K commission, 3.0% rate. Closed May 15. Both transactions involved Linda Thornton (buyer side) and Thomas Garrett (seller side). Average time from LOI to close: 94 days.",
                "key_metrics": [
                    {"label": "Riverside Heights", "value": "$662.5K", "trend": "$26.5M, 2.5%"},
                    {"label": "Poplar Pointe", "value": "$294K", "trend": "$9.8M, 3.0%"},
                    {"label": "Avg LOI-to-Close", "value": "94 days", "trend": "Both Q2 deals"},
                    {"label": "Avg Commission", "value": "2.75%", "trend": "Blended rate"},
                ],
            },
            {
                "heading": "Active Pipeline Details",
                "content": "Village at Germantown ($24.5M, closing) — $735K commission, closing Q3. The Vue at Madison ($34M, due diligence) — $850K commission. Oakwood Crossings ($11.5M, LOI) — $345K commission. The Emerson ($68M, LOI) — $1.36M commission. Highland Ridge ($6.2M, underwriting) — $217K commission. Total: $144.2M, $3.5M commission.",
                "key_metrics": [
                    {"label": "Deal Count", "value": "5 active", "trend": "$144.2M total"},
                    {"label": "Largest Deal", "value": "$68M", "trend": "The Emerson — $1.36M commission"},
                    {"label": "Avg Active Deal", "value": "$28.8M", "trend": "Ranging $6.2-68M"},
                    {"label": "Commission at Risk", "value": "$3.5M", "trend": "Blended 2.4%"},
                ],
            },
            {
                "heading": "Business Development Activity",
                "content": "14 activities logged YTD: 6 property tours, 3 inspections/appraisals, 3 meetings/calls, 2 appraisals. 8 new listings taken totaling 1.14M SF. 4 repeat clients representing 40% of YTD revenue. Exclusive listings (3 of 8) commanding 3.5% average commission vs 2.3% for co-listings.",
                "key_metrics": [
                    {"label": "Activities YTD", "value": "14", "trend": "Tours, inspections, calls"},
                    {"label": "New Listings", "value": "8", "trend": "1.14M SF total"},
                    {"label": "Repeat Clients", "value": "4", "trend": "40% of YTD rev"},
                    {"label": "Exclusive Listings", "value": "3", "trend": "3.5% avg vs 2.3% co-list"},
                ],
            },
        ],
        "action_items": [
            "Prepare Q2 pipeline review presentation for managing director",
            "Activate backup offer strategy on The Emerson",
            "Follow up on Warburg Realty Trust for next acquisition mandate",
            "Schedule Q3 goal setting with Linda Thornton",
        ],
        "tags": ["commission", "report", "quarterly", "pipeline"],
    },
]


def _score(doc: dict[str, Any], q: str) -> int:
    """Simple keyword relevance score."""
    text = " ".join([
        doc.get("title", ""),
        doc.get("type", ""),
        " ".join(doc.get("tags", [])),
        " ".join(s.get("heading", "") for s in doc.get("sections", [])),
    ]).lower()
    words = q.lower().split()
    return sum(3 if w in doc.get("title", "").lower() else 1 for w in words if w in text)


class QueryRequest(BaseModel):
    query: str
    user_id: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-document-generation", "status": "ok", "version": "0.3.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "document_generation"}


@app.post("/mcp/query")
def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    q = payload.query.lower()

    type_filter = None
    if any(w in q for w in ("portfolio summary", "portfolio performance", "portfolio overview")):
        type_filter = "portfolio_summary"
    elif any(w in q for w in ("offering memorandum", "om", "offering memo", "offering")):
        type_filter = "offering_memorandum"
    elif any(w in q for w in ("market survey", "market report", "market analysis", "market research", "comps")):
        type_filter = "market_survey"
    elif any(w in q for w in ("broker price opinion", "bpo", "price opinion", "valuation")):
        type_filter = "broker_price_opinion"
    elif any(w in q for w in ("commission report", "commission summary", "gci", "commission")):
        type_filter = "commission_report"

    candidates = [d for d in _DOCUMENT_TEMPLATES if (type_filter is None or d["type"] == type_filter)]

    scored = [(d, _score(d, q)) for d in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    results = [d for d, s in scored if s > 0][:2]
    if not results:
        results = [d for d, s in scored[:1]]

    return {
        "service": "document_generation",
        "query": payload.query,
        "user_id": payload.user_id or "anonymous",
        "summary": f"Found {len(results)} document(s)",
        "documents": results,
    }


@app.get("/admin/data")
def admin_get_data() -> dict[str, Any]:
    return {
        "service": "document_generation",
        "total_templates": len(_DOCUMENT_TEMPLATES),
        "templates": [{"id": d["id"], "type": d["type"], "title": d["title"]} for d in _DOCUMENT_TEMPLATES],
    }


@app.post("/admin/data")
def admin_post_data(payload: dict[str, Any]) -> dict[str, Any]:
    doc = payload.get("document")
    if not doc or not isinstance(doc, dict):
        return {"error": "Missing 'document' field"}
    if "id" not in doc or "title" not in doc:
        return {"error": "Document must have 'id' and 'title'"}
    existing = [d for d in _DOCUMENT_TEMPLATES if d.get("id") == doc["id"]]
    if existing:
        _DOCUMENT_TEMPLATES[_DOCUMENT_TEMPLATES.index(existing[0])] = doc
        return {"service": "document_generation", "action": "updated", "id": doc["id"], "total": len(_DOCUMENT_TEMPLATES)}
    _DOCUMENT_TEMPLATES.append(doc)
    return {"service": "document_generation", "action": "added", "id": doc["id"], "total": len(_DOCUMENT_TEMPLATES)}


# ═══════════════════════════════════════════════════════════════════════
#  EXPORT — Models
# ═══════════════════════════════════════════════════════════════════════

class ExportRequest(BaseModel):
    type: str  # "report" | "table"
    format: str  # "xlsx" | "docx" | "pdf"
    title: str
    data: dict[str, Any]


def _report_sections(payload: ExportRequest) -> list[dict[str, Any]]:
    sections = payload.data.get("sections", [])
    if isinstance(sections, list) and sections:
        return [section for section in sections if isinstance(section, dict)]

    title = payload.title.strip() or "Generated document"
    return [
        {
            "heading": title,
            "content": "No structured sections were returned with this document.",
            "key_metrics": [],
        }
    ]


# ═══════════════════════════════════════════════════════════════════════
#  EXPORT — Generators
# ═══════════════════════════════════════════════════════════════════════

def _sanitize_name(title: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9]+", "-", title).strip("-").lower()
    return name[:60] or "export"


def _generate_excel(payload: ExportRequest) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

    wb = Workbook()
    ws = wb.active
    ws.title = payload.title[:31] or "Export"

    header_font = Font(bold=True, size=14, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    section_font = Font(bold=True, size=12, color="1F4E79")
    metric_header_font = Font(bold=True, size=10, color="FFFFFF")
    metric_header_fill = PatternFill(start_color="2E75B6", end_color="2E75B6", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin"),
    )
    wrap = Alignment(wrap_text=True, vertical="top")

    if payload.type == "report":
        data = payload.data
        sections = _report_sections(payload)
        action_items = data.get("action_items", [])
        tags = data.get("tags", [])

        row = 1
        ws.cell(row=row, column=1, value=payload.title).font = header_font
        ws.cell(row=row, column=1).fill = header_fill
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        ws.cell(row=row, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[row].height = 30

        for section in sections:
            row += 2
            ws.cell(row=row, column=1, value=section.get("heading", "")).font = section_font
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)

            row += 1
            ws.cell(row=row, column=1, value=section.get("content", "")).alignment = wrap
            ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
            ws.row_dimensions[row].height = 60

            metrics = section.get("key_metrics", [])
            if metrics:
                row += 1
                for col, h in enumerate(["Metric", "Value", "Trend"], 1):
                    c = ws.cell(row=row, column=col, value=h)
                    c.font = metric_header_font
                    c.fill = metric_header_fill
                    c.border = thin_border
                    c.alignment = Alignment(horizontal="center")
                for m in metrics:
                    row += 1
                    ws.cell(row=row, column=1, value=m.get("label", "")).border = thin_border
                    ws.cell(row=row, column=2, value=m.get("value", "")).border = thin_border
                    ws.cell(row=row, column=3, value=m.get("trend", "")).border = thin_border

        if action_items:
            row += 2
            ws.cell(row=row, column=1, value="Action Items").font = section_font
            for item in action_items:
                row += 1
                ws.cell(row=row, column=1, value=f"  {item}").alignment = wrap

        if tags:
            row += 2
            ws.cell(row=row, column=1, value="Tags").font = section_font
            row += 1
            ws.cell(row=row, column=1, value=", ".join(tags))

        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 30

    else:
        headers = payload.data.get("headers", [])
        rows = payload.data.get("rows", [])

        ws.cell(row=1, column=1, value=payload.title).font = header_font
        ws.cell(row=1, column=1).fill = header_fill
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=max(len(headers), 1))
        ws.cell(row=1, column=1).alignment = Alignment(horizontal="center")
        ws.row_dimensions[1].height = 30

        if headers:
            for col, h in enumerate(headers, 1):
                c = ws.cell(row=2, column=col, value=h)
                c.font = metric_header_font
                c.fill = metric_header_fill
                c.border = thin_border
                c.alignment = Alignment(horizontal="center")

        for r_idx, row_data in enumerate(rows, 3 if headers else 2):
            for c_idx, val in enumerate(row_data, 1):
                ws.cell(row=r_idx, column=c_idx, value=str(val)).border = thin_border

        for i, _h in enumerate(headers, 1):
            ws.column_dimensions[chr(64 + i) if i <= 26 else f"A{i}"].width = 25

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _generate_docx(payload: ExportRequest) -> bytes:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    doc = Document()

    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(11)
    style.paragraph_format.space_after = Pt(6)

    title_para = doc.add_heading(payload.title, level=1)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER

    if payload.type == "report":
        data = payload.data
        sections = _report_sections(payload)
        action_items = data.get("action_items", [])
        tags = data.get("tags", [])

        for section in sections:
            doc.add_heading(section.get("heading", ""), level=2)
            doc.add_paragraph(section.get("content", ""))

            metrics = section.get("key_metrics", [])
            if metrics:
                table = doc.add_table(rows=1, cols=3)
                table.style = "Light Grid Accent 1"
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                hdr = table.rows[0].cells
                for i, heading in enumerate(["Metric", "Value", "Trend"]):
                    hdr[i].text = heading
                    for p in hdr[i].paragraphs:
                        for r in p.runs:
                            r.bold = True
                            r.font.size = Pt(9)
                for m in metrics:
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(m.get("label", ""))
                    row_cells[1].text = str(m.get("value", ""))
                    row_cells[2].text = str(m.get("trend", ""))
                    for cell in row_cells:
                        for p in cell.paragraphs:
                            for r in p.runs:
                                r.font.size = Pt(9)

                doc.add_paragraph()

        if action_items:
            doc.add_heading("Action Items", level=2)
            for item in action_items:
                doc.add_paragraph(item, style="List Bullet")

        if tags:
            doc.add_heading("Tags", level=2)
            doc.add_paragraph(", ".join(tags))

    else:
        headers = payload.data.get("headers", [])
        rows = payload.data.get("rows", [])

        if headers:
            table = doc.add_table(rows=1, cols=len(headers))
            table.style = "Light Grid Accent 1"
            table.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = table.rows[0].cells
            for i, h in enumerate(headers):
                hdr[i].text = h
                for p in hdr[i].paragraphs:
                    for r in p.runs:
                        r.bold = True

            for row_data in rows:
                row_cells = table.add_row().cells
                for i, val in enumerate(row_data):
                    if i < len(row_cells):
                        row_cells[i].text = str(val)

    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _generate_pdf(payload: ExportRequest) -> bytes:
    from weasyprint import HTML

    if payload.type == "report":
        data = payload.data
        sections = _report_sections(payload)
        action_items = data.get("action_items", [])
        tags = data.get("tags", [])
        table_headers = []
        table_rows = []
    else:
        sections = []
        action_items = []
        tags = payload.data.get("tags", [])
        table_headers = payload.data.get("headers", [])
        table_rows = payload.data.get("rows", [])

    metric_rows = ""
    for s in sections:
        metrics_html = ""
        for m in s.get("key_metrics", []):
            metrics_html += f"""
            <tr>
                <td style="padding:4px 8px;border:1px solid #ccc;font-size:9pt;">{m.get('label','')}</td>
                <td style="padding:4px 8px;border:1px solid #ccc;font-size:9pt;font-weight:bold;">{m.get('value','')}</td>
                <td style="padding:4px 8px;border:1px solid #ccc;font-size:9pt;color:#666;">{m.get('trend','')}</td>
            </tr>"""

        section_html = f"""
        <div style="page-break-inside:avoid;margin-bottom:20px;">
            <h2 style="color:#1F4E79;font-size:14pt;border-bottom:2px solid #1F4E79;padding-bottom:4px;">{s.get('heading','')}</h2>
            <p style="font-size:10pt;line-height:1.5;color:#333;">{s.get('content','')}</p>
            {f'<table style="width:100%;border-collapse:collapse;margin-top:8px;">{metrics_html}</table>' if metrics_html else ''}
        </div>"""
        metric_rows += section_html

    table_html = ""
    if table_headers:
        th = "".join(f"<th style='padding:6px 10px;border:1px solid #ccc;background:#2E75B6;color:#fff;font-size:9pt;text-align:left;'>{h}</th>" for h in table_headers)
        tr = ""
        for row in table_rows:
            td = "".join(f"<td style='padding:4px 8px;border:1px solid #ccc;font-size:9pt;'>{str(v)}</td>" for v in row)
            tr += f"<tr>{td}</tr>"
        table_html = f"""
        <table style="width:100%;border-collapse:collapse;margin-top:10px;">
            <tr>{th}</tr>
            {tr}
        </table>"""

    actions_html = ""
    if action_items:
        items = "".join(f"<li style='font-size:10pt;margin-bottom:4px;'>{item}</li>" for item in action_items)
        actions_html = f"""
        <div style="page-break-inside:avoid;margin-top:20px;">
            <h2 style="color:#1F4E79;font-size:14pt;border-bottom:2px solid #1F4E79;padding-bottom:4px;">Action Items</h2>
            <ul>{items}</ul>
        </div>"""

    tags_html = ""
    if tags:
        tags_html = f"""
        <div style="page-break-inside:avoid;margin-top:20px;">
            <h2 style="color:#1F4E79;font-size:14pt;border-bottom:2px solid #1F4E79;padding-bottom:4px;">Tags</h2>
            <p style="font-size:10pt;color:#666;">{', '.join(tags)}</p>
        </div>"""

    html_str = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {{ margin: 1.5cm 2cm; }}
        body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #333; }}
    </style>
</head>
<body>
    <h1 style="color:#1F4E79;font-size:18pt;text-align:center;margin-bottom:24px;">{payload.title}</h1>
    {metric_rows}
    {table_html}
    {actions_html}
    {tags_html}
</body>
</html>"""

    pdf_bytes = HTML(string=html_str).write_pdf()
    if not pdf_bytes:
        raise RuntimeError(
            "weasyprint produced an empty PDF. "
            "Check that fontconfig and system fonts are installed in the container."
        )
    return pdf_bytes


# ═══════════════════════════════════════════════════════════════════════
#  EXPORT — Endpoints
# ═══════════════════════════════════════════════════════════════════════

FORMAT_MAP = {
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "pdf": ("application/pdf", ".pdf"),
}


@app.post("/export")
def export_document(payload: ExportRequest) -> Response:
    fmt_info = FORMAT_MAP.get(payload.format)
    if not fmt_info:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {payload.format}")
    content_type, ext = fmt_info

    try:
        if payload.format == "xlsx":
            content = _generate_excel(payload)
        elif payload.format == "docx":
            content = _generate_docx(payload)
        elif payload.format == "pdf":
            content = _generate_pdf(payload)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {payload.format}")
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Export library not available: {e.name}. Run: pip install {e.name}",
        ) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export generation failed: {e}") from e

    filename = f"{_sanitize_name(payload.title)}{ext}"
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
