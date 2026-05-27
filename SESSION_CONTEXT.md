# AI Agentic Q&A — Session Context (May 6, 2026)

## Session Summary
Final verification and bug fixes for the 8-backend AI Agentic Q&A platform deployed on Azure.

## URLs
- **Chat UI:** https://demo.resiq.co
- **API:** https://api.resiq.co
- **Health Check:** `GET https://api.resiq.co/ready` (all 8 MCPs: `reachable: true`)

## Bugs Found & Fixed During This Session

| # | Issue | Root Cause | Fix | Status |
|---|-------|-----------|-----|--------|
| 1 | Mail/OneDrive/Files MCPs returned Graph API errors instead of demo fallback | Terraform pinned old image digests (`sha256:...`) | Rebuilt Docker images → pushed to ACR → updated digests in `terraform/main.tf` → `terraform apply` | ✅ Fixed |
| 2 | File Share MCP returned empty `items: []` | Same as #1 — old image without demo data | Same fix | ✅ Fixed |
| 3 | Multi-round conversation lost context | UI only sent current message; orchestrator had no `history` field | Added `history` to `ChatRequest` + UI sends full conversation context | ✅ Fixed |
| 4 | LLM chose `query_files` instead of `query_knowledge_base` for SOPs | Tool description wasn't explicit enough | Strengthened `query_knowledge_base` description: *"ALWAYS use this tool for SOPs... Do NOT use query_files or query_onedrive"* | ✅ Fixed |

## Files Modified (Committed to `main` as `4fcd14b`)

```
terraform/main.tf          — Updated 4 pinned ACR image digests
terraform/outputs.tf       — Added outputs for new MCP internal URLs
orchestrator/app/main.py   — Added history support + stronger KB tool description
web_ui/src/App.tsx         — UI sends full conversation history
web_ui/src/Cards.tsx       — Dark theme cards, tool badges, result decks
web_ui/src/styles.css      — Full dark theme styling
web_ui/src/main.tsx        — Entry point
web_ui/src/LoginPage.tsx   — Login screen
web_ui/src/SettingsPage.tsx — Admin settings with tabs
web_ui/src/auth.tsx        — Auth context
mcp_servers/analytics/     — NEW: Analytics MCP (port 8007)
mcp_servers/document_generation/ — NEW: Doc Gen MCP (port 8006)
mcp_servers/knowledge_base/  — NEW: KB MCP (port 8005)
mcp_servers/memory/        — NEW: Memory MCP (port 8004)
teams_app/                 — Teams sideloadable app package
DEMO_SCRIPT.md             — Full v6.0 demo script
```

## Docker Image Digests (Current — May 6, 2026)

| Image | Digest |
|-------|--------|
| `aiagent2acrdev.azurecr.io/orchestrator:latest` | `sha256:4877c3eba10db1982944888605254f3a65b921f9d2819765a8fe8ef49323429b` |
| `aiagent2acrdev.azurecr.io/mcp-mail:latest` | `sha256:b2845be1c878d506aafc9653817a42c817d2dce29a4a9e6700983483644cdea6` |
| `aiagent2acrdev.azurecr.io/mcp-onedrive:latest` | `sha256:55e23d6681a79a9255442b37a059fd44265a793b30d8af6b60e59decfd32a6e` |
| `aiagent2acrdev.azurecr.io/mcp-files:latest` | `sha256:0aaae5eaa2d2002ff31afd20bb6e6bc06c7618444682c68bdffeaf1097b4ecaf` |
| `aiagent2acrdev.azurecr.io/mcp-sql:latest` | `sha256:...` (unchanged — uses `:latest` tag) |
| `aiagent2acrdev.azurecr.io/mcp-knowledge-base:latest` | `sha256:...` (unchanged — uses `:latest` tag) |
| `aiagent2acrdev.azurecr.io/mcp-memory:latest` | `sha256:...` (unchanged — uses `:latest` tag) |
| `aiagent2acrdev.azurecr.io/mcp-document-generation:latest` | `sha256:...` (unchanged — uses `:latest` tag) |
| `aiagent2acrdev.azurecr.io/mcp-analytics:latest` | `sha256:...` (unchanged — uses `:latest` tag) |

## Demo Scenario Test Results (All ✅ PASS)

| Scenario | Tools Called | Result |
|----------|------------|--------|
| A — Financial Email Intelligence | `query_mail` | 13 emails, 5 unread revenue/budget with action items |
| B — OneDrive Revenue Reports | `query_onedrive` | Q2-2026-Revenue-Report.xlsx, Board-Deck-Q2-Review.pptx |
| C — File Share Excel Search | `query_files` | 4 finance Excel files |
| D — Sales Pipeline | `query_analytics` + `query_sql` | 6 KPI cards + 12 CRM contacts |
| E — Board Meeting Prep (multi-tool) | `query_mail` + `query_onedrive` + `query_analytics` + `query_files` | Synthesized 4-source board briefing |
| F — Knowledge Base SOPs | `query_knowledge_base` | 5 security SOPs with key points |
| G — Multi-Tool KB + Files | `query_files` + `query_memory` | Security SOP + file share compliance docs |
| H — Multi-Round Conversation | `query_analytics` + `query_sql` (with history) | Q2 vs Q3 pipeline comparison |
| I — Personalized Context | `query_memory` + `query_document_generation` | CFO-tailored board prep with bookmarks |
| J — Document Generation | `query_document_generation` | 5-page board briefing with sections + action items |
| K — Analytics KPIs | `query_analytics` | 6 sales KPI cards, 2 trends, 5 insights |

## Admin Endpoints Verified
- `GET https://api.resiq.co/admin/mcp-config` — All 8 servers enabled
- `GET https://api.resiq.co/admin/mcp-data/knowledge_base` — 18 documents (8 SOPs + 10 Policies)

## Next Steps / Notes for New Machine
1. Clone repo: `git clone https://github.com/siddonj/aiagent2.git`
2. Run `terraform plan` in `terraform/` to verify state matches digests above
3. If any Container App needs restart: `az containerapp revision restart --name <app> --resource-group rg-aiagent2-dev --revision <revision>`
4. UI is auto-deployed to `https://demo.resiq.co` via Static Web App
5. Complex multi-tool prompts may 500 on first attempt (OpenAI timeout) — retry after 5-10s

---
*Session ended: May 6, 2026. Commit: `4fcd14b` on `main`*
