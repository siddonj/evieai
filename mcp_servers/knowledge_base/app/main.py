"""Knowledge Base MCP Server — Multifamily & Brokerage Policies, SOPs, Compliance."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="mcp-knowledge-base", version="0.2.0")

# ═══════════════════════════════════════════════════════════════════════
#  DEMO DATA  —  Multifamily Operations & Brokerage Policies
# ═══════════════════════════════════════════════════════════════════════

_SOPS: list[dict[str, Any]] = [
    {
        "id": "sop-mf-001",
        "type": "SOP",
        "category": "Property Management",
        "title": "Unit Turnover & Make-Ready Process",
        "version": "2.1",
        "effective_date": "2026-01-15",
        "owner": "Operations Team",
        "status": "Active",
        "summary": "Unit turnover must be completed within 5 business days of vacancy. Scope: deep clean, paint touch-ups, appliance inspection, HVAC filter replacement, pest control. Final inspection by property manager before listing. Average turnover cost target: $850/unit for standard units, $1,500 for premium.",
        "key_points": [
            "5 business day turnaround target from move-out to rent-ready",
            "Mandatory: deep clean, paint, appliance check, HVAC filter, pest control",
            "Property manager must sign off on final inspection checklist",
            "Turnover cost cap: $850 standard, $1,500 premium (pre-approval required above)",
            "Photo documentation required for all pre-occupancy condition",
            "Smart lock codes reset and community fob deactivated same day",
        ],
        "related": ["sop-mf-003", "policy-mf-002"],
    },
    {
        "id": "sop-mf-002",
        "type": "SOP",
        "category": "Property Management",
        "title": "Rent Collection & Delinquency Procedures",
        "version": "3.0",
        "effective_date": "2026-02-01",
        "owner": "Revenue Management Team",
        "status": "Active",
        "summary": "Rent due on the 1st of each month. 5-day grace period ends on the 5th. Late fee of $50 or 5% (whichever is greater) applied on the 6th. Pay-or-quit notice served on the 10th. Eviction filing initiated on the 20th if no payment or payment plan. Rent collection target: 97%+ by the 10th.",
        "key_points": [
            "Rent due 1st, grace period through 5th, late fee applied 6th",
            "Late fee: $50 or 5% of monthly rent (whichever is greater)",
            "Pay-or-quit notice (3-day) served on the 10th per TN law",
            "Payment plans available for qualifying hardship cases (max 3-month terms)",
            "Eviction filing via General Sessions Court on the 20th",
            "Online payment portal: 82% of tenants use auto-pay or e-check",
        ],
        "related": ["policy-mf-001", "policy-mf-007"],
    },
    {
        "id": "sop-mf-003",
        "type": "SOP",
        "category": "Property Management",
        "title": "Maintenance Request Handling",
        "version": "2.5",
        "effective_date": "2026-01-01",
        "owner": "Maintenance Department",
        "status": "Active",
        "summary": "Emergency maintenance (no AC, gas leak, water leak, no power, lockout) responded to within 2 hours. Urgent (non-emergency within 24 hours): appliance not working, plumbing issue, pest sighting. Routine: 3-5 business days. All work orders tracked in Yardi. Resident satisfaction survey sent after completion.",
        "key_points": [
            "Emergency: 2-hour response time — HVAC, gas, water, power, security",
            "Urgent: 24-hour response — appliance, plumbing, pest, electrical (non-emergency)",
            "Routine: 3-5 business days — cosmetic, lightbulbs, filter changes",
            "All work orders logged in Yardi with photo documentation",
            "Resident survey sent within 24 hours of maintenance completion",
            "Third-party vendor approval required for work >$500",
        ],
        "related": ["sop-mf-001", "policy-mf-005"],
    },
    {
        "id": "sop-mf-004",
        "type": "SOP",
        "category": "Leasing / Compliance",
        "title": "Fair Housing Compliance — Leasing & Showings",
        "version": "4.0",
        "effective_date": "2026-01-01",
        "owner": "Compliance Officer",
        "status": "Active",
        "summary": "All leasing agents must complete Fair Housing training annually. No steering, discriminatory statements, or differential treatment. All qualification criteria (income, credit, rental history) applied uniformly. Service animals and ESA must be accommodated. Reasonable accommodation requests documented and responded to within 5 days. Marketing materials must not exclude or imply preference.",
        "key_points": [
            "Annual Fair Housing training mandatory for all leasing staff",
            "Income requirements: 3x rent — applied uniformly, bank statements OK",
            "Service animals: no pet fees, no breed/weight restrictions, no deposit",
            "ESAs: valid letter from licensed healthcare provider required",
            "Reasonable accommodation response time: 5 business days",
            "All showing notes and prospect interactions logged in CRM",
            "Marketing materials reviewed by compliance for Fair Housing language",
        ],
        "related": ["sop-mf-008", "policy-mf-001", "policy-mf-003"],
    },
    {
        "id": "sop-mf-005",
        "type": "SOP",
        "category": "Property Management",
        "title": "Seasonal Inspections & Preventive Maintenance",
        "version": "1.8",
        "effective_date": "2025-10-01",
        "owner": "Facilities Manager",
        "status": "Active",
        "summary": "Quarterly inspections of roof, HVAC, plumbing, electrical, parking lot, landscaping, pool, and fire safety systems. Pre-winter: pipe insulation, heater tune-ups, snow removal contracts confirmed. Pre-summer: AC tune-ups, pool opening, landscaping plan. Fire alarm and sprinkler testing per NFPA standards.",
        "key_points": [
            "Quarterly exterior inspection: roof, parking, landscaping, signage",
            "HVAC: spring tune-up for AC, fall tune-up for heat — filter change quarterly",
            "Fire safety: monthly alarm test, annual sprinkler inspection (NFPA 25)",
            "Pool: weekly chemical tests (Memphis Health Dept. standards), annual safety inspection",
            "Pre-winter checklist: pipe insulation, heater startup, snow removal contract",
            "Capital reserve funded at $250/unit/year for planned replacements",
        ],
        "related": ["sop-mf-003", "policy-mf-005"],
    },
    {
        "id": "sop-mf-006",
        "type": "SOP",
        "category": "Brokerage",
        "title": "Listing Agreement & Property Marketing",
        "version": "2.0",
        "effective_date": "2026-03-01",
        "owner": "Brokerage Department",
        "status": "Active",
        "summary": "Exclusive listing agreement signed before any marketing begins. Marketing package includes: professional photography, drone video, offering memorandum, financial model, and CoStar listing. Property tours coordinated within 48 hours of request. Weekly status updates to seller. Offers presented within 24 hours of receipt with broker analysis.",
        "key_points": [
            "Exclusive listing agreement required before marketing spend",
            "Full marketing package: photos, drone, OM, financial model, CoStar",
            "Tours scheduled within 48 hours of qualified buyer request",
            "Weekly written status updates to seller every Monday by 10am",
            "All offers presented to seller within 24 hours with broker recommendation",
            "Confidentiality agreements required before OM distribution",
            "CoStar syndication within 3 business days of signed listing",
        ],
        "related": ["sop-mf-007", "policy-mf-004"],
    },
    {
        "id": "sop-mf-007",
        "type": "SOP",
        "category": "Brokerage",
        "title": "Offer to Closing — Deal Management Process",
        "version": "1.5",
        "effective_date": "2026-02-15",
        "owner": "Transaction Management Team",
        "status": "Active",
        "summary": "Written offers submitted with proof of funds or financing letter. LOI terms: purchase price, cap rate, due diligence timeline, earnest money (3% of offer price standard). Due diligence period 30-45 days for MF assets. Earnest money held in escrow by closing attorney. Commission disbursement at closing via HUD-1. Post-closing: referral fee disbursement within 10 days.",
        "key_points": [
            "Proof of funds or lender pre-approval letter required with offer",
            "Standard earnest money: 3% of purchase price (non-refundable after DD)",
            "Due diligence period: 30 days standard, 45 for assets >$20M",
            "All commission agreements in writing before LOI execution",
            "Closing funds wired — personal checks not accepted at closing table",
            "Referral fees disbursed within 10 calendar days of closing",
            "Post-closing survey sent to both buyer and seller within 5 days",
        ],
        "related": ["sop-mf-006", "policy-mf-006"],
    },
    {
        "id": "sop-mf-008",
        "type": "SOP",
        "category": "Leasing / Compliance",
        "title": "Eviction Process — Tennessee Law Compliance",
        "version": "2.2",
        "effective_date": "2026-03-01",
        "owner": "Legal & Compliance Team",
        "status": "Active",
        "summary": "Evictions follow Tennessee Code Title 66-28-505. Three-step process: (1) 3-day pay-or-quit notice, (2) detainer warrant filed with General Sessions Court, (3) court hearing and writ of possession. Tenant may redeem by paying all rent + fees + court costs up to the hearing date. Legal representation retained for all court appearances. No self-help evictions — illegal under TN law.",
        "key_points": [
            "Step 1: 3-day pay-or-quit notice served in person or posted conspicuously",
            "Step 2: Detainer warrant filed with Shelby County General Sessions Court",
            "Step 3: Court hearing scheduled within 15-30 days of filing",
            "Tenant right of redemption: pay all owed rent + fees + costs before hearing",
            "No self-help evictions — no lockouts, utility shutoffs, or property removal",
            "Legal counsel required at all court appearances — in-house or retained",
            "Average timeline: 45-60 days from first notice to writ of possession",
        ],
        "related": ["sop-mf-002", "policy-mf-001", "policy-mf-003"],
    },
    {
        "id": "sop-mf-009",
        "type": "SOP",
        "category": "Property Management",
        "title": "Pool Operations & Safety",
        "version": "1.5",
        "effective_date": "2025-05-01",
        "owner": "Facilities Manager",
        "status": "Active",
        "summary": "Pool season: Memorial Day through Labor Day. Daily chemical testing and logging. Certified pool operator (CPO) on staff at each property with a pool. Lifeguard required for pools exceeding 5 ft depth. Gate locks self-closing and self-latching. Pool rules posted at entrance. No glass containers within pool enclosure.",
        "key_points": [
            "Pool season: Memorial Day to Labor Day (extended hours for tenant events)",
            "Daily chlorine, pH, alkalinity tests — logged in PoolGuard system",
            "CPO on staff at each property — certification renewed every 3 years",
            "Depth >5ft: lifeguard on duty during all operating hours",
            "Self-closing, self-latching gates inspected weekly",
            "Chemical storage: locked, ventilated, separate from mechanical room",
            "Annual safety inspection by Memphis Health Department before opening",
        ],
        "related": ["sop-mf-005"],
    },
    {
        "id": "sop-mf-010",
        "type": "SOP",
        "category": "Brokerage",
        "title": "Commission Splits & Referral Fee Schedule",
        "version": "2.0",
        "effective_date": "2026-01-01",
        "owner": "Brokerage Operations",
        "status": "Active",
        "summary": "Standard commission: 2.5-3.0% of purchase price for exclusive listings. Co-brokerage splits: 50/50 standard, 60/40 for procuring cause. Internal referrals: 25% to referring agent. External referrals: 25% referral fee (reduced to 20% if no active TN license). Commission paid at closing via HUD-1. Volume bonuses: 5% override at $500K GCI, 10% at $1M GCI.",
        "key_points": [
            "Exclusive listing commission: 2.5-3.0% negotiable per engagement letter",
            "Co-brokerage split: 50/50 standard (60/40 if procuring cause documented)",
            "Internal referral: 25% of gross commission to referring agent",
            "External referral: 25% (20% if unlicensed — finder's fee permissible)",
            "Volume bonus: 5% override at $500K annual GCI, 10% at $1M",
            "Bonuses paid quarterly within 15 days of quarter end",
            "All splits documented in written commission agreement before closing",
        ],
        "related": ["sop-mf-007", "policy-mf-004", "policy-mf-006"],
    },
]

_POLICIES: list[dict[str, Any]] = [
    {
        "id": "policy-mf-001",
        "type": "Policy",
        "category": "Fair Housing & Compliance",
        "title": "Fair Housing Policy — Equal Housing Opportunity",
        "version": "4.2",
        "effective_date": "2026-01-01",
        "owner": "Chief Compliance Officer",
        "status": "Active",
        "summary": "We do business in accordance with the Fair Housing Act (Title VIII of the Civil Rights Act of 1968 as amended). No discrimination based on race, color, religion, sex, handicap, familial status, or national origin. All properties display Equal Housing Opportunity logo. Violations of this policy are grounds for immediate termination.",
        "key_points": [
            "Fair Housing Act protections strictly enforced at all properties",
            "Equal Housing Opportunity poster displayed in all leasing offices",
            "No discriminatory statements in marketing, tours, or lease terms",
            "Familial status: cannot refuse families with children, no adult-only buildings",
            "Disability: reasonable accommodation/modification process published",
            "Violation reporting: confidential ethics line 901-555-HELP",
            "Annual Fair Housing training: 100% completion required for all staff",
        ],
        "related": ["sop-mf-004", "sop-mf-008", "policy-mf-003"],
    },
    {
        "id": "policy-mf-002",
        "type": "Policy",
        "category": "Leasing",
        "title": "Tenant Qualification Standards",
        "version": "3.5",
        "effective_date": "2026-02-01",
        "owner": "Revenue Management",
        "status": "Active",
        "summary": "All applicants screened uniformly: credit score 620+ minimum (580+ with additional deposit), gross income 3x rent, no evictions in past 5 years, no felony convictions related to property damage or violent crime within 7 years. Application fee: $50 non-refundable. Co-signers accepted for students: 4.5x income requirement. Criminal background check performed on all applicants 18+.",
        "key_points": [
            "Credit: 620+ minimum (580+ with 1.5x security deposit)",
            "Income: 3x monthly rent (verified via pay stubs, tax returns, bank statements)",
            "Eviction: no prior evictions filed within past 5 years",
            "Criminal: no violent/ property felony within 7 years (per HUD guidelines)",
            "Co-signer: 4.5x income, must be US resident, joint liability",
            "All occupants 18+ screened — no exceptions",
            "Application fee: $50 non-refundable (TN maximum)",
        ],
        "related": ["policy-mf-001", "sop-mf-004"],
    },
    {
        "id": "policy-mf-003",
        "type": "Policy",
        "category": "Fair Housing & Compliance",
        "title": "Service Animal & Emotional Support Animal Policy",
        "version": "2.5",
        "effective_date": "2025-12-01",
        "owner": "Compliance Officer",
        "status": "Active",
        "summary": "Service animals (trained to perform specific tasks for disability) are not pets — no fees, deposits, or breed/weight restrictions apply. Emotional support animals (ESAs) require valid letter from a licensed healthcare professional, renewed annually. Fraudulent ESA documentation is grounds for lease termination. All accommodation requests processed within 5 business days.",
        "key_points": [
            "Service animals: no pet fees, deposit, or breed/weight restrictions — by law",
            "ESAs: valid letter from licensed professional (MD, DO, NP, PA, LCSW, PhD)",
            "ESA letter must be current (within 12 months), on letterhead, with license #",
            "Online registration certificates are not valid documentation",
            "Breed/weight restrictions do not apply to service animals or ESAs",
            "Request response: 5 business days, interim accommodation if urgent",
            "Fraudulent ESA documentation: lease termination + possible legal action",
        ],
        "related": ["sop-mf-004", "policy-mf-001", "policy-mf-005"],
    },
    {
        "id": "policy-mf-004",
        "type": "Policy",
        "category": "Brokerage",
        "title": "Buyer Representation & Agency Disclosure",
        "version": "3.0",
        "effective_date": "2026-01-01",
        "owner": "Brokerage Managing Director",
        "status": "Active",
        "summary": "Agency disclosure provided before any substantive discussion of property terms. Buyer representation agreement executed before submitting offers. Exclusive buyer agency: 3% standard fee. Dual agency permitted only with written consent from both parties. Confidentiality obligations survive termination of agency relationship. No undisclosed dual agency — violation may result in license suspension.",
        "key_points": [
            "Agency disclosure form signed before discussing pricing or terms",
            "Buyer representation agreement required before offer submission",
            "Exclusive buyer agency: 3% standard, negotiable for portfolio acquisitions",
            "Dual agency: written consent from both buyer and seller required",
            "Confidentiality: seller's minimum price, buyer's max budget — never disclosed",
            "Agency disclosure records retained for 5 years per TN Real Estate Commission",
            "No undisclosed dual agency — immediate termination for violation",
        ],
        "related": ["sop-mf-006", "sop-mf-007", "policy-mf-006"],
    },
    {
        "id": "policy-mf-005",
        "type": "Policy",
        "category": "Property Management",
        "title": "Property Safety & Liability Prevention",
        "version": "3.2",
        "effective_date": "2025-11-01",
        "owner": "Risk Management",
        "status": "Active",
        "summary": "All properties maintain $5M general liability coverage. Slip/trip hazards corrected within 24 hours. Snow/ice removal within 4 hours of accumulation. Lighting inspections weekly (parking lots, hallways, stairwells). Security camera footage retained 30 days. Incident reports filed within 2 hours of any on-site injury. Annual property liability audit by external risk consultant.",
        "key_points": [
            "General liability: $5M per occurrence minimum",
            "Trip hazards: corrected within 24 hours of report",
            "Snow removal: 4-hour response, paths cleared before 8am",
            "Lighting: weekly inspection log for all common areas and parking",
            "Security cameras: 30-day retention, 90-day for incident footage",
            "Incident reports: filed within 2 hours, reviewed by risk manager within 24",
            "Annual safety audit: external consultant, report to ownership",
        ],
        "related": ["sop-mf-003", "sop-mf-005", "sop-mf-009"],
    },
    {
        "id": "policy-mf-006",
        "type": "Policy",
        "category": "Brokerage",
        "title": "Commission Disbursement & Fee Schedule",
        "version": "2.0",
        "effective_date": "2026-01-01",
        "owner": "Finance & Operations",
        "status": "Active",
        "summary": "Commissions disbursed within 5 business days of closing funds clearing. Referral fees paid within 10 days. Commission advance available for active agents (up to 50% of projected fee, interest-free, repaid at closing). Annual audit of all commission disbursements. Disputes resolved via mediation before arbitration. Fee schedule published internally and updated quarterly.",
        "key_points": [
            "Standard disbursement: 5 business days post-closing",
            "Referral fees: 10 business days post-closing",
            "Commission advance: up to 50%, interest-free, repaid at closing",
            "Annual audit of all commission transactions by external CPA",
            "Dispute resolution: mediation (30 days) then binding arbitration",
            "Fee schedule reviewed quarterly by brokerage committee",
            "1099-NEC issued for all non-employee commission payments",
        ],
        "related": ["sop-mf-007", "sop-mf-010", "policy-mf-004"],
    },
    {
        "id": "policy-mf-007",
        "type": "Policy",
        "category": "Property Management",
        "title": "Security Deposits & Move-Out Procedures",
        "version": "2.8",
        "effective_date": "2025-09-01",
        "owner": "Operations Team",
        "status": "Active",
        "summary": "Security deposit = one month's rent (max per TN law: 2 months). Deposits held in interest-bearing escrow account. Itemized deduction list provided within 30 days of move-out with receipts. Normal wear and tear not deducted. Security deposit returned via check within 30 days (TN law). Pre-move-out inspection offered at 30 days notice.",
        "key_points": [
            "Deposit: 1 month's rent standard (max 2 months per TN law)",
            "Escrow account: interest-bearing, reconciled monthly",
            "Deductions: itemized list with receipts within 30 days of move-out",
            "Normal wear and tear (paint fading, carpet wear) is not deducted",
            "Return via check within 30 days — direct deposit available",
            "Pre-move-out inspection offered at 30-day notice mark",
            "Dispute: tenant may request third-party inspection at their cost",
        ],
        "related": ["sop-mf-001", "sop-mf-002"],
    },
    {
        "id": "policy-mf-008",
        "type": "Policy",
        "category": "Fair Housing & Compliance",
        "title": "Tenant Grievance & Complaint Procedure",
        "version": "2.0",
        "effective_date": "2026-04-01",
        "owner": "Compliance Officer",
        "status": "Active",
        "summary": "Tenants may file complaints via portal, phone, or in-person. Complaints acknowledged within 24 hours. Investigation begins within 5 business days. Fair Housing complaints escalated to compliance officer within 24 hours. Retaliation against complainants prohibited. HUD or local fair housing agency referral provided if requested. All complaints logged and tracked to resolution.",
        "key_points": [
            "Complaint channels: resident portal, phone, email, in-person office",
            "24-hour acknowledgment of all complaints",
            "Investigation initiated within 5 business days",
            "Fair Housing complaints: escalation to compliance officer within 24 hours",
            "No retaliation — lease non-renewal for retaliation is grounds for legal action",
            "HUD/Tennessee Human Rights Commission referral upon request",
            "Monthly complaint log review by property management leadership",
        ],
        "related": ["policy-mf-001", "sop-mf-004", "sop-mf-008"],
    },
    {
        "id": "policy-mf-009",
        "type": "Policy",
        "category": "Finance",
        "title": "Capital Expenditure & Reserve Policy",
        "version": "1.5",
        "effective_date": "2025-06-01",
        "owner": "Chief Financial Officer",
        "status": "Active",
        "summary": "Capital reserve funded at $250/unit/year. Expenditures >$10K require ownership approval. Roof replacement: 20-year lifecycle, $500K-$1M depending on building size. HVAC replacement: 15-year lifecycle, $4K-$6K per unit. Parking lot resurfacing: 10-year cycle. Capital plan reviewed annually with ownership. Reserve study updated every 3 years by third-party engineer.",
        "key_points": [
            "Capital reserve contribution: $250/unit/year",
            "Expenditure approval: >$10K requires ownership sign-off",
            "Roof: 20-year lifecycle, budget $500K-$1M at 2026 costs",
            "HVAC: 15-year lifecycle, $4K-$6K per unit (through-wall), $8K-$12K (packaged)",
            "Parking: sealcoat every 3 years ($15K-$30K), resurface every 10 ($50K-$150K)",
            "Annual capital review with ownership each October",
            "Reserve study: third-party engineering report every 3 years",
        ],
        "related": ["sop-mf-005", "policy-mf-005"],
    },
    {
        "id": "policy-mf-010",
        "type": "Policy",
        "category": "Brokerage",
        "title": "Conflict of Interest & Disclosure Policy",
        "version": "2.0",
        "effective_date": "2026-01-01",
        "owner": "General Counsel",
        "status": "Active",
        "summary": "All agents must disclose any personal or financial interest in a property before showing or listing. No undisclosed ownership interest in any entity transacting with the brokerage. Family relationships with buyers/sellers disclosed in writing. Agent cannot represent both sides in a dual-agency transaction without explicit written consent from both parties. Violations reported to TN Real Estate Commission.",
        "key_points": [
            "Personal interest in property: disclose before any client interaction",
            "Ownership interest: no undisclosed interest in any transaction counterparty",
            "Family relationships: written disclosure to brokerage managing director",
            "Self-dealing: prohibited — no agent may purchase their own listing without full disclosure",
            "Dual agency: written consent required before any negotiations",
            "Annual conflict of interest disclosure filing required",
            "Violation: internal investigation + mandatory TREC reporting",
        ],
        "related": ["policy-mf-004", "policy-mf-006"],
    },
]

_ALL_DOCS = _SOPS + _POLICIES


# ═══════════════════════════════════════════════════════════════════════
#  API
# ═══════════════════════════════════════════════════════════════════════

class QueryRequest(BaseModel):
    query: str


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "mcp-knowledge-base", "status": "ok", "version": "0.2.0"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/mcp")
def mcp_info() -> dict[str, str]:
    return {"transport": "streamable-http", "service": "knowledge_base"}


def _score(doc: dict[str, Any], q: str) -> int:
    """Simple keyword relevance score."""
    text = " ".join(
        [
            doc.get("title", ""),
            doc.get("category", ""),
            doc.get("summary", ""),
            " ".join(doc.get("key_points", [])),
        ]
    ).lower()
    words = q.lower().split()
    return sum(3 if w in doc.get("title", "").lower() else 1 for w in words if w in text)


@app.post("/mcp/query")
def mcp_query(payload: QueryRequest) -> dict[str, Any]:
    q = payload.query.lower()

    # Determine document type filter
    type_filter = None
    if any(w in q for w in ("sop", "standard operating", "procedure", "protocol", "process")):
        type_filter = "SOP"
    elif any(w in q for w in ("policy", "rule", "guideline", "handbook")):
        type_filter = "Policy"

    # Category filter
    category_filter = None
    if any(w in q for w in ("fair housing", "discrimination", "equal", "ada", "disability", "service animal", "esa", "eviction")):
        category_filter = "Fair Housing & Compliance"
    elif any(w in q for w in ("lease", "rent", "qualification", "applicant", "deposit", "income")):
        category_filter = "Leasing"
    elif any(w in q for w in ("maintenance", "repair", "turnover", "inspection", "pool", "safety")):
        category_filter = "Property Management"
    elif any(w in q for w in ("commission", "listing", "referral", "buyer rep", "agency", "disclosure")):
        category_filter = "Brokerage"
    elif any(w in q for w in ("capital", "reserve", "budget", "expenditure", "finance")):
        category_filter = "Finance"

    candidates = [d for d in _ALL_DOCS if (type_filter is None or d["type"] == type_filter)]
    if category_filter:
        candidates = [d for d in candidates if d["category"] == category_filter]

    # Score and rank
    scored = [(d, _score(d, q)) for d in candidates]
    scored.sort(key=lambda x: x[1], reverse=True)

    # Return top 5 with positive scores, or top 3 if nothing matched
    results = [d for d, s in scored if s > 0][:5]
    if not results:
        results = [d for d, s in scored[:3]]

    return {
        "service": "knowledge_base",
        "query": payload.query,
        "summary": f"Found {len(results)} relevant document(s)",
        "documents": results,
    }


@app.get("/admin/data")
def admin_get_data() -> dict[str, Any]:
    return {
        "service": "knowledge_base",
        "total_documents": len(_ALL_DOCS),
        "sops": len([d for d in _ALL_DOCS if d["type"] == "SOP"]),
        "policies": len([d for d in _ALL_DOCS if d["type"] == "Policy"]),
        "documents": _ALL_DOCS,
    }


@app.post("/admin/data")
def admin_post_data(payload: dict[str, Any]) -> dict[str, Any]:
    doc = payload.get("document")
    if not doc or not isinstance(doc, dict):
        return {"error": "Missing 'document' field in payload"}
    if "id" not in doc or "title" not in doc:
        return {"error": "Document must have 'id' and 'title' fields"}
    existing = [d for d in _ALL_DOCS if d.get("id") == doc["id"]]
    if existing:
        _ALL_DOCS[_ALL_DOCS.index(existing[0])] = doc
        return {"service": "knowledge_base", "action": "updated", "id": doc["id"], "total": len(_ALL_DOCS)}
    _ALL_DOCS.append(doc)
    return {"service": "knowledge_base", "action": "added", "id": doc["id"], "total": len(_ALL_DOCS)}
