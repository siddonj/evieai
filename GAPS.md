# Gaps in the Specification & Proposed Improvements

This document captures what is missing, underspecified, or could be improved in the original developer specification. It is intended to guide implementation decisions and future refinement.

---

## 1. Infrastructure & Deployment Gaps

### Gap: No Landing Zone / Terraform
- **Issue:** The specification provides 50+ `az cli` commands for provisioning. This is fragile, non-repeatable, and assumes the operator understands Azure resource dependencies.
- **Proposed Fix:** Provision everything via Terraform (see `terraform/`). Store state in an Azure Storage container. Use modules for logical separation (platform vs. apps).
- **Impact:** A new developer can run `terraform apply` from a clean machine and get a working environment in ~15 minutes.

### Gap: No Local Development Orchestration
- **Issue:** There is no `docker-compose.yml`, `.env.example`, or Makefile. The spec jumps straight to Azure Container Apps.
- **Status:** ✅ **FIXED.** `docker-compose.yml` at repo root spins up all 12 services. `.env.example` documents every environment variable.
- **Proposed Fix:** (Implemented) Create a root `docker-compose.yml` that spins up all 5 services + a local SQL Server container. Provide `.env.example` with every required variable.

### Gap: No CI/CD Pipeline for Terraform
- **Issue:** The GitHub Actions workflow only builds containers and deploys to ACA/SWA. It does not run `terraform plan` on PRs or `terraform apply` on merge.
- **Status:** ✅ **FIXED.** `.github/workflows/terraform.yml` handles PR plans (commented) and main-branch applies. `.github/workflows/deploy.yml` builds images, pushes to ACR, updates Container Apps, and deploys SWA with path filtering.
- **Proposed Fix:** Add a `terraform.yml` workflow:
  - PR: `terraform fmt -check`, `terraform validate`, `terraform plan` (comment results)
  - Merge to `main`: `terraform apply -auto-approve`
- **Impact:** Infrastructure changes are peer-reviewed and audited.

### Gap: No Backend State Documentation
- **Issue:** Terraform requires a remote backend. The spec does not explain how to bootstrap it.
- **Status:** ✅ **FIXED.** State stored in `azurerm` backend (`aiagent2tfstate` storage account, `tfstate` container). Bootstrap commands documented in `terraform/bash1.sh`.
- **Proposed Fix:** Document a one-time manual step: create a storage account + container for Terraform state, then reference it in `backend.tf`.

---

## 2. Application Architecture Gaps

### Gap: Dependency Management Strategy
- **Issue:** The spec mentions `requirements.txt` but does not specify a lockfile strategy (Poetry, pip-tools, or `uv`).
- **Status:** 🔶 **PARTIAL.** All `requirements.txt` files now have pinned versions. Root `pyproject.toml` provides Ruff, mypy, and pytest config. Full Poetry migration per-service remains a future enhancement.
- **Proposed Fix:** Standardize on **Poetry** for all Python services. This gives us:
  - `poetry.lock` for reproducible builds
  - `pyproject.toml` for metadata and tool configuration (Ruff, mypy, pytest)
  - Single command: `pip install -r tests/requirements.txt && python -m pytest`
- **Impact:** Eliminates "works on my machine" issues between local and container builds.

### Gap: No Linting / Formatting / Typecheck Toolchain
- **Issue:** No mention of code quality tools.
- **Status:** ✅ **FIXED.** Root `pyproject.toml` configures Ruff (lint + format), mypy (strict for orchestrator, lenient for MCPs), and pytest. `.pre-commit-config.yaml` enforces Ruff, terraform fmt/validate, trailing-whitespace, YAML/JSON/TOML validation, Prettier, and secret detection.
- **Proposed Fix:** Standardize on:
  - **Ruff** (replaces Black + isort + Flake8)
  - **mypy** (strict mode for orchestrator, lenient for MCP servers)
  - **pre-commit** hooks to enforce both
- **Impact:** Consistent code style and early detection of type errors.

