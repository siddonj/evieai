# AI-Powered Agentic Q&A App — Implementation Plan

> This plan assumes **zero Azure knowledge** and **no existing landing zone**. All Azure infrastructure is provisioned via Terraform. Application code is generated after the landing zone is stable.

---

## Phase 0: Prerequisites & Tooling (1–2 days)

Goal: Every contributor can run `terraform apply` and local dev commands from a clean machine.

- [ ] Install Terraform 1.7+, Azure CLI, Docker Desktop, Node.js 20 LTS, Python 3.11+
- [ ] Run `az login` and `az account set --subscription <id>`
- [ ] Install pre-commit hooks (terraform fmt, tflint, trailing-whitespace)
- [ ] Decide dependency managers: **Poetry** for Python, **npm** for React
- [ ] Create repo skeleton (`orchestrator/`, `mcp_servers/`, `web_ui/`, `terraform/`, `.github/workflows/`)
- [ ] Bootstrap `AGENTS.md` (this file will evolve)

---

## Phase 1: Landing Zone — Terraform Infrastructure (3–5 days)

Goal: A reproducible, destroyable Azure environment with zero manual portal clicks.

**What the landing zone provisions:**
1. Resource Group + naming convention (`rg-aiqa-<env>`)
2. Log Analytics Workspace (central logs for all Container Apps)
3. Azure Container Registry (ACR) — `Basic` SKU for dev, `Standard` for prod
4. Azure Key Vault — all secrets live here; apps use **system-assigned managed identity**
5. Azure OpenAI — GPT-4o deployment with TPM capacity
6. Azure SQL Server + Serverless Database — firewall rules + admin login
7. Azure Storage Account + File Share — for the File Share MCP server
8. Azure Container Apps Environment — internal VNet integration (optional but recommended)
9. Azure Static Web App — free tier for dev

**Key Terraform decisions:**
- State stored in an Azure Storage backend (created once manually, documented in `terraform/README.md`)
- All secrets injected into Key Vault during `terraform apply`; never committed to git
- Outputs file generates a `.env` for local development automatically

**Deliverables:**
- `terraform/` directory with modular, documented code
- `terraform apply` succeeds from a fresh checkout
- `terraform destroy` tears down everything cleanly

---

## Phase 2: Local Development Bootstrap (2–3 days)

Goal: `docker compose up` brings up the entire stack locally.

- [ ] Root-level `docker-compose.yml`:
  - Orchestrator (port 8000)
  - SQL MCP via DAB container (port 5000)
  - File Share MCP (port 8001)
  - O365 Mail MCP (port 8002)
  - OneDrive MCP (port 8003)
  - Local SQL Server container (for DAB to target)
  - Azurite or local volume for file share testing
- [ ] `.env.example` with every variable an agent needs
- [ ] `Makefile` or `package.json` scripts for common tasks:
  - `make infra` → `terraform apply`
  - `make dev` → `docker compose up --build`
  - `make test` → `pytest tests/ -v`
  - `make lint` → `ruff check . && mypy .`
- [ ] Health-check endpoints for every service

---

## Phase 3: MCP Servers (5–7 days)

Goal: All 4 MCP servers run locally and in Azure, exposing tools via Streamable HTTP.

### 3a — SQL MCP (Data API Builder)
- Containerize Microsoft's `mcr.microsoft.com/azure-databases/data-api-builder:latest`
- DAB config (`dab-config.json`) maps SQL tables to REST/GraphQL
- Terraform deploys with `ingress = internal` and Key Vault secret reference for connection string

### 3b — File Share MCP
- `fastmcp` server reading from `BASE_PATH`
- Cloud adaptation: use `azure-storage-file-share` SDK when `AZURE_STORAGE_ACCOUNT` is set
- Local: bind-mount a host directory

### 3c — O365 Mail MCP
- MS Graph client credentials flow (fallback to OBO in Teams context)
- Tools: `search_emails`, `read_email`, `send_email`
- Handles pagination and large inboxes

### 3d — OneDrive MCP
- MS Graph file listing, search, download
- Shared code with Mail MCP for auth/Graph client (extract a `mcp_servers/common/` library)

**Deliverables:**
- Each server has `server.py`, `Dockerfile`, `requirements.txt`, `tests/`
- `pytest` passes for all 4 servers
- Servers register themselves to the orchestrator via env vars (`MCP_<NAME>_URL`)

---

## Phase 4: Orchestrator (4–6 days)

Goal: FastAPI app that receives chat messages, routes to OpenAI, and dynamically invokes MCP tools.

- [ ] OpenAI chat completions with function/tool calling
- [ ] MCP client implementation (Streamable HTTP transport)
- [ ] Tool discovery: fetch tool schemas from each MCP server at startup
- [ ] Report generation pipeline (HTML + optional PDF via `weasyprint` or Playwright)
- [ ] CORS configuration driven by env var (Static Web App URL)
- [ ] Structured logging to stdout (Container Apps captures this automatically)
- [ ] `/health` and `/ready` probes

