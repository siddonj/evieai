"""Dashboard MCP Server — Unified dashboard views for multifamily & brokerage."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mcp-dashboard", version="0.1.0")

# ═══════════════════════════════════════════════════════════════════════
#  DEMO DATA — Dashboard views derived from the same portfolio as SQL/Analytics
# ═══════════════════════════════════════════════════════════════════════

_PROPERTIES = [
    {"id": 1, "name": "The Vue at Madison", "city": "Memphis", "type": "Multifamily", "units": 240, "occupied": 228, "rent": 1625, "noi": 1872000, "cap": 5.8, "value": 32275862, "status": "Active", "owner": "Madison Street Partners"},
    {"id": 2, "name": "Riverside Heights", "city": "Memphis", "type": "Multifamily", "units": 180, "occupied": 171, "rent": 1475, "noi": 1380000, "cap": 5.5, "value": 25090909, "status": "Active", "owner": "Riverside Capital Group"},
    {"id": 3, "name": "Oakwood Crossings", "city": "Memphis", "type": "Multifamily", "units": 96, "occupied": 82, "rent": 1095, "noi": 648000, "cap": 6.2, "value": 10451613, "status": "Active", "owner": "Oakwood Holdings LLC"},
    {"id": 4, "name": "Highland Ridge", "city": "Memphis", "type": "Multifamily", "units": 64, "occupied": 58, "rent": 975, "noi": 384000, "cap": 6.8, "value": 5647059, "status": "Active", "owner": "Highland Properties LLC"},
    {"id": 5, "name": "The Emerson", "city": "Memphis", "type": "Multifamily", "units": 312, "occupied": 296, "rent": 1895, "noi": 3450000, "cap": 5.2, "value": 66346154, "status": "Active", "owner": "Emerson Development Group"},
    {"id": 6, "name": "Southgate Village", "city": "Memphis", "type": "Multifamily", "units": 128, "occupied": 102, "rent": 845, "noi": 480000, "cap": 7.5, "value": 6400000, "status": "Active", "owner": "Southgate REIT"},
    {"id": 7, "name": "Poplar Pointe", "city": "Memphis", "type": "Multifamily", "units": 72, "occupied": 68, "rent": 1280, "noi": 560000, "cap": 5.9, "value": 9491525, "status": "Active", "owner": "Poplar Pointe Investors"},
    {"id": 8, "name": "Village at Germantown", "city": "Germantown", "type": "Multifamily", "units": 156, "occupied": 148, "rent": 1475, "noi": 1248000, "cap": 5.4, "value": 23111111, "status": "Under Contract", "owner": "Germantown Development LLC"},
    {"id": 9, "name": "University Village", "city": "Memphis", "type": "Student Housing", "units": 120, "occupied": 112, "rent": 725, "noi": 396000, "cap": 7.0, "value": 5657143, "status": "Active", "owner": "U of M Properties LLC"},
    {"id": 10, "name": "The Gardens at Shelby", "city": "Memphis", "type": "Senior Living", "units": 90, "occupied": 86, "rent": 2100, "noi": 856000, "cap": 6.5, "value": 13169231, "status": "Active", "owner": "Shelby Senior Housing Fund"},
    {"id": 11, "name": "Court Square Flats", "city": "Memphis", "type": "Mixed-Use", "units": 24, "occupied": 22, "rent": 1550, "noi": 186000, "cap": 5.5, "value": 3381818, "status": "Active", "owner": "Court Square Development LLC"},
    {"id": 12, "name": "Cordova Station", "city": "Cordova", "type": "Multifamily", "units": 168, "occupied": 154, "rent": 1185, "noi": 1008000, "cap": 5.8, "value": 17379310, "status": "Active", "owner": "Cordova Station Partners"},
]

_DEALS = [
    {"id": 1, "property": "Village at Germantown", "stage": "Closing", "value": 24500000, "commission": 735000, "agent": "Linda Thornton", "buyer": "Warburg Realty Trust", "target_close": "2026-07-15", "status": "Active"},
    {"id": 2, "property": "The Vue at Madison", "stage": "Due Diligence", "value": 34000000, "commission": 850000, "agent": "Linda Thornton", "buyer": "Blackstone Real Estate", "target_close": "2026-08-30", "status": "Active"},
    {"id": 3, "property": "Oakwood Crossings", "stage": "LOI", "value": 11500000, "commission": 345000, "agent": "Michael Davidson", "buyer": "ValueAdd Equity Fund III", "target_close": "2026-09-15", "status": "Active"},
    {"id": 4, "property": "The Emerson", "stage": "LOI", "value": 68000000, "commission": 1360000, "agent": "Linda Thornton", "buyer": "Invesco Real Estate", "target_close": "2026-10-01", "status": "Active"},
    {"id": 5, "property": "Highland Ridge", "stage": "Underwriting", "value": 6200000, "commission": 217000, "agent": "Linda Thornton", "buyer": "Camber Property Group", "target_close": "2026-10-30", "status": "Active"},
    {"id": 6, "property": "Riverside Heights", "stage": "Closed", "value": 26500000, "commission": 662500, "agent": "Linda Thornton", "buyer": "Warburg Realty Trust", "target_close": "2026-05-01", "status": "Closed"},
    {"id": 7, "property": "Poplar Pointe", "stage": "Closed", "value": 9800000, "commission": 294000, "agent": "Linda Thornton", "buyer": "Poplar Pointe Investors", "target_close": "2026-05-15", "status": "Closed"},
    {"id": 8, "property": "Southgate Village", "stage": "Lost", "value": 6800000, "commission": 170000, "agent": "Michael Davidson", "buyer": "N/A", "target_close": None, "status": "Lost"},
    {"id": 9, "property": "The Gardens at Shelby", "stage": "Negotiating", "value": 850000, "commission": 34000, "agent": "Linda Thornton", "buyer": "Shelby Senior Housing Fund", "target_close": "2026-08-01", "status": "Active", "type": "Lease"},
    {"id": 10, "property": "The Emerson", "stage": "Underwriting", "value": 45000000, "commission": 225000, "agent": "Linda Thornton", "buyer": "N/A", "target_close": "2026-08-15", "status": "Active", "type": "Refinance"},
    {"id": 11, "property": "Germantown Land Parcel", "stage": "LOI", "value": 3200000, "commission": 112000, "agent": "Thomas Garrett", "buyer": "Pinnacle Development Group", "target_close": "2026-10-01", "status": "Active", "type": "Land Sale"},
    {"id": 12, "property": "Portfolio: Southgate + Highland", "stage": "LOI", "value": 14500000, "commission": 362500, "agent": "Linda Thornton", "buyer": "BlueSky Capital Partners", "target_close": "2026-09-30", "status": "Active"},
]

_ACTIVITIES = [
    {"id": 1, "type": "Tour", "subject": "ValueAdd Equity tour Oakwood Crossings", "due": "2026-05-15", "agent": "Linda Thornton", "status": "Open"},
    {"id": 2, "type": "Tour", "subject": "Camber Group tour Highland Ridge", "due": "2026-05-20", "agent": "Linda Thornton", "status": "Open"},
    {"id": 3, "type": "Inspection", "subject": "Phase I Environmental — The Vue", "due": "2026-05-25", "agent": "Environmental Partners Inc", "status": "Open"},
    {"id": 4, "type": "Meeting", "subject": "Lender lunch — First Horizon credit review", "due": "2026-05-28", "agent": "Linda Thornton", "status": "Open"},
    {"id": 5, "type": "Meeting", "subject": "Germantown land parcel negotiation", "due": "2026-05-30", "agent": "Thomas Garrett", "status": "Open"},
    {"id": 6, "type": "Meeting", "subject": "JLL collaboration lunch", "due": "2026-06-02", "agent": "Linda Thornton", "status": "Open"},
    {"id": 7, "type": "Tour", "subject": "BlueSky Capital portfolio tour", "due": "2026-06-05", "agent": "Linda Thornton", "status": "Open"},
    {"id": 8, "type": "Inspection", "subject": "The Vue appraisal walk", "due": "2026-06-08", "agent": "Linda Thornton", "status": "Open"},
    {"id": 9, "type": "Tour", "subject": "Harbor Group — Emerson + Vue tour", "due": "2026-06-12", "agent": "Linda Thornton", "status": "Open"},
    {"id": 10, "type": "Appraisal", "subject": "Emerson refinance appraisal", "due": "2026-06-15", "agent": "Memphis Appraisal Group", "status": "Open"},
    {"id": 11, "type": "Tour", "subject": "Blackstone tour The Vue", "due": "2026-04-12", "agent": "Linda Thornton", "status": "Completed"},
    {"id": 12, "type": "Meeting", "subject": "Q2 pipeline review", "due": "2026-05-19", "agent": "Linda Thornton", "status": "Completed"},
]

# ─── Computed metrics ─────────────────────────────────────────────────

def _compute_overview() -> dict[str, Any]:
    total_units = sum(p["units"] for p in _PROPERTIES)
    occupied = sum(p["occupied"] for p in _PROPERTIES)
    active_deals = [d for d in _DEALS if d["status"] == "Active"]
    total_noi = sum(p["noi"] for p in _PROPERTIES)
    total_value = sum(p["value"] for p in _PROPERTIES)
    pipeline_value = sum(d["value"] for d in active_deals)
    pipeline_comm = sum(d["commission"] for d in active_deals)
    closed_ytd = sum(d["value"] for d in _DEALS if d["status"] == "Closed")

    return {
        "portfolio_value": round(total_value, 2),
        "total_units": total_units,
        "occupied_units": occupied,
        "occupancy": round(occupied / total_units * 100, 1) if total_units else 0,
        "total_noi": total_noi,
        "pipeline_value": pipeline_value,
        "pipeline_commission": pipeline_comm,
        "active_deals": len(active_deals),
        "closed_ytd": closed_ytd,
        "properties_count": len(_PROPERTIES),
    }


def _portfolio_dashboard() -> dict[str, Any]:
    total_units = sum(p["units"] for p in _PROPERTIES)
    occupied = sum(p["occupied"] for p in _PROPERTIES)
    return {
        "properties": _PROPERTIES,
        "occupancy_by_type": {
            ptype: {
                "units": sum(p["units"] for p in _PROPERTIES if p["type"] == ptype),
                "occupied": sum(p["occupied"] for p in _PROPERTIES if p["type"] == ptype),
            }
            for ptype in {p["type"] for p in _PROPERTIES}
        },
        "top_by_noi": sorted(_PROPERTIES, key=lambda p: p["noi"], reverse=True)[:3],
        "overall_occupancy": round(occupied / total_units * 100, 1) if total_units else 0,
    }


def _pipeline_dashboard() -> dict[str, Any]:
    stages_ordered = ["LOI", "Negotiating", "Underwriting", "Due Diligence", "Closing", "Closed", "Lost"]
    by_stage = {}
    for s in stages_ordered:
        deals = [d for d in _DEALS if d["stage"] == s]
        if deals:
            by_stage[s] = {
                "count": len(deals),
                "value": sum(d["value"] for d in deals),
                "commission": sum(d["commission"] for d in deals),
            }
    active = [d for d in _DEALS if d["status"] == "Active"]
    return {
        "by_stage": by_stage,
        "active_deals": active,
        "pipeline_total": sum(d["value"] for d in active),
        "commission_pipeline": sum(d["commission"] for d in active),
        "closing_this_quarter": [d for d in active if d.get("target_close") and d["target_close"] >= "2026-07-01" and d["target_close"] <= "2026-09-30"],
    }


def _market_dashboard() -> dict[str, Any]:
    by_city = {}
    for p in _PROPERTIES:
        city = p["city"]
        if city not in by_city:
            by_city[city] = {"properties": 0, "units": 0, "avg_rent": 0, "avg_cap": 0}
        data = by_city[city]
        data["properties"] += 1
        data["units"] += p["units"]
        data["avg_rent"] = round((data["avg_rent"] * (data["properties"] - 1) + p["rent"]) / data["properties"], 2)
        data["avg_cap"] = round((data["avg_cap"] * (data["properties"] - 1) + p["cap"]) / data["properties"], 2)

    by_type = {}
    for p in _PROPERTIES:
        ptype = p["type"]
        if ptype not in by_type:
            by_type[ptype] = {"count": 0, "units": 0, "avg_cap": 0}
        data = by_type[ptype]
        data["count"] += 1
        data["units"] += p["units"]
        data["avg_cap"] = round((data["avg_cap"] * (data["count"] - 1) + p["cap"]) / data["count"], 2)

    avg_cap = round(sum(p["cap"] for p in _PROPERTIES) / len(_PROPERTIES), 1)
    avg_rent = round(sum(p["rent"] for p in _PROPERTIES) / len(_PROPERTIES), 2)

    return {
        "by_city": by_city,
        "by_type": by_type,
        "overall_avg_cap": avg_cap,
        "overall_avg_rent": avg_rent,
        "total_properties": len(_PROPERTIES),
        "total_units": sum(p["units"] for p in _PROPERTIES),
    }


def _activities_dashboard() -> dict[str, Any]:
    upcoming = [a for a in _ACTIVITIES if a["status"] == "Open"]
    completed = [a for a in _ACTIVITIES if a["status"] == "Completed"]
    this_week = [a for a in upcoming if a.get("due", "") <= "2026-05-25"]
    return {
        "upcoming_count": len(upcoming),
        "completed_count": len(completed),
        "this_week": this_week,
        "upcoming": sorted(upcoming, key=lambda a: a.get("due", ""))[:8],
        "by_type": {
            atype: len([a for a in upcoming if a["type"] == atype])
            for atype in {a["type"] for a in upcoming}
        },
    }


# ─── API ──────────────────────────────────────────────────────────────


class QueryRequest(BaseModel):
    query: str
    user_id: str | None = None


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-dashboard", "status": "ok", "version": "0.1.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "dashboard"}


@app.post("/mcp/query")
def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    q = payload.query.lower()

    if any(w in q for w in ("overview", "home", "dashboard", "summary")):
        data = _compute_overview()
        return {"service": "dashboard", "view": "overview", "data": data}

    if any(w in q for w in ("portfolio", "property", "properties", "asset")):
        return {"service": "dashboard", "view": "portfolio", "data": _portfolio_dashboard()}

    if any(w in q for w in ("pipeline", "deal", "commission", "funnel", "stage")):
        return {"service": "dashboard", "view": "pipeline", "data": _pipeline_dashboard()}

    if any(w in q for w in ("market", "submarket", "city", "type", "cap rate")):
        return {"service": "dashboard", "view": "market", "data": _market_dashboard()}

    if any(w in q for w in ("activity", "activities", "upcoming", "task", "tour", "calendar")):
        return {"service": "dashboard", "view": "activities", "data": _activities_dashboard()}

    # Default: return overview
    return {"service": "dashboard", "view": "overview", "data": _compute_overview()}
