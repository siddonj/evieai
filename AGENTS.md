# AGENTS.md — EvieAI

> Hard-won context for agent sessions. If a fact is obvious from filenames, it is not here.

---

## Repo Layout

```
terraform/              # Azure landing zone — provision everything first
orchestrator/           # FastAPI core — chat, tool-calling, connectors, approvals (port 8000)
  app/                  #   FastAPI routers, services, middleware
  auth/                 #   Teams SSO / OBO token exchange
connectors/             # Connector runtime — protocol, registry, adapter stubs
  adapters/             #   PropexoAdapter, WebhookAdapter, etc.
mcp_servers/            # Data/tool services (streamable HTTP, ports 8001–8009)
  file_share/           #   Local files + Azure Files (port 8001)
  o365_mail/            #   Graph API Outlook (port 8002)
  onedrive/             #   Graph API OneDrive (port 8003)
  memory/               #   Profiles, bookmarks, user context (port 8004)
  knowledge_base/       #   SOPs, policy, structured KB (port 8005)
  document_generation/  #   Template-based report generation (port 8006)
  analytics/            #   Demo KPIs, trends (port 8007)
  dashboard/            #   Metrics aggregation (port 8009)
  sql/                  #   DAB config + SQL wrapper (port 8008)
  common/               #   Shared graph_client, auth helpers
web_ui/                 # React + Vite admin/chat frontend (port 5173)
db/migrations/          # Bitemporal schema + seed data
tests/                  # Unit, integration, and smoke tests
scripts/evals/          # Evaluation harness + reliability gate scripts
docs/                   # Architecture, deployment, API reference, DR, support, install
teams_app/              # Teams app manifest and verification
.azure-pipelines/       # Azure DevOps CI/CD pipelines
.github/workflows/      # GitHub Actions CI/CD (alternative)
.env.example            # Local environment variable template
docker-compose.yml      # Local full-stack orchestration
pyproject.toml          # Python toolchain config (Ruff, mypy, pytest)
PLAN.md                 # Phased implementation plan
GAPS.md                 # Known gaps and improvement proposals
```

**Rule of thumb:** If Terraform has not been applied yet, do not write application code. The landing zone must exist first.

---

## Terraform — The One Source of Truth for Azure

- **Never** use `az cli` to create or modify Azure resources. All infrastructure lives in `terraform/`.
- State backend uses Azure Storage (bootstrapped once manually; see `terraform/README.md`).
- Running `terraform apply` from a clean checkout takes ~10–15 minutes and creates:
  - Resource Group, Log Analytics, ACR, Key Vault, OpenAI, SQL Serverless, Storage, Container Apps, Static Web App
  - Entra ID app registration for Graph API (admin consent is still manual — see `terraform/README.md`)
- After first deploy, run `terraform output` to get URLs and connection strings.

**Key outputs:**
- `orchestrator_url` — public API
- `acr_login_server` — tag Docker images as `{acr_login_server}/orchestrator:latest`
- `key_vault_name` — secrets storage
- `ui_default_hostname` — chat UI URL

---

## Local Development

Goal: `docker compose up` from repo root brings up the full stack.

- `docker compose up --build` — starts orchestrator + 8 MCP servers + SQL Server + DAB + Web UI
- `docker-compose.yml` defines all services, ports, health checks, and environment
- `.env.example` must list every environment variable. Copy to `.env` and fill values (at minimum `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY`).
- **Ports (hard-coded in spec and Terraform):**
  - Orchestrator: `8000`
  - DAB (SQL Data API Builder): `5000`
  - File Share MCP: `8001`
  - O365 Mail MCP: `8002`
  - OneDrive MCP: `8003`
  - Memory MCP: `8004`
  - Knowledge Base MCP: `8005`
  - Document Generation MCP: `8006`
  - Analytics MCP: `8007`
  - SQL MCP (FastAPI wrapper): `8008` (mapped from container port `8004`)