**Deliverables:**
- `orchestrator/main.py`, routers, services, tests
- Dockerfile with multi-stage build (slim final image)
- Local: `uvicorn main:app --reload` for hot reload

---

## Phase 5: Web UI (3–4 days)

Goal: React chat interface that talks to the orchestrator.

- [ ] Vite + React + TypeScript scaffold
- [ ] Chat thread UI with streaming responses (SSE or WebSocket)
- [ ] Markdown rendering for agent replies
- [ ] Report download viewer
- [ ] `VITE_API_BASE_URL` injected at build time for production
- [ ] Basic error handling and retry logic

**Deliverables:**
- `web_ui/` with `npm run dev` (port 5173) and `npm run build`
- Dockerfile (optional) or direct SWA deployment from `dist/`

---

## Phase 6: Integration & End-to-End Testing (3–4 days)

Goal: The full stack works together in the Azure landing zone.

- [ ] Post-deployment verification script (shell or Python):
  1. Health checks on all services
  2. Chat round-trip via orchestrator
  3. Tool invocation: SQL query, file list, email count, OneDrive search
  4. Report generation and download
- [ ] GitHub Actions workflow:
  - Trigger: push to `main`
  - Steps: build images → push to ACR → `terraform apply` (or `az containerapp update`) → deploy SWA
- [ ] Load test (optional): `k6` or `locust` against `/api/chat`

---

## Phase 7: Microsoft Teams Integration (2–3 days)

Goal: Users can interact with the agent inside Teams without leaving the app.

- [ ] **Recommended path:** Copilot Studio plugin (Section 9.4 of spec)
  - No bot code required
  - Point Copilot Studio to orchestrator OpenAPI spec
  - Publish to Teams channel
- [ ] **Alternative:** Teams Toolkit static tab embedding the React UI
  - SSO token via `@microsoft/teams-js`
  - Orchestrator exchanges token via OBO flow

**Deliverables:**
- Teams app manifest (`manifest.json`)
- SSO/OBO flow implemented in orchestrator (behind feature flag)

---

## Phase 8: Production Hardening (Ongoing)

- [ ] Enable Azure Monitor alerts (Container App restarts, 5xx rates, OpenAI TPM exhaustion)
- [ ] WAF / Front Door in front of orchestrator (optional)
- [ ] SQL Database backup policy (LTR — Long Term Retention)
- [ ] Key Vault soft-delete protection and RBAC lockdown
- [ ] Cost alerts ($ threshold on subscription)
- [ ] Rotate secrets quarterly via Terraform + Key Vault

---

## Execution Order Summary

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7 → Phase 8
   │          │          │          │          │          │          │          │
   │          │          │          │          │          │          │          └─ Continuous
   │          │          │          │          │          │          └─ Teams SSO + Copilot Studio
   │          │          │          │          │          └─ React UI + SWA deploy
   │          │          │          │          └─ FastAPI + OpenAI + MCP client
   │          │          │          └─ 4x MCP servers + DAB
   │          │          └─ docker-compose + .env + Makefile
   │          └─ terraform apply (resource group → apps)
   └─ Install tools + repo skeleton
```

---

## Decision Log

| Decision | Rationale |
|----------|-----------|
| **Terraform over az CLI** | Reproducible, reviewable, destroyable. The spec used `az` commands which are error-prone for beginners. |
| **Poetry for Python** | Lockfile guarantees reproducible builds across local, CI, and container. Replaces plain `requirements.txt`. |
| **Single Container Apps Environment** | All MCP servers live in one ACA env with internal ingress. Orchestrator is the only public-facing app. |
| **DAB for SQL MCP** | Avoids writing a custom SQL MCP server. Microsoft maintains the image; we only maintain `dab-config.json`. |
| **Copilot Studio over Bot Framework** | Bot Framework requires Azure Bot resource, extra code, and ongoing certificate management. Copilot Studio is the 2025+ recommended path. |
| **System-assigned managed identities** | No client secrets in container env vars. Key Vault access is granted via Azure RBAC in Terraform. |

---

## Estimated Timeline

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 0 — Prerequisites | 1–2 days | 2 days |
| 1 — Landing Zone | 3–5 days | 7 days |
| 2 — Local Dev Bootstrap | 2–3 days | 10 days |
| 3 — MCP Servers | 5–7 days | 17 days |
| 4 — Orchestrator | 4–6 days | 23 days |
| 5 — Web UI | 3–4 days | 27 days |
| 6 — Integration + CI/CD | 3–4 days | 31 days |
| 7 — Teams Integration | 2–3 days | 34 days |
| 8 — Production Hardening | Ongoing | — |

**Conservative total: 5–7 weeks to production-ready MVP.**
