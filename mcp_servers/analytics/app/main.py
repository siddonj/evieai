"""Analytics MCP Server — Multifamily & Brokerage KPIs, trends, and insights."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mcp-analytics", version="0.2.0")

# ═══════════════════════════════════════════════════════════════════════
#  DEMO DATA  —  Multifamily & Brokerage Analytics
# ═══════════════════════════════════════════════════════════════════════

_ANALYTICS_CATEGORIES: dict[str, dict[str, Any]] = {
    "portfolio": {
        "category": "Portfolio Performance",
        "kpi_cards": [
            {"name": "Portfolio Value", "value": "$215.4M", "change": "+14%", "period": "YoY", "status": "positive", "target": "$200M", "target_status": "exceeded"},
            {"name": "Occupancy Rate", "value": "92.5%", "change": "+1.0pp", "period": "QoQ", "status": "positive", "target": "92%", "target_status": "exceeded"},
            {"name": "Avg Rent/Unit", "value": "$1,287", "change": "+4.5%", "period": "YoY", "status": "positive", "target": "+3.5%", "target_status": "exceeded"},
            {"name": "Total NOI", "value": "$13.5M", "change": "+8.5%", "period": "TTM", "status": "positive", "target": "$12.5M", "target_status": "exceeded"},
            {"name": "Avg Cap Rate", "value": "6.1%", "change": "+0.1pp", "period": "YoY", "status": "neutral", "target": "5.5-6.5%", "target_status": "on_track"},
            {"name": "Rent Collection", "value": "98.0%", "change": "+0.3pp", "period": "QoQ", "status": "positive", "target": "97%", "target_status": "exceeded"},
            {"name": "Units Under Mgmt", "value": "1,650", "change": "+402", "period": "YoY", "status": "positive", "target": "1,500", "target_status": "exceeded"},
        ],
        "trends": [
            {"metric": "Occupancy Rate", "data": [{"month": "Jan", "value": 91.0}, {"month": "Feb", "value": 91.3}, {"month": "Mar", "value": 91.8}, {"month": "Apr", "value": 92.2}, {"month": "May", "value": 92.5}], "trend_direction": "up", "trend_strength": "steady"},
            {"metric": "Average Rent", "data": [{"quarter": "Q1-2025", "value": 1210}, {"quarter": "Q2-2025", "value": 1230}, {"quarter": "Q3-2025", "value": 1250}, {"quarter": "Q4-2025", "value": 1265}, {"quarter": "Q1-2026", "value": 1278}, {"quarter": "Q2-2026", "value": 1287}], "trend_direction": "up", "trend_strength": "steady"},
        ],
        "insights": [
            "Portfolio expanded to 12 properties (1,650 units) with addition of student housing, senior living, and mixed-use assets",
            "Average rent growth of 4.5% YoY exceeds market average of 3.2% for Memphis MSA",
            "Student housing (University Village) adds 725/unit average — 93% occupancy with 62% renewal rate",
            "Senior living (The Gardens at Shelby) at 95% occupancy with waitlist — strong demographic tailwind",
            "Cordova Station adds 168 units in growing suburban submarket at 1185/unit with 3% annual rent growth",
        ],
    },
    "pipeline": {
        "category": "Deal Pipeline",
        "kpi_cards": [
            {"name": "Active Pipeline Value", "value": "$197.2M", "change": "+35%", "period": "QoQ", "status": "positive", "target": "$150M", "target_status": "exceeded"},
            {"name": "Active Deals", "value": "9", "change": "+4", "period": "QoQ", "status": "positive", "target": "6", "target_status": "exceeded"},
            {"name": "Total Commission Pipeline", "value": "$4.3M", "change": "+25%", "period": "QoQ", "status": "positive", "target": "$3.5M", "target_status": "exceeded"},
            {"name": "Closed YTD", "value": "$36.3M", "change": "3 deals", "period": "YTD", "status": "positive", "target": "$45M", "target_status": "on_track"},
            {"name": "Commission Earned YTD", "value": "$956.5K", "change": "+65%", "period": "YTD", "status": "positive", "target": "800K", "target_status": "exceeded"},
            {"name": "Avg Days on Market", "value": "32", "change": "-5", "period": "days YoY", "status": "positive", "target": "35", "target_status": "below_target"},
            {"name": "Win Rate", "value": "75%", "change": "+10pp", "period": "YoY", "status": "positive", "target": "65%", "target_status": "exceeded"},
            {"name": "Avg Deal Size", "value": "$18.2M", "change": "+8%", "period": "YoY", "status": "positive", "target": "$15M", "target_status": "exceeded"},
        ],
        "trends": [
            {"metric": "Pipeline Value", "data": [{"month": "Jan", "value": 98}, {"month": "Feb", "value": 108}, {"month": "Mar", "value": 125}, {"month": "Apr", "value": 165}, {"month": "May", "value": 197}], "trend_direction": "up", "trend_strength": "strong"},
            {"metric": "Commission Pipeline", "data": [{"quarter": "Q1-2025", "value": 1.8}, {"quarter": "Q2-2025", "value": 2.1}, {"quarter": "Q3-2025", "value": 2.4}, {"quarter": "Q4-2025", "value": 2.8}, {"quarter": "Q1-2026", "value": 3.5}, {"quarter": "Q2-2026", "value": 4.3}], "trend_direction": "up", "trend_strength": "strong"},
        ],
        "insights": [
            "Pipeline at $197.2M — highest in firm history, driven by The Emerson ($68M), The Vue ($34M), and new Emerson refi ($45M)",
            "Portfolio deal (Southgate + Highland Ridge bundled at $14.5M) expanding buyer pool with value-add investors",
            "New ground lease mandate for The Gardens at Shelby adds $85K NOI annuity at 4% commission",
            "Germantown development parcel ($3.2M LOI) diversifies pipeline into land/development advisory",
            "Win rate holding at 75% — two closed deals YTD with strong Q3-Q4 closing pipeline ($110M under LOI/DD)",
        ],
    },
    "market": {
        "category": "Market Analytics — Memphis MSA",
        "kpi_cards": [
            {"name": "Market Avg Occupancy", "value": "91.5%", "change": "+0.8pp", "period": "QoQ", "status": "positive", "target": "90%", "target_status": "exceeded"},
            {"name": "Market Avg Rent", "value": "$1,285", "change": "+3.2%", "period": "YoY", "status": "positive", "target": "+2.5%", "target_status": "exceeded"},
            {"name": "Class A Cap Rate", "value": "5.2-5.8%", "change": "tightening", "period": "QoQ", "status": "neutral", "target": "5.0-6.0%", "target_status": "on_track"},
            {"name": "Class B/C Cap Rate", "value": "6.5-7.5%", "change": "stable", "period": "QoQ", "status": "neutral", "target": "6.0-7.5%", "target_status": "on_track"},
            {"name": "New Supply (2026)", "value": "420 units", "change": "-15%", "period": "YoY", "status": "positive", "target": "<500", "target_status": "below_target"},
            {"name": "Memphis Population", "value": "633,104", "change": "+0.6%", "period": "YoY", "status": "positive", "target": "growth", "target_status": "on_track"},
            {"name": "Job Growth", "value": "+2.1%", "change": "+0.3pp", "period": "YoY", "status": "positive", "target": "+1.5%", "target_status": "exceeded"},
            {"name": "Avg Rent/SF", "value": "$1.42", "change": "+0.05", "period": "YoY", "status": "positive", "target": "$1.35", "target_status": "exceeded"},
        ],
        "trends": [
            {"metric": "Market Occupancy", "data": [{"quarter": "Q1-2025", "value": 89.8}, {"quarter": "Q2-2025", "value": 90.2}, {"quarter": "Q3-2025", "value": 90.5}, {"quarter": "Q4-2025", "value": 90.7}, {"quarter": "Q1-2026", "value": 91.0}, {"quarter": "Q2-2026", "value": 91.5}], "trend_direction": "up", "trend_strength": "steady"},
            {"metric": "New Supply", "data": [{"year": 2021, "value": 680}, {"year": 2022, "value": 720}, {"year": 2023, "value": 580}, {"year": 2024, "value": 495}, {"year": 2025, "value": 420}], "trend_direction": "down", "trend_strength": "steady"},
        ],
        "insights": [
            "Memphis MF market remains supply-constrained — new deliveries down 15% YoY, supporting rent growth",
            "Class A cap rates compressing as institutional capital targets Sunbelt secondary markets",
            "Downtown submarket seeing strongest rent growth at +6.2% YoY, driven by The Emerson and new amenities",
            "Workforce housing (Class B/C) showing resilient occupancy at 94%, outperforming Class A at 91%",
            "Job growth at 2.1% outpacing national average, with logistics and healthcare sectors leading",
        ],
    },
    "brokerage": {
        "category": "Agent & Team Performance",
        "kpi_cards": [
            {"name": "Listings Taken YTD", "value": "12", "change": "+5", "period": "YoY", "status": "positive", "target": "9", "target_status": "exceeded"},
            {"name": "Total SF Listed", "value": "1.45M", "change": "+35%", "period": "YoY", "status": "positive", "target": "1.1M", "target_status": "exceeded"},
            {"name": "Avg Commission Rate", "value": "2.7%", "change": "+0.1pp", "period": "YoY", "status": "positive", "target": "2.5%", "target_status": "exceeded"},
            {"name": "Total GCI YTD", "value": "$956.5K", "change": "+65%", "period": "YoY", "status": "positive", "target": "$800K", "target_status": "exceeded"},
            {"name": "Repeat Clients", "value": "5", "change": "+3", "period": "YTD", "status": "positive", "target": "3", "target_status": "exceeded"},
            {"name": "Avg Days to Close", "value": "45", "change": "-5", "period": "days", "status": "positive", "target": "50", "target_status": "below_target"},
        ],
        "trends": [
            {"metric": "Gross Commission Income", "data": [{"quarter": "Q1-2025", "value": 325}, {"quarter": "Q2-2025", "value": 380}, {"quarter": "Q3-2025", "value": 420}, {"quarter": "Q4-2025", "value": 470}, {"quarter": "Q1-2026", "value": 520}, {"quarter": "Q2-2026", "value": 437}], "trend_direction": "up", "trend_strength": "strong"},
            {"metric": "Listings Taken", "data": [{"quarter": "Q1-2025", "value": 3}, {"quarter": "Q2-2025", "value": 4}, {"quarter": "Q3-2025", "value": 4}, {"quarter": "Q4-2025", "value": 5}, {"quarter": "Q1-2026", "value": 7}, {"quarter": "Q2-2026", "value": 5}], "trend_direction": "up", "trend_strength": "steady"},
        ],
        "insights": [
            "12 listings taken YTD (1.45M SF) — diversified across MF, student housing, senior living, and development land",
            "GCI pacing toward $2M+ annual — 65% ahead of last year with strong Q3 pipeline",
            "5 repeat clients accounting for 45% of YTD revenue — referral network strengthening",
            "Service line expansion into ground lease negotiation and development advisory adding new revenue streams",
            "Exclusive listings (5 of 12) command 3.2% average commission vs 2.3% for co-listings",
        ],
    },
}

# Align with old name for backward compat in queries
_DEMO_DATA = _ANALYTICS_CATEGORIES


def _determine_category(q: str) -> str | None:
    """Map query to analytics category."""
    q = q.lower()
    if any(w in q for w in ("portfolio", "property", "occupancy", "rent", "noi", "cap rate", "unit", "building", "asset")):
        return "portfolio"
    elif any(w in q for w in ("pipeline", "deal", "commission", "closing", "loi", "due diligence", "stage", "offer")):
        return "pipeline"
    elif any(w in q for w in ("market", "memphis", "supply", "demographic", "job growth", "population", "submarket")):
        return "market"
    elif any(w in q for w in ("agent", "brokerage", "gci", "listing", "commission rate", "volume", "team", "performance")):
        return "brokerage"
    return None


class QueryRequest(BaseModel):
    query: str
    user_id: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-analytics", "status": "ok", "version": "0.2.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "analytics"}


@app.post("/mcp/query")
def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    q = payload.query.lower()
    category = _determine_category(q)

    if category and category in _ANALYTICS_CATEGORIES:
        data = _ANALYTICS_CATEGORIES[category]
        return {
            "service": "analytics",
            "mode": "demo",
            "query": payload.query,
            "category": category,
            "category_name": data["category"],
            "kpi_cards": data["kpi_cards"],
            "trends": data["trends"],
            "insights": data["insights"],
            "summary": f"Returning {data['category']} analytics — {len(data['kpi_cards'])} KPIs, {len(data['trends'])} trends, {len(data['insights'])} insights.",
        }

    # No specific category matched — return a high-level overview across all categories
    return {
        "service": "analytics",
        "mode": "demo",
        "query": payload.query,
        "summary": "Multifamily & brokerage analytics overview across all categories.",
        "categories": [
            {
                "name": cat["category"],
                "key": key,
                "kpi_count": len(cat["kpi_cards"]),
                "headline_kpis": [k["name"] for k in cat["kpi_cards"][:3]],
            }
            for key, cat in _ANALYTICS_CATEGORIES.items()
        ],
        "insights": [
            insight
            for cat in _ANALYTICS_CATEGORIES.values()
            for insight in cat["insights"]
        ],
    }