- Orchestrator hot reload: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
- UI dev server: `npm run dev` (Vite, usually port `5173`)

**Note:** Azure Container Apps use different port assignments — `sql_mcp` and `memory_mcp` both use port 8004 in separate Container Apps (different FQDNs). Local docker-compose uses separate ports (8008/8004) to avoid collisions.

---

## Python Toolchain

- **Runtime:** 3.11+ (Docker base image: `python:3.11-slim`)
- **Dependency manager:** `requirements.txt` with pinned versions per service. Root `pyproject.toml` holds Ruff, mypy, and pytest configuration.
- **Lint / format / typecheck:**
  - `ruff check .` + `ruff format .`
  - `mypy .` (strict for orchestrator, lenient for MCP servers)
- **Test runner:** `pytest tests/ -v`
  - Unit tests mock OpenAI and Graph API
  - Integration tests require local services running

## MCP Servers — Fast & Critical Rules

1. **Transport:** Streamable HTTP (`fastmcp run server.py --transport streamable-http --port <PORT>`)
2. **Ingress:** In Azure, all MCP servers use **internal ingress only**. Only the orchestrator is public.
3. **SQL MCP:** Do not write a custom SQL server. Use Microsoft's DAB container (`mcr.microsoft.com/azure-databases/data-api-builder:latest`). We only maintain `dab-config.json`.
4. **Graph API (Mail + OneDrive):** Extract a shared `graph_client.py` into `mcp_servers/common/` or a shared package. Do not duplicate MSAL auth logic.
5. **Health checks:** Every MCP server must expose a lightweight health endpoint for Container Apps probes.

---

## Orchestrator — Architecture Notes

- **Framework:** FastAPI
- **OpenAI:** Azure OpenAI chat completions with tool/function calling
- **MCP client:** Must discover tools from each MCP server at startup (or cache schemas)
- **CORS:** Configured via env var `CORS_ORIGINS` (set to Static Web App URL in production)
- **Reports:** Generate HTML via Jinja2 templates; store in `/tmp/reports` locally, Azure Blob in production
- **Auth:** Teams SSO / OBO flow is feature-flagged (`ENABLE_TEAMS_SSO=true`). Do not make it mandatory for local dev.

---

## Secrets & Environment

- **Never commit secrets.**
- **Local:** `.env` file (gitignored)
- **Azure:** Terraform generates all secrets, stores them in **Key Vault**, and injects them into Container Apps as encrypted app secrets (not hardcoded in images). 
- **Production hardening:** Switch Container Apps to `secretref:` syntax resolving secrets via managed identity instead of direct Terraform injection. Managed identities and Key Vault role assignments are already provisioned for this upgrade.
- **Terraform outputs** a `.env`-compatible block for local use after `apply`.

---

## CI/CD — Azure DevOps Pipelines

### Pipelines

| Pipeline | YAML | Trigger | What it does |
|----------|------|---------|-------------|
| `Terraform` | `.azure-pipelines/terraform.yml` | PR to `main`: plan. Push to `main`: apply. | `fmt` → `validate` → `plan` (PR) or `apply` (merge) |
| `Build & Deploy` | `.azure-pipelines/deploy.yml` | Push to `main` (paths: `orchestrator/`, `mcp_servers/`, `web_ui/`) | Lint → build 9 Docker images → push to ACR → `az containerapp update` each → deploy SWA |

### Required Azure DevOps setup

**1. Service connections** (Project Settings → Service connections → New):

| Name | Type | How to create |
|------|------|--------------|
| `azure-sc` | Azure Resource Manager | New → Azure Resource Manager → Subscription scope. Select your subscription (`82aff681-2b59-4b43-aad7-18da14c63df4` / `ResiQ`). Name it `azure-sc`. |
| `acr-sc` | Docker Registry | New → Docker Registry → Azure Container Registry. Select `azure-sc` as the subscription, pick `aiagent2acrdev` from the dropdown. Name it `acr-sc`. |