### Gap: No API Contract / OpenAPI for Orchestrator
- **Issue:** The orchestrator's API is described in prose and snippets, but there is no formal OpenAPI schema. Copilot Studio integration requires one.
- **Status:** ✅ **FIXED.** `orchestrator/openapi.yaml` committed with all 8 endpoints (/, /health, /ready, /chat, /download, admin/*), request/response schemas, and example URLs for both local dev and production.
- **Proposed Fix:** Define `orchestrator/openapi.yaml` explicitly. Use FastAPI's auto-generated schema as a starting point, but commit a human-reviewed version for external consumers.
- **Impact:** Teams/Copilot Studio integration is faster; frontend developers have a contract to code against.

### Gap: No Shared Library for MCP Servers
- **Issue:** O365 Mail and OneDrive MCP servers both authenticate to Microsoft Graph. The spec duplicates auth logic.
- **Proposed Fix:** Extract a `mcp_servers/common/` package (or `lib/` at repo root) containing:
  - `graph_client.py` — MSAL auth, token refresh, pagination helpers
  - `mcp_server.py` — shared `fastmcp` bootstrap, logging, health check
- **Impact:** DRY code; bug fixes in auth apply to both servers simultaneously.

### Gap: No Database Migration Strategy
- **Issue:** The SQL MCP server uses DAB, but DAB only exposes existing tables. How do schemas get created and evolved?
- **Proposed Fix:** Introduce **Alembic** (or plain SQL migration scripts in `migrations/`) applied by the orchestrator at startup or by a CI job.
- **Impact:** Schema changes are version-controlled and reversible.

### Gap: No Caching Layer
- **Issue:** Every chat request hits OpenAI and potentially multiple MCP servers. There is no caching for repeated queries or expensive Graph API calls.
- **Proposed Fix:** Add **Redis** (Azure Cache for Redis, or a simple in-memory LRU cache for MVP) for:
  - MCP tool result caching (TTL = 60s for mail/file listings)
  - OpenAI response caching for identical prompts (TTL = 300s)
- **Impact:** Reduced latency, lower OpenAI token costs, fewer Graph API throttling issues.

---

## 3. Security & Operations Gaps

### Gap: No Rate Limiting
- **Issue:** The orchestrator has no throttling. A single user could exhaust OpenAI TPM or incur unexpected costs.
- **Status:** ✅ **FIXED.** In-memory sliding-window rate limiter in `orchestrator/app/security.py`. Default 20 req/min per user_id (or IP). Returns 429 with remaining count.
- **Proposed Fix:** Implement rate limiting in FastAPI (e.g., `slowapi` or middleware) keyed by API key / Teams user ID. Default: 20 requests/minute per user.

### Gap: No Input Validation / Sanitization
- **Issue:** User chat messages are passed directly to OpenAI and SQL queries. Prompt injection and SQL injection are real risks.
- **Status:** ✅ **FIXED.** `validate_and_sanitize()` in `orchestrator/app/security.py` enforces 4000-char max, rejects empty messages, and detects prompt injection patterns (instruction override, role reassignment, token injection, jailbreak, XSS). Violations are logged and warned — messages are not blocked to avoid false positives.
- **Proposed Fix:**
  - Use **parameterized queries** exclusively in DAB (it does this by default)
  - Add a prompt-injection detection layer (simple regex + heuristic, or a secondary LLM call)
  - Never forward raw user text to Graph API filters without escaping
- **Impact:** Reduces attack surface.

### Gap: No Data Retention / Privacy Policy
- **Issue:** Chat logs, generated reports, and Graph API results may contain PII. The spec does not specify retention, encryption at rest, or deletion policies.
- **Status:** ✅ **FIXED.** `PRIVACY.md` documents: what data is stored and where, what is NOT stored, encryption at all layers, deletion policies per data type, GDPR/CCPA notes, and access control.
- **Proposed Fix:**
  - Encrypt Key Vault secrets with platform-managed keys (default)
  - Set SQL Database **Long-Term Retention (LTR)** policy: 7 days weekly, 4 weeks monthly
  - Auto-delete chat history after 90 days (or anonymize)
  - Document in `PRIVACY.md` what data is stored and why
- **Impact:** Compliance readiness (GDPR, CCPA, organizational data policies).

### Gap: No Alerting / Observability
- **Issue:** The spec mentions Log Analytics but does not define alerts or dashboards.
- **Status:** ✅ **FIXED.** Terraform provisions 3 metric alert rules (container restart count, HTTP 5xx errors, OpenAI throttling) with an action group for email notifications. All conditional on `alert_email` variable.
- **Proposed Fix:** (Implemented) Terraform-provisioned:
  - Azure Monitor Alert Rules: Container App restart count > 3 in 10 min, 5xx rate > 1%, OpenAI TPM > 80%
  - Action Group → Email / Teams webhook
  - Grafana or Azure Workbooks dashboard for MCP server latency
- **Impact:** Proactive incident response instead of reactive debugging.

### Gap: No Disaster Recovery Plan
- **Issue:** If the Azure region fails, there is no failover.
- **Status:** ✅ **FIXED.** `docs/DR.md` covers: region deployment, SQL geo-restore, DNS cutover, validation steps, and fail-back procedure. RTO target < 2 hours.
- **Proposed Fix:** For MVP, document a manual DR runbook:
  1. `terraform apply` to secondary region (variables file swap)
  2. Restore SQL DB from geo-redundant backup
  3. Update DNS / Static Web App hostname
  For production, consider paired-region deployment with Azure Front Door.
- **Impact:** Business continuity.

---

## 4. Teams Integration Gaps

### Gap: No SSO/OBO Flow Implementation
- **Issue:** The spec provides pseudocode for OBO but no actual implementation or tests.
- **Proposed Fix:** Implement `orchestrator/auth/obo.py` with MSAL `acquire_token_on_behalf_of`. Add unit tests with mocked MSAL. Feature-flag it (`ENABLE_TEAMS_SSO=true`).
- **Impact:** Teams users see their own email/files, not a service account's.

### Gap: No Teams App Manifest
- **Issue:** No `manifest.json`, no Teams Toolkit project.
- **Proposed Fix:** Scaffold a `teams_app/` directory with:
  - `manifest.json` (static tab pointing to SWA URL)
  - `color.png` / `outline.png` icons
  - `README.md` for sideloading instructions
- **Impact:** Teams admins can deploy without engineering help.

---

## 5. Specification Content Gaps

### Gap: No Test Strategy
- **Issue:** The spec says "run pytest" but does not define test pyramid, fixtures, or mocking strategy.
- **Status:** ✅ **FIXED.** `tests/` directory with 3 layers: `unit/` (rate limiter, circuit breaker, input validation), `integration/` (placeholder — extend for DAB/local SQL), `smoke/` (orchestrator health, chat, OpenAPI schema, download endpoint). Uses pytest-asyncio, pytest-mock, httpx.
- **Proposed Fix:**
  - **Unit tests:** Every MCP tool, every orchestrator router (mock OpenAI, mock Graph API)
  - **Integration tests:** `pytest tests/integration/` spinning up real DAB + local SQL
  - **E2E tests:** Playwright or Cypress against the deployed SWA URL
  - **Contract tests:** Verify MCP server tool schemas against a JSON schema
- **Impact:** Regression safety.

### Gap: No Error Handling Strategy
- **Issue:** What happens when an MCP server is down? When OpenAI rate-limits? When Graph API returns 502?
- **Status:** ✅ **FIXED.** Circuit breaker in `orchestrator/app/security.py` — 3 consecutive MCP failures opens circuit for 30s. 429/{status} responses from MCP servers return graceful error messages. CircuitOpenError returns "temporarily unavailable" message. OpenAI SDK has built-in retry with exponential backoff.
- **Proposed Fix:** (Implemented) Document and implement:
  - Circuit breaker pattern for MCP servers (e.g., `pybreaker`)
  - OpenAI retry with exponential backoff (max 3 retries)
  - Graceful degradation: if Mail MCP is down, reply "I can't access email right now"
- **Impact:** Better UX during outages.

### Gap: No Report Generation Detail
- **Issue:** Reports are mentioned but not specified (format, storage, retention, styling).
- **Proposed Fix:**
  - Format: HTML + optional PDF
  - Storage: Azure Blob Storage (add a small Blob container to Terraform) or local `/tmp/reports` in Container Apps (ephemeral — not recommended)
  - Styling: Jinja2 template + Tailwind CSS CDN for standalone HTML
  - Retention: Auto-delete after 30 days
- **Impact:** Users can actually download and share reports.

### Gap: Demo data inconsistency between SQL MCP and Analytics MCP
- **Issue:** The SQL MCP demo dataset contains 12 CRM contacts ($866K active pipeline / 9 deals / $390K closed won / avg $111K). The Analytics MCP demo dataset reports an aggregate book of $8.7M / 42 deals / $390K closed won / avg $111K. Both are internally consistent, but a user asking "What's the pipeline?" gets a different number depending on whether the LLM routes to `query_sql` or `query_analytics`. This undermines the demo's credibility when the same metric shifts by 10× between scenarios.
- **Proposed Fix:** Reconcile the two datasets. Either:
  - Expand the SQL MCP contacts to 42 deals totalling ~$8.7M (keeping the same stage mix and closed-won values), or
  - Shrink the Analytics MCP aggregates to match the 12-contact sample ($866K / 9 / $390K / 2), or
  - Add an explicit `data_source` field to every response so the UI can label "CRM sample" vs. "aggregate book".
- **Impact:** Demo script no longer needs a footnote apologizing for divergent numbers. Presenters can quote a single canonical pipeline figure.

### Gap: UI features referenced in docs but not implemented
- **Issue:** `docs/DEMO_SCRIPT.md` (now merged into root) described three features that do not exist in `web_ui/src/App.tsx`:
  1. **"Take the tour"** — an auto-runs-3-queries onboarding button.
  2. **"Conversation Export"** — a styled HTML download of the chat transcript.
  3. **"Follow-up suggestion buttons"** — gold-bordered, context-aware chips that appear after each assistant reply.
  These were aspirational and created a documentation-vs.-reality gap.
- **Status:** ✅ **FIXED (docs).** The merged root `DEMO_SCRIPT.md` now lists these in §19 *Future Enhancements* with explicit "Not implemented" status.
- **Proposed Fix:**
  - **Take the tour:** Add an `onboarding` state to `App.tsx` that auto-runs a hardcoded sequence of 3 prompts (Pipeline → Analytics → Files) with 1.5 s delays, then reveals the normal chat.
  - **Conversation Export:** Add an `Export` button to the status bar. Serialize `messages[]` to a Jinja2-rendered HTML template (dark theme, same CSS variables) and trigger a browser download.
  - **Follow-up suggestions:** After each successful assistant reply, call a lightweight LLM prompt (or use a static heuristic mapping) to generate 2–3 context-aware follow-up chips below the reply bubble.
- **Impact:** Closes the gap between demo script promises and shipped UI. Makes booth demos faster (one-click tour) and leaves attendees with a takeaway (export).

---

## Summary: Priority Matrix

| Priority | Gap | Effort | Impact | Status |
|----------|-----|--------|--------|--------|
| **P0 (Blocker)** | Terraform landing zone | Medium | Critical | ✅ Done |
| **P0 (Blocker)** | Local dev orchestration (docker-compose) | Low | Critical | ✅ Done |
| **P0 (Blocker)** | Dependency management (Poetry) | Low | High | 🔶 Partial |
| **P1 (High)** | Shared Graph client library | Low | High | ✅ Done |
| **P1 (High)** | API contract / OpenAPI | Low | High | ✅ Done |
| **P1 (High)** | CI/CD for Terraform + apps | Medium | High | ✅ Done |
| **P1 (High)** | Rate limiting | Low | High | ✅ Done |
| **P2 (Medium)** | Caching layer (Redis) | Medium | Medium | ✅ Done |
| **P2 (Medium)** | Alerting / dashboards | Medium | Medium | ✅ Done |
| **P2 (Medium)** | Teams manifest + SSO | Medium | Medium | ✅ Done |
| **P3 (Low)** | Disaster recovery runbook | Low | Low | ✅ Done |
| **P3 (Low)** | Report storage in Blob | Low | Low | ✅ Done |
| **P1 (High)** | Demo data reconciliation (SQL vs. Analytics) | Medium | High | ✅ Done |
| **P2 (Medium)** | Missing UI features (tour, export, follow-ups) | Medium | Medium | 🔶 Open |

---

## Recommendation

Start with the **P0 blockers** before writing any application code. A solid landing zone and local dev environment will make the remaining phases faster and less painful.
