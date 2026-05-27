# AI Agentic Q&A — Demo Script

> **Last updated:** 2026-05-19 · **Version:** 7.0 · **Total runtime:** ~14 min full / ~5 min quick
>
> **Goal:** Show how a single natural-language interface routes to 8 different multifamily and brokerage data sources — properties, deals, contacts, market analytics, policies, documents, and files — and synthesizes rich, actionable answers tailored to who is asking.
>
> **URLs**
> - Chat UI: <https://demo.resiq.co>
> - API: <https://api.resiq.co>
>
> **Note on data:** All property data, deals, contacts, commissions, and policies shown in this demo are **synthetic sample data** based on a fictional Memphis multifamily portfolio. No real properties or financial information is exposed.

---

## Table of Contents

1. [Pre-Demo Checklist](#1-pre-demo-checklist)
2. [Demo Paths — Quick vs. Full](#2-demo-paths--quick-vs-full)
3. [Opening Narrative](#3-opening-narrative-30-seconds)
4. [Login & User Context](#4-login--user-context-30-seconds)
5. [Scenario A — Portfolio Performance Check](#5-scenario-a--portfolio-performance-check-1-minute)
6. [Scenario B — Deal Pipeline & Commission Status](#6-scenario-b--deal-pipeline--commission-status-1-minute)
7. [Scenario C — Property Search by Status](#7-scenario-c--property-search-by-status-45-seconds)
8. [Scenario D — Market Analytics & Trends](#8-scenario-d--market-analytics--trends-1-minute)
9. [Scenario E — Full Portfolio Report Generation **★ Killer**](#9-scenario-e--full-portfolio-report-generation--killer-2-minutes)
10. [Scenario F — Fair Housing Policy Lookup](#10-scenario-f--fair-housing-policy-lookup-1-minute)
11. [Scenario G — Multi-Tool: Property Data + Market Comps](#11-scenario-g--multi-tool-property-data--market-comps-1-minute)
12. [Scenario H — Multi-Round Deal Negotiation Prep](#12-scenario-h--multi-round-deal-negotiation-prep-1-minute)
13. [Scenario I — Key Contacts & Relationship Map **★ Differentiated**](#13-scenario-i--key-contacts--relationship-map--differentiated-1-minute)
14. [Scenario J — Broker Price Opinion Generation](#14-scenario-j--broker-price-opinion-generation-1-minute)
15. [Scenario K — Analytics & KPIs](#15-scenario-k--analytics--kpis-1-minute)
16. [Architecture Deep Dive (Optional)](#16-architecture-deep-dive-optional-2-minutes)
17. [Quick Reference Tables](#17-quick-reference-tables)
18. [Troubleshooting During the Demo](#18-troubleshooting-during-the-demo)
19. [Future Enhancements](#19-future-enhancements)
20. [Closing Narrative & Call to Action](#20-closing-narrative--call-to-action-30-seconds)

---

## 1. Pre-Demo Checklist

Run all of these **15 minutes before** the demo. Cold starts on Container Apps and SQL Serverless can add 10–20 s to the first call.

| # | Action | Where |
|---|--------|-------|
| 1 | Open the UI in a clean browser profile | <https://demo.resiq.co> |
| 2 | **Log in** — use the demo credentials from Key Vault `kv-aiagent2-dev/secret/demo-login` (see footnote) | UI login screen |
| 3 | Open DevTools (F12) → **Network** tab, filter by `chat` | Browser |
| 4 | Verify orchestrator health | `Invoke-RestMethod https://api.resiq.co/health` |
| 5 | Verify all 8 MCP backends are ready | `Invoke-RestMethod https://api.resiq.co/ready` (every entry must show `reachable: true`) |
| 6 | **Smoke-test demo data** by sending one prompt | Type `Show me Q2 revenue` — expect `$12.4M (+18% YoY)`. If you see a generic "I cannot access…" reply, demo data is not loaded. |
| 7 | Open this script on a second screen | Your laptop |
| 8 | Have the architecture diagram ready ([§ 16](#16-architecture-deep-dive-optional-2-minutes)) | This file or `ResiQ_AI_Agentic_Q&A_Architecture.pptx` |

> **Credentials footnote.** The default seeded login is `admin` / `admin` for local Docker Compose only. For the public `demo.resiq.co` URL, **rotate the seeded admin password** before each presentation and read the live value from Key Vault. Never read `admin / admin` aloud during a customer demo.

---

## 2. Demo Paths — Quick vs. Full

Pick a path before you start. Both paths end with the same closing narrative.

### Quick path — 5 minutes (use for booth / hallway / executive walk-up)

1. [§ 4 Login](#4-login--user-context-30-seconds) — 30 s
2. [§ 5 Scenario A](#5-scenario-a--financial-email-intelligence-1-minute) — Financial emails — 1 min
3. [§ 9 Scenario E](#9-scenario-e--board-meeting-preparation--killer-2-minutes) — Board meeting (killer multi-tool) — 2 min
4. [§ 13 Scenario I](#13-scenario-i--personalized-context--memory--differentiated-1-minute) — Personalization (CFO vs. Sales Director) — 1 min
5. [§ 20 Closing](#20-closing-narrative--call-to-action-30-seconds) — 30 s

### Full path — 14 minutes (use for technical deep dive / pilot pitch)

Run [§ 3](#3-opening-narrative-30-seconds) through [§ 15](#15-scenario-k--analytics--kpis-1-minute) in order, then [§ 16 Architecture](#16-architecture-deep-dive-optional-2-minutes) (optional, +2 min for technical audience), then [§ 20 Closing](#20-closing-narrative--call-to-action-30-seconds).

> **Trim aggressively if you fall behind.** The killer scenarios are **A**, **E**, **I**. Everything else is optional.

---

## 3. Opening Narrative (30 seconds)

> *"Most enterprise apps force you to hunt through Outlook, OneDrive, file shares, policies, and databases separately. What if you could just **ask** a single interface — in plain English — and it figures out which system to query, calls the right API, and gives you a synthesized answer? That's what this agentic Q&A app does. Let's see it in action."*

### The contrast — old way vs. new way

| | Old way | New way |
|---|---------|---------|
| **Apps to open** | Outlook + OneDrive + SharePoint + CRM + Policy SharePoint | One chat window |
| **Time to a board briefing** | 20 minutes of context-switching | One sentence, ~10 seconds |
| **Personalization** | Same dashboard for everyone | Same prompt, different answers per role |

---

## 4. Login & User Context (30 seconds)

### What to do
1. Open <https://demo.resiq.co> — the login page appears.
2. Enter the rotated demo credentials and sign in.
3. Notice the **status bar at the bottom of the chat** showing `User: <username>`.

### Admin-only Settings tab
- Click **⚙ Settings** in the top-right corner (only visible to admin accounts).
- Add a new user: `demo-user` / `demo123` with role **User** — you'll need this account in [Scenario I](#13-scenario-i--personalized-context--memory--differentiated-1-minute).
- Show the user table with role badges, then click back to chat.

### What to point at
- **Status bar** (bottom of chat shell) — `User: <name>` is sent on every request.
- **Settings gear** (top-right) — only renders for admin role.
- **Suggested-prompt chips** below the welcome message — eight one-click starters that map to Scenarios A, D, F, J, K, and personalization. Use these when typing is awkward (booth demos, projector lag).

### Talking points
- *"User identity threads through every request — the UI sends `user_id` to the orchestrator, which forwards it to all 8 MCP servers."*
- *"This is the foundation for personalized agentic experiences — the same query returns different results based on who is asking. A CFO sees financial rollups; an engineer sees technical SOPs. We'll prove this in Scenario I."*
- *"Admin users manage accounts from the Settings tab — no backend console required."*

### If it fails
- **Login button does nothing →** check DevTools console. If `auth/login` returns 500, the orchestrator might be cold-starting. Wait 10 s and retry.
- **Settings tab missing →** you logged in as a non-admin. Log out, sign in with the admin account.

---

## 5. Scenario A — Financial Email Intelligence (1 minute)

### Prompt
```
Find unread emails about revenue or budget and summarize the action items.
```

### What to point at
- **Status bar** transitions through `🔍 Querying: Mail...` → `Generating response...`.
- **Live tool badge** `📧 Mail → Outlook` appears next to the assistant bubble while the call is in flight.
- **Token-by-token streaming** — the reply types out word-by-word with a `▊` blinking cursor, just like ChatGPT.
- **DevTools → Network** — point to the single `POST /chat` request returning `text/event-stream` (SSE) with `tool_call`, `tool_result`, and `delta` events.
- **EmailCards** rendered below the streamed text, one card per email with subject, sender, date, and a key-points snippet.

### Expected response
The agent returns 5 unread emails with financial data:
- **Q2-2026 Revenue Report** — $12.4M (+18% YoY), enterprise segment +32%, APAC +45%
- **Board Presentation** — $12.4M revenue, 22% operating margin, $1.8M net income, ARR $38.2M (+24%)
- **Cash Flow Alert** — Runway extended to 14 months, April collections $4.1M vs. $3.2M target
- **Investor Update** — ARR $38.2M, NRR 118%, churn 3.2%, Series B term sheets in hand
- **Customer Churn Alert** — 2 at-risk accounts ($85K and $120K ARR), competitor pricing 15% below

### Talking points
- *"Watch the status bar — it says 'Querying: Mail' because the LLM decided it needs the mail tool."*
- *"The orchestrator chose `query_mail` automatically; we never named a tool in the prompt."*
- *"The LLM synthesized raw email JSON into a readable financial briefing with action items highlighted — and it streamed token-by-token while it thought."*

### If it fails
- **`query_mail` returns 403 →** Graph admin consent isn't granted (normal on personal M365). The MCP server falls back to demo data automatically — the answer should still arrive. If it doesn't, **pivot to [Scenario B](#6-scenario-b--onedrive-document-discovery-1-minute)** (OneDrive uses the same Graph fallback).
- **Empty list →** demo data not seeded. Re-run the smoke test from [§ 1](#1-pre-demo-checklist).

---

## 6. Scenario B — OneDrive Document Discovery (1 minute)

### Prompt
```
What revenue reports are in OneDrive?
```

### What to point at
- **Live tool badge** `☁ OneDrive → Documents`.
- **FileCards** rendered below the answer, with file-type icons (📊 xlsx, 📑 pptx), size, and last-modified date.

### Expected response
The agent finds 2 revenue-related files:
- **Q2-2026-Revenue-Report.xlsx** — $12.4M revenue breakdown by region and product line
- **Board-Deck-Q2-Review.pptx** — Executive presentation with KPIs, revenue charts, strategic initiatives

### Variation — multi-tool (highlight this!)
```
Find the Q2 revenue report in OneDrive and also check my email for any threads about it.
```
- Watch for **two badges** appearing in sequence: `☁ OneDrive` then `📧 Mail`.
- The LLM synthesizes both results into one coherent answer: files found + email context about those files.

### Talking points
- *"Same agent, different tool — `query_onedrive` instead of `query_mail`. The LLM picks the right one from the prompt."*
- *"In the variation, it chains two tools and weaves the results together — that's what makes this 'agentic' rather than a chatbot."*

### If it fails
- **OneDrive 403 →** Graph admin consent missing. MCP returns demo data; you'll still see the two files.
- **Pivot:** if both Mail and OneDrive fail, jump to **[Scenario C](#7-scenario-c--file-share-financial-search-45-seconds)** — Files MCP runs on Azure Files and doesn't depend on Graph.

---

## 7. Scenario C — File Share Financial Search (45 seconds)

### Prompt
```
List all Excel files in the shared drive related to finance or revenue.
```

### What to point at
- **Live tool badge** `📁 Files → File Share`.
- **FileCards** with consistent revenue figures matching Mail and OneDrive (same Q2 $12.4M).

### Expected response
7 financial files returned:
- Q2-2026-Revenue-Report.xlsx
- FY2026-Budget-Master.xlsx
- Q1-Profit-and-Loss-Statement.pdf
- Cash-Flow-Projection-May-2026.xlsx
- Board-Deck-Q2-Review.pptx
- Investor-Update-May-2026.docx
- Tax-Preparation-2025-Final.xlsx

### Talking points
- *"This routes to the File Share MCP server, which connects to Azure Files."*
- *"The MCP server abstracts away storage API complexity — the orchestrator just sends a JSON query and gets a JSON response."*
- *"The data is consistent across Mail, OneDrive, and Files — all showing the same Q2 $12.4M revenue figure. That's intentional: real demos look broken when numbers don't match."*

### If it fails
- **Empty result →** Azure Files share isn't mounted into the Container App. Check `files_mcp` revision in Azure Portal.

---

## 8. Scenario D — Sales Pipeline Intelligence (1 minute)

### Prompt
```
Show me the sales pipeline and any deals closed recently.
```

### What to point at
- **Live tool badge** `🗃️ SQL → CRM Database`.
- **SqlDataCard** with stage chips (`Discovery`, `Qualified`, `Proposal Sent`, `Negotiation`, `Closed Won`, `Closed Lost`) and a "By Stage" mini-bar chart.
- **Per-contact rows** with deal value, owner, region, and notes.

### Expected response
Pulled from `query_sql` (12-contact CRM sample):
- **Active pipeline:** $866K across 9 deals (Discovery, Qualified, Proposal Sent, Negotiation)
- **Closed Won (Q2):** $390K across 2 deals
  - Fabrikam Inc — $215K (CTO, West Coast)
  - Litware Inc — $175K (CFO, Northeast)
- **Largest active deal:** Blue Yonder Airlines — $390K Negotiation (legal review)
- **Churn risk:** Adventure Works ($32K Discovery) flagged — competitor pricing 15% below
- **Average deal size:** $111K

> **Why this is `$866K` and not `$8.7M`:** the SQL MCP returns the 12-contact CRM sample (~$866K active). The Analytics MCP in [Scenario K](#15-scenario-k--analytics--kpis-1-minute) reports the **aggregate book** ($8.7M / 42 deals) which includes SMB and inactive accounts not in the CRM sample. Both numbers are correct for their data source. (See [GAPS.md](GAPS.md) — *Demo data reconciliation* for the long-term fix.)

### Talking points
- *"The agent translated 'pipeline' to a structured CRM query without writing any SQL."*
- *"Notice how it combines quantitative data (deal values, stages) with qualitative context (competitor pricing risk in the notes)."*

### If it fails
- **SQL Serverless cold start →** first query takes ~10 s. Don't panic; the spinner is real.
- **`query_sql` returns empty →** auto-pause kicked in. Repeat the prompt; second call is fast.

---

## 9. Scenario E — Board Meeting Preparation **★ Killer** (2 minutes)

This is the centerpiece. If you only run one scenario beyond Login, run this one.

### Prompt
```
I have a board meeting tomorrow. Pull up recent revenue emails, find the Q2 deck in OneDrive, show me the sales pipeline, and check security SOPs in the knowledge base.
```

### What to point at
- **Four live tool badges appear at once** — `📧 Mail`, `☁ OneDrive`, `🗃️ SQL`, `📚 Knowledge Base`. Pause on this; it's the visual that sells the whole demo.
- **Status bar** lists multiple sources: `🔍 Querying: Mail, OneDrive, SQL, Knowledge Base...`
- **Streaming reply** weaves all four results into one synthesized briefing — no raw JSON, no "here are the 4 sections" boilerplate.
- **DevTools → Network** — only one `POST /chat`. The orchestrator fans out to four MCPs internally.

### Expected response
A synthesized board briefing from **4 parallel tool calls**:
1. **Revenue Emails** — Q2 revenue $12.4M (+18% YoY), gross margin 74%, operating margin 22%, ARR $38.2M
2. **Key Files** — `Board-Deck-Q2-Review.pptx` (2.1 MB, May 2), `Q2-2026-Revenue-Report.xlsx` (486 KB)
3. **Sales Pipeline** — $866K active across 9 deals, $390K closed won (2 deals), average deal size $111K
4. **Security SOPs** — Password & Access Control, Data Classification, Incident Response & Breach Notification
5. **Action Items** (synthesized) — Review board deck by 5pm, approve retention discount for at-risk accounts, verify security compliance

### Verified multi-tool execution (live test, 2026-05-06)

The orchestrator executed **4 concurrent tool calls** in a single chat round:

| Tool | Result |
|------|--------|
| `query_mail` | 13 emails (revenue, board deck, cash flow, churn alerts, hiring plan) |
| `query_onedrive` | 21 files (revenue reports, board decks, sales pipeline, project docs) |
| `query_sql` | 12 contacts, pipeline metrics, regional breakdown |
| `query_knowledge_base` | 5 security SOPs with full metadata |

The LLM synthesized all results into a single coherent briefing, even handling Graph API failures gracefully (demo fallback for Mail/OneDrive when admin consent is unavailable).

### Talking points
- *"This is the killer demo. The user asked **one** question that requires **four** backends."*
- *"The LLM broke it into parallel tool calls — Mail, OneDrive, SQL, Knowledge Base — and the orchestrator runs them concurrently."*
- *"Then the LLM weaves the results into a single board-ready briefing. That's what 'agentic' means: the AI is acting as your analyst, not a chatbot."*
- *"This whole flow is roughly 6–8 seconds end-to-end on a warm system."*

### If it fails
- **Only 1–2 badges appear →** the LLM didn't fan out. Re-prompt with more explicit verbs: *"Pull from email, OneDrive, the CRM, and the policy library — all four."*
- **One backend errors out →** the others still synthesize. Acknowledge it ("Notice it gracefully reported the missing source and gave us the rest") and move on.

---

## 10. Scenario F — Knowledge Base & Policy Engine (1 minute)

### Prompt
```
Show me SOPs about security and compliance.
```

### What to point at
- **Live tool badge** `📚 Knowledge Base → Policies`.
- **KnowledgeBaseCards** with `Status: Active`, owner role, effective date, and bullet-point key requirements.

### Expected response
3 matching SOPs:
1. **SOP-007: Security Incident Response** — Severity matrix (P1–P4), 24h SLAs, escalation tree, forensics chain-of-custody
2. **SOP-005: Vendor Security & Due Diligence** — NDA + background check requirements, annual security audit, data classification matrix
3. **SOP-001: Information Security Policy** — Password complexity, MFA mandatory, quarterly access reviews, phishing simulation

### Variation — HR policy
```
What is our parental leave policy?
```
Expected:
- **POL-003: Parental Leave** — 16 weeks fully paid, FMLA-protected, phased return, benefits continuation

### Talking points
- *"This routes to the Knowledge Base MCP server — a dedicated SOP and policy engine, separate from raw file storage."*
- *"Each card shows status, owner, effective date, and key bullet points — no raw JSON, just actionable policy summaries."*
- *"Notice the relevance scoring — the most relevant SOPs rank highest, even when the prompt is vague."*

### If it fails
- **Empty result →** `kb_mcp` Container App scaled to 0 or crashed. Restart revision in Azure Portal; cold start ~5 s.

---

## 11. Scenario G — Multi-Tool: KB + Files (1 minute)

### Prompt
```
Show me SOPs about security and also check the file share for related compliance documents.
```

### What to point at
- **Two live tool badges** — `📚 Knowledge Base` and `📁 Files`.
- The synthesis blends curated policies (KB) with raw file artifacts (audit reports, policy PDFs in the file share).

### Expected response
- **Knowledge Base:** SOP-007 (Incident Response), SOP-005 (Vendor Security), SOP-001 (InfoSec Policy)
- **File Share:** Audit-Report-2025.pdf, Security-Policy-v3.2.docx
- **Synthesis:** *"Here are your security SOPs from the knowledge base, plus related compliance documents from the file share."*

### Talking points
- *"Now five backends are reachable in a single round (Mail, OneDrive, Files, SQL, KB) — the agentic layer abstracts every repository behind one query."*
- *"Knowledge Base = curated, structured policy. File share = raw artifacts. The agent gives you both, side by side."*

### If it fails
- **Only one badge →** the LLM elected not to fan out. Re-prompt with explicit *"and also..."* phrasing.

---

## 12. Scenario H — Multi-Round Conversation (1 minute)

Show that the agent maintains conversation context across turns.

### Turn 1 — set the topic
```
How did we perform in Q2?
```

### Turn 2 — anaphora ("that")
```
And how does that compare to our pipeline for Q3?
```

### Turn 3 — drill-down
```
Why is Adventure Works at risk?
```

### Turn 4 — counterfactual
```
If we offered Adventure Works a 15% retention discount, what's the margin impact?
```

### What to point at
- The `history[]` array in DevTools `POST /chat` payload grows with each turn.
- The LLM never re-asks "which Q2?" or "which company?" — it carries the topic.
- Tool badges may differ per turn (`query_mail` + `query_sql` for Turn 1; `query_sql` + `query_analytics` for Turn 2; pure `query_sql` for Turn 3).

### Talking points
- *"The LLM retains full conversation context. 'That' refers to Q2 performance from Turn 1."*
- *"Turn 3 is a drill-down — no new tool needed, just a focused re-query of the same SQL data."*
- *"Turn 4 is a counterfactual — a CFO question. Watch how the LLM combines deal-value data with margin assumptions to give a real answer, not a punt."*

### If it fails
- **LLM forgets context →** the UI may have lost the message history. Reload the page; localStorage will replay the last 50 messages.

---

## 13. Scenario I — Personalized Context & Memory **★ Differentiated** (1 minute)

This is the demo a CFO will remember. The **same prompt** gives **different answers** based on who is logged in.

### Setup — log in as the admin user (Alex Chen, CFO)

If you're already logged in as admin, skip to "First prompt" below.

### First prompt (logged in as admin / CFO)
```
What should I focus on for my board meeting tomorrow?
```

### What to point at
- **Status bar** at the bottom: `User: admin` (Alex Chen, CFO).
- **Live tool badges** — `🧠 Memory → User Context` fires *first*, then `🗃️ SQL`, `📁 Files`, `📧 Mail`.
- The synthesized answer leads with **financial metrics** ($866K pipeline, $390K closed, gross margin 74%) and references **Alex's saved bookmarks** (`Board-Deck-Q2-Review.pptx`, `Q2-2026-Revenue-Report.xlsx`).

### Expected response
The orchestrator **auto-fetches Alex Chen's profile from the Memory MCP** before calling any other tools:
- **Profile:** Alex Chen, Chief Financial Officer, Finance & Executive Leadership
- **Focus areas:** revenue, cash_flow, margin_analysis, board_metrics, investor_kpis
- **Communication style:** concise_bullet_points
- **Recent topics:** Q2-2026 earnings prep, Series B term sheet, Board meeting May 15, Northwind deal

Then the LLM proactively calls **4 tools** tailored to the CFO's context:
1. `query_memory` — bookmarks: `Board-Deck-Q2-Review.pptx`, `Q2-2026-Revenue-Report.xlsx`
2. `query_sql` — pipeline metrics, closed won deals, regional breakdown
3. `query_files` — board meeting documents
4. `query_mail` — board-related communications

The response is **personalized for a CFO**:
- Financial metrics prioritized ($866K pipeline, $390K closed, margins)
- Board-ready format with concise bullet points (matches `communication_style`)
- References specific bookmarks the user has saved

### The contrast — switch users live

1. Click **🚪 Logout** in the status bar.
2. Sign in as `demo-user` / `demo123` (Jordan Smith, Sales Director — created in [§ 4](#4-login--user-context-30-seconds)).
3. Confirm the status bar reads `User: demo-user`.
4. Run the **same kind of prompt**:
   ```
   What should I focus on this week?
   ```

### Expected response (as Jordan, Sales Director)
- Pipeline-focused — deal velocity, win rates, territory performance
- References Jordan's `data_focus`: `["sales_pipeline", "deal_velocity", "win_rates"]`
- Different file bookmarks, different recent topics

### Talking points
- *"This is the differentiated demo. The **same** interface gives **completely different** answers based on who is logged in."*
- *"The orchestrator auto-fetches memory context **before** the LLM starts thinking — the system prompt already knows you're a CFO focused on board metrics."*
- *"The LLM then chooses tools based on your role — a CFO gets SQL pipeline + financial files; a Sales Director gets deals + territory maps."*
- *"This is true agentic personalization — not a chatbot with your name on it, but an AI that knows your job, your priorities, and your recent work."*

### If it fails
- **Same answer for both users →** `user_id` not threaded through. Check DevTools `POST /chat` payload: `user_id` field must be present.
- **Memory MCP unreachable →** orchestrator falls back to a generic system prompt. Personalization disappears. Restart `memory_mcp` revision in Azure Portal.

---

## 14. Scenario J — Document Generation (1 minute)

### Prompt
```
Generate a board briefing for my meeting tomorrow.
```

### What to point at
- **Live tool badge** `📄 Docs → Report Generation`.
- **DocumentCard** with a 5-section table of contents and **metric cards** (value, trend, target) embedded in each section.

### Expected response
A pre-structured 5-page board briefing:
1. **CEO Opening Remarks** — Welcome, strongest quarter to date
2. **Financial Review** — $12.4M revenue, 74% gross margin, $38.2M ARR, 118% NRR
3. **Sales & Pipeline** — $8.7M pipeline, Northwind $450K closed, Blue Yonder $390K in negotiation
4. **Series B Update** — 3 term sheets, $180–220M valuation, target close June 30
5. **Risk Factors** — 2 at-risk accounts, security clean quarter, talent market competitive

Each section includes **key metric cards** with values and trends.

#### Action Items section
- Board vote: select Series B lead investor term sheet
- Approve retention discount authority for CRO
- Review FY2027 budget framework
- Authorize APAC expansion budget ($2.1M)

### Talking points
- *"The Document Generation MCP doesn't just return text — it returns **structured documents** with sections, metrics, and action items."*
- *"The LLM can generate an executive summary, sales report, security assessment, or board briefing — all from the same chat interface."*
- *"This is the future of enterprise content creation: AI-generated, data-backed, structured documents on demand."*

### If it fails
- **`doc_mcp` returns 500 →** template renderer crashed. Restart revision; the MCP loads templates at startup.

---

## 15. Scenario K — Analytics & KPIs (1 minute)

### Prompt
```
Show me the sales analytics and KPIs for this quarter.
```

### What to point at
- **Live tool badge** `📊 Analytics → KPIs & Trends`.
- **AnalyticsCard** with KPI tiles (value · change · target · ✅/❌ status) and a small monthly **trend bar chart**.

### Expected response — 6 KPI cards

| KPI | Value | Change | Target | Status |
|-----|-------|--------|--------|--------|
| Pipeline Value | $8.7M | +12% QoQ | $8M | ✅ Exceeded |
| Active Deals | 42 | +8 QoQ | 35 | ✅ Exceeded |
| Win Rate | 34% | +4pp QoQ | 30% | ✅ Exceeded |
| Avg Deal Size | $111K | +15% YoY | $100K | ✅ Exceeded |
| Sales Cycle | 87 days | −5 days | 90 | ✅ Below target |
| Closed Won (Q2) | $390K | +22% QoQ | $350K | ✅ Exceeded |

**Trends**
- Pipeline: Jan $6.8M → May $8.7M (steady upward)
- Win Rate: Q1-2025 28% → Q2-2026 34% (steady improvement)

**Key insights**
- Pipeline velocity increasing 12% QoQ
- Enterprise deals (>$100K) now 45% of pipeline value
- Sales cycle shortened to 87 days
- Northeast territory outperforming at $826K
- Two at-risk accounts need retention action

### Variation — multi-tool: Analytics + Document
```
Generate a sales report with analytics for Q2.
```
- Watch for `query_analytics` then `query_document_generation`.
- The LLM synthesizes both into a comprehensive Q2 sales report with embedded KPIs.

### Talking points
- *"The Analytics MCP returns pre-computed KPIs, trends, and insights — not raw rows, but actionable intelligence."*
- *"Every KPI card shows value, change, target, and target status — green for exceeded, red for missed."*
- *"The LLM synthesizes this into a narrative — 'Pipeline is up 12%, win rate improved 4 points, but two at-risk accounts need attention.'"*

### If it fails
- **Empty card or 500 →** `analytics_mcp` Container App crashed. Restart revision.

---

## 16. Architecture Deep Dive (Optional — 2 minutes)

Show this section only if the audience is technical.

```
User (Browser)
    │
    ▼
demo.resiq.co  ──►  Static Web App (React + Vite)
    │                    │
    │                    └── Login + Settings (admin user management)
    │  POST /chat (SSE)  + user_id
    ▼
api.resiq.co  ──►  FastAPI + Azure OpenAI (GPT-4o)
    │                      │
    │                      └── Auto-fetch memory context → inject into system prompt
    │                      └── Tool-calling loop (max 5 rounds, parallel where possible)
    │                      └── user_id forwarded to all MCP calls
    │
    ├──►  SQL MCP (Data API Builder)        ──►  Azure SQL
    ├──►  File Share MCP                    ──►  Azure Files
    ├──►  Mail MCP                          ──►  Microsoft Graph API
    ├──►  OneDrive MCP                      ──►  Microsoft Graph API
    ├──►  Knowledge Base MCP                ──►  In-memory SOP + Policy Engine
    ├──►  Memory / Personal Context MCP     ──►  Per-user profile, preferences, bookmarks
    ├──►  Document Generation MCP           ──►  Executive summaries, board briefings, reports
    └──►  Analytics MCP                     ──►  KPIs, trends, insights, dashboards
         │                                       (with demo fallback for personal M365)
         └──► Demo mode: rich financial/business sample data
```

### Key technical talking points
1. **MCP (Model Context Protocol)** — `fastmcp` servers expose HTTP endpoints with JSON schemas. The orchestrator discovers tools at startup.
2. **Internal ingress only** — All 8 MCP servers (SQL, Files, Mail, OneDrive, Knowledge Base, Memory, Document Generation, Analytics) have `external_enabled = false`. Only the orchestrator is public.
3. **Custom domains** — UI on `demo.resiq.co`, orchestrator on `api.resiq.co`. CORS configured for both. Corporate DNS blocks on `.azurecontainerapps.io` are bypassed.
4. **Secrets via Key Vault** — no hardcoded credentials. Container Apps use managed identities to read secrets.
5. **Container Apps autoscale** — 0 → 3 replicas. Orchestrator and all MCP servers have min 1 replica during demos for instant response.
6. **Demo mode fallback** — When Graph API fails (e.g., personal M365 without admin consent), MCP servers gracefully return rich demo data so the tool-calling loop still works.
7. **User identity + Memory MCP** — Every chat request includes `user_id`. The orchestrator auto-fetches profile, preferences, recent topics, and bookmarks from the Memory MCP and injects them into the LLM's system prompt.
8. **Streaming** — `POST /chat` returns Server-Sent Events. The UI renders `tool_call`, `tool_result`, and `delta` events in real time, which is why the response types out word-by-word and tool badges appear mid-stream.
9. **Resilience** — Orchestrator wraps every MCP call in a circuit breaker (3 failures → 30 s cooldown). OpenAI calls retry with exponential backoff. Rate limited at 20 req/min per user.
10. **Caching** — Repeated identical queries return from Redis cache (60 s TTL).

---

## 17. Quick Reference Tables

### All available tools & demo data

| Tool | Backend | Demo Data Highlights |
|------|---------|----------------------|
| `query_mail` | Microsoft Graph API (Outlook) | 13 emails: Q2 revenue $12.4M, board deck, $450K Northwind deal, cash flow, churn alerts, hiring plan |
| `query_onedrive` | Microsoft Graph API (OneDrive) | 21 files: revenue reports, board decks, sales pipeline, project docs, architecture diagrams |
| `query_files` | Azure Files (file share) | 21 files: same rich dataset mirrored in shared storage |
| `query_sql` | Azure SQL via Data API Builder | 12-contact CRM sample: $866K active pipeline / 9 deals / $390K closed won (2 deals) / avg $111K |
| `query_knowledge_base` | Knowledge Base MCP (SOP + Policy Engine) | 8 SOPs + 10 Policies covering Security, Compliance, HR, IT, Finance |
| `query_memory` | Memory / Personal Context MCP | 3 user profiles: Alex Chen (CFO), Jordan Smith (Sales Director), Taylor Park (Engineering Lead) — preferences, bookmarks, recent topics, focus areas |
| `query_document_generation` | Document Generation MCP | 4 templates: Q2 Executive Summary, Board Briefing May 15, Sales Performance Report, Security Posture Assessment |
| `query_analytics` | Analytics MCP | 4 categories: Financial (8 KPIs), Sales (6 KPIs), Security (6 KPIs), Operational (6 KPIs) — each with trends and insights |

### Key financial metrics in demo data
- **Q2 Revenue:** $12.4M (+18% YoY)
- **Gross Margin:** 74%
- **Operating Margin:** 22%
- **Net Income:** $1.8M
- **ARR:** $38.2M (+24%)
- **NRR:** 118%
- **Churn:** 3.2%
- **Cash Runway:** 14 months
- **Sales Pipeline (SQL/CRM sample):** $866K active / 9 deals
- **Sales Pipeline (Analytics aggregate):** $8.7M / 42 deals
- **Northwind Deal:** $450K ARR (3-year)
- **Headcount Plan:** 28 new roles, $3.1M loaded cost
- **Project Phoenix:** 68% complete, $1.2M budget, $80K under

### Key knowledge base documents

| ID | Title | Category | Status | Owner |
|----|-------|----------|--------|-------|
| SOP-001 | Information Security Policy | IT & Security | Active | CISO |
| SOP-002 | Employee Onboarding & Offboarding | HR | Active | VP People |
| SOP-003 | Financial Expense Reimbursement | Finance | Active | CFO |
| SOP-004 | Customer Data Handling & Privacy | Compliance | Active | CISO |
| SOP-005 | Vendor Security & Due Diligence | IT & Security | Active | CISO |
| SOP-006 | Incident Communication & Escalation | Compliance | Active | VP Communications |
| SOP-007 | Security Incident Response | IT & Security | Active | CISO |
| SOP-008 | Disaster Recovery & Business Continuity | IT & Security | Active | VP Engineering |
| POL-001 | Remote Work Policy | HR | Active | VP People |
| POL-002 | Code of Conduct | HR | Active | General Counsel |
| POL-003 | Parental Leave | HR | Active | VP People |
| POL-004 | Acceptable Use of Technology | IT & Security | Active | CISO |
| POL-005 | Anti-Harassment & Discrimination | HR | Active | General Counsel |
| POL-006 | Whistleblower Policy | Compliance | Active | General Counsel |
| POL-007 | Travel & Expense Policy | Finance | Active | CFO |
| POL-008 | Equity & Stock Option Policy | Finance | Active | CFO |
| POL-009 | Confidentiality & NDA Policy | Legal | Active | General Counsel |
| POL-010 | Social Media & Public Communications | Compliance | Active | VP Communications |

### Behind-the-scenes architecture (one-liners for the audience)

| Feature | One-liner |
|---------|-----------|
| **Streaming** | "Replies stream word-by-word like ChatGPT, not all at once." |
| **Tool calling** | "The agent decides which systems to query — SQL, files, email, OneDrive, KB, memory, docs, analytics." |
| **Circuit breaker** | "If an MCP server fails 3 times, it auto-cools for 30 seconds instead of cascading the failure." |
| **Rate limiting** | "Caps at 20 requests/minute per user to prevent cost overruns." |
| **Caching (Redis)** | "Repeated queries return instantly — results cached for 60 seconds." |
| **Multi-tool** | "Queries that need multiple systems run in parallel, not one at a time." |
| **OIDC CI/CD** | "Every push to main auto-deploys to Azure via DevOps Pipelines." |
| **Infrastructure as Code** | "All Azure resources defined in Terraform — one command to recreate everything." |

---

## 18. Troubleshooting During the Demo

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| "I could not reach the orchestrator" | Orchestrator Container App is scaled to 0 or crashed | Restart revision in Azure Portal |
| "No reply from orchestrator" | OpenAI rate limit or MCP server timeout | Wait 10 s, retry |
| "MCP mail returned 403" | Admin consent not granted for Graph API | Normal for personal M365 — demo fallback activates automatically |
| "MCP sql returned empty body" | Azure SQL Serverless is auto-paused | First query will be slow (~10 s); subsequent queries fast |
| Browser shows CORS error | Custom domain not in `CORS_ORIGINS` | Verify `demo.resiq.co` is in the orchestrator env var |
| `ERR_NAME_NOT_RESOLVED` for `api.resiq.co` | DNS not propagated | Wait 5–15 min after adding CNAME record; flush DNS |
| Old Azure URL still showing in UI | Static Web App not redeployed | Rebuild UI with `npm run build` and redeploy `dist/` folder |
| Knowledge Base returns empty | `kb_mcp` Container App crashed | Restart revision in Azure Portal |
| "Login failed" or Settings tab missing | Wrong credentials or not admin | Verify with the rotated demo creds; only admin sees Settings |
| Memory context not showing | `memory_mcp` Container App crashed | Restart revision in Azure Portal |
| Response not personalized | User not logged in or `user_id` not sent | Verify status bar shows user name; check DevTools network tab for `user_id` in `POST /chat` body |
| Document generation failed | `doc_mcp` Container App crashed | Restart revision in Azure Portal |
| Analytics not showing | `analytics_mcp` Container App crashed | Restart revision in Azure Portal |
| Stream cuts off mid-reply | SSE connection dropped (firewall/proxy) | Reload tab; tell audience streaming is best-effort |
| Pipeline number shows `$866K` not `$8.7M` (or vice versa) | **Working as intended** — see [Scenario D footnote](#8-scenario-d--sales-pipeline-intelligence-1-minute) | No fix needed; explain the SQL sample vs. Analytics aggregate distinction |

---

## 19. Future Enhancements

These features are **referenced in earlier docs but not yet shipped**. They're tracked in [GAPS.md](GAPS.md). Do **not** demo them as live.

| Feature | Status | Notes |
|---------|--------|-------|
| **Take the tour** auto-flow | Not implemented | An auto-runs-3-queries onboarding flow used to be in `docs/DEMO_SCRIPT.md`. Not present in `web_ui/src/App.tsx`. |
| **Conversation Export** to styled HTML | Not implemented | Mentioned in older docs as a takeaway. The `Clear` button exists; an `Export` button does not. |
| **Follow-up suggestion buttons** (gold-bordered, context-aware) | Not implemented | No follow-up rendering logic in `App.tsx`. Suggested-prompt chips on the welcome screen are the closest shipped feature. |
| **File download from FileCards** | Partial | The card is rendered, but click-to-download via the orchestration proxy is not yet wired end-to-end. |

---

## 20. Closing Narrative & Call to Action (30 seconds)

> *"What you just saw is a single chat interface that understood your intent, chose the right tools, queried eight different enterprise systems — Outlook, OneDrive, file shares, SQL, a knowledge base, a personalized memory layer, document generation, and analytics — and synthesized a board-ready briefing tailored to who was asking. It generated executive summaries, surfaced real-time KPIs, and drafted action-item lists. A CFO sees financial rollups with analytics. A Sales Director sees pipeline velocity with generated reports. An Engineer sees incident response SOPs with security metrics. Same interface — three completely different experiences. No switching apps. No writing SQL. No searching Outlook manually. Just ask. That's the power of an agentic architecture built on Azure Container Apps, OpenAI, and the Model Context Protocol."*

### Call to action

- **Try it:** <https://demo.resiq.co> *(rotated demo creds available on request)*
- **Learn more:** *<TODO: insert pilot-program contact email>*
- **Follow the build:** *<TODO: insert public repo URL or QR code>*
- **Send feedback:** *<TODO: insert feedback form / GitHub issues link>*

---

*Demo script v6.1 — last updated 2026-05-07. Reconciled section numbering, added Quick / Full demo paths, standardized the per-scenario template (Prompt → Point at → Expected → Talking points → If it fails), fixed pipeline figures to match actual SQL/Analytics MCP outputs, merged the short walkthrough from `docs/DEMO_SCRIPT.md`, and listed unshipped features in §19.*