**2. Variable group** (Pipelines → Library → `aiagent2-secrets`):

| Variable | How to get the value |
|----------|---------------------|
| `SWA_TOKEN` | `az staticwebapp secrets list --name aiagent2-ui-dev -g rg-aiagent2-dev --query "properties.apiKey" -o tsv` |

The deploy pipeline `YAML` already references this group — no manual linking needed.

**3. Create the pipelines** (Pipelines → New Pipeline → Azure Repos Git → `evieai` → Existing YAML):

- Select `/.azure-pipelines/terraform.yml` → Save as `Terraform`
- Select `/.azure-pipelines/deploy.yml` → Save as `Build & Deploy`

**4. Terraform OIDC authentication:**

The terraform pipeline uses `ARM_USE_OIDC: true`. Variables must be set on the Terraform pipeline (Edit → Variables):

| Variable | Value |
|----------|-------|
| `ARM_CLIENT_ID` | Service principal app ID (`20e46d4c-bb19-417c-bf62-45b64af80342`) |
| `ARM_TENANT_ID` | `f2e5a963-b89f-40f9-90d0-4214549acf22` |
| `ARM_SUBSCRIPTION_ID` | `82aff681-2b59-4b43-aad7-18da14c63df4` |

### Pipeline verification

| Check | Command |
|-------|---------|
| See pipeline runs | Pipelines → Pipelines → select pipeline → Runs |
| Trigger manually | Pipelines → select pipeline → Run pipeline |
| View lint failures | Click the run → Lint stage → expand failing task |
| View deploy logs | Click the run → Deploy stage → expand `az containerapp` step |

### Pre-commit hooks

`.pre-commit-config.yaml` enforces Ruff, terraform fmt/validate, trailing-whitespace, YAML/JSON/TOML checks, and Prettier. Run `pre-commit install` once per machine. The CI lint job also runs these checks on every push.

### GitHub Actions (also available)

The `.github/workflows/` directory contains equivalent workflows if you prefer GitHub Actions over Azure DevOps. Both achieve the same result — choose whichever CI provider you're using.

---

## Testing — What to Run & When

| Context | Command |
|---------|---------|
| Local unit tests | `python -m pytest tests/unit -v` |
| Local integration | `docker compose up` then `python -m pytest tests/integration -v --base-url http://localhost:8000` |
| Deployed smoke tests | `pytest tests/smoke -v --base-url $(terraform output -raw orchestrator_url)` |
| Terraform validation | `terraform fmt -check && terraform validate` |

---

## Common Pitfalls

1. **Managed identity role propagation delay.** Terraform assigns Key Vault Secrets User roles to Container App identities, but Azure AD replication can take 1–2 minutes. If a Container App later switches to `secretref:` and crashes on startup, wait and restart the revision.
2. **Admin consent is manual.** After `terraform apply`, a Global Admin must open the Azure portal → Entra ID → App registrations → API permissions → Grant admin consent. Without this, Mail/OneDrive MCP returns 403.
3. **DAB config drift.** If you change SQL schema, you must update `dab-config.json` and rebuild the DAB container image or mount the new config. DAB does not auto-discover schema changes.
4. **SQL Serverless cold start.** First query after auto-pause incurs ~10s delay. For demos, run a warm-up query or disable auto-pause (`--auto-pause-delay -1`).
5. **Port collisions in docker-compose.** The orchestrator expects MCP servers at specific ports. Do not change them without updating orchestrator env vars.
6. **First run setup.** Copy `.env.example` to `.env` and fill in `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` at minimum. Run `docker compose up --build` from repo root.

---

## External References

- Original spec: `AI-Powered Agentic Q&A App — Developer Specification (1).docx`
- Implementation plan: `PLAN.md`
- Known gaps: `GAPS.md`
- Terraform docs: `terraform/README.md`
