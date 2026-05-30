# EvieAI — AI-Powered Agentic Q&A Platform

**Production-ready**, multi-tenant intelligent question-answering system for organizations with scattered data across Microsoft 365, databases, file shares, and analytics dashboards.

## What Is EvieAI?

EvieAI is an **AI-powered agent-driven Q&A platform** that synthesizes answers from multiple enterprise data sources. Instead of asking users to manually search email, OneDrive, SQL databases, and local files separately, a single natural-language question triggers intelligent data retrieval across all systems and a synthesized, contextual response.

**Key value proposition:**
- 🤖 **Agentic** — AI reasons over available tools and data sources automatically
- 🔗 **Multi-source** — One question across email, files, databases, dashboards
- 📊 **Report generation** — Converts answers into shareable HTML/PDF briefings
- 🔐 **Secure** — Azure-managed identities, no credential storage, RBAC-enforced
- 📱 **Multi-channel** — Web UI, Teams integration (SSO), REST API
- ⚙️ **Operational** — Admin dashboard with service monitoring and remote restart capability
- 🌍 **Multi-tenant** — Deploy to multiple client organizations with isolated resources and data

### What This Repo Contains

- **Orchestrator** (`orchestrator/`): FastAPI service orchestrating chat, tool-calling, connectors, approvals, reliability gates, and service management
- **MCP servers** (`mcp_servers/`): Decoupled data/tool services (SQL, files, O365 mail, OneDrive, memory, knowledge base, document generation, analytics, dashboard)
- **Web UI** (`web_ui/`): React + TypeScript + Vite admin dashboard and chat interface
- **Infrastructure as Code** (`terraform/`): Complete Azure environment (Container Apps, Storage, OpenAI, SQL, Key Vault, SWA)
- **Comprehensive Docs** (`docs/`): Architecture, deployment guides, API reference, DR playbook, operational runbooks

> **Note:** Internal resource names use legacy `aiagent2` prefix; product name is **EvieAI**. Multi-client deployments use custom prefixes per client.

---

## Core Capabilities

### Chat & Reasoning
- **Natural-language Q&A** — Ask questions in plain English; AI routes to appropriate data sources
- **Multi-source synthesis** — Single query aggregates results from email, files, databases, dashboards, and knowledge bases
- **Multi-turn conversations** — Context persists across conversation history; AI understands references to previous questions
- **Streaming responses** — Answers stream to UI in real-time as tools execute
- **Tool calling with metadata** — Visual badges show which data sources were queried ("📧 query_mail", "📊 query_analytics")

### Data Integration
- **SQL Databases** — Query Azure SQL via parameterized ORM (Data API Builder)
- **Microsoft 365 Email** — Full mailbox search with Graph API (Outlook connector)
- **OneDrive/SharePoint** — File search and metadata retrieval
- **Local file shares** — Search and index Azure Files or local storage
- **Knowledge bases** — Semantic search over SOPs, policies, and structured content
- **Analytics dashboards** — Pre-calculated KPIs, trends, and insights
- **User memory** — Session-specific context and user profiles

### Document Generation
- **Automated briefings** — Generate multi-section HTML reports from Q&A results
- **Customizable templates** — Use Jinja2 to format and style reports
- **Action items** — Extract and highlight recommended next steps
- **Export-ready** — Save as HTML or convert to PDF

### Administration & Operations
- **Real-time service monitoring** — Admin dashboard displays health status of all microservices
- **Remote service restart** — Restart individual MCP services or orchestrator from the admin UI without SSH/portal access
- **Approval workflow** — Review and approve write-back actions before execution
- **Circuit breakers** — Safety controls to prevent cascading failures or runaway tool execution
- **Reliability gates** — Automated thresholds block high-failure-rate operations
- **Audit logging** — All chat, approvals, and service actions logged for compliance

### Security
- **Azure Managed Identity** — No credential storage; services authenticate via system-assigned identities
- **Key Vault integration** — Secrets (API keys, connection strings) never appear in code or images
- **RBAC** — Fine-grained role assignments per service and per client
- **Teams SSO** — Optional single sign-on via Microsoft Entra (feature-flagged)
- **Data isolation** — Multi-tenant deployments use separate resource groups per client
- **Encrypted secrets** — Container Apps use `secretref:` syntax for Key Vault injection

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Orchestrator** | FastAPI (Python 3.11) | Core API, tool routing, session management |
| **LLM** | Azure OpenAI (GPT-4o) | Reasoning, tool selection, response synthesis |
| **Web UI** | React 18 + TypeScript + Vite | Chat interface, admin dashboard |
| **MCP Framework** | Model Context Protocol (fastmcp) | Standardized tool definitions and execution |
| **Database** | Azure SQL Serverless (T-SQL) + PostgreSQL | Structured data, entity resolution |
| **Storage** | Azure Blob Storage + File Shares | Documents, file share integration |
| **Secrets** | Azure Key Vault | Secure credential storage |
| **Identity** | Azure Entra ID | SSO, Graph API permissions, RBAC |
| **Container Orchestration** | Azure Container Apps | Microservice hosting, auto-scaling, health checks |
| **Static Hosting** | Azure Static Web App | CDN-backed React UI |
| **Logging** | Azure Log Analytics | Telemetry, debugging, operational insights |
| **IaC** | Terraform + Bicep | Infrastructure provisioning and updates |
| **CI/CD** | Azure DevOps Pipelines | Automated testing, image builds, deployments |
| **Testing** | pytest + unittest.mock | Unit and integration tests |
| **Code Quality** | Ruff (linter) + mypy (type checker) | Consistent style, type safety |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Layer                                  │
│  ┌──────────────┐  ┌─────────────────────────────────────────┐ │
│  │  Web Browser │  │  Microsoft Teams (sideloaded tab)       │ │
│  │  (React UI)  │  │  (single sign-on via Entra)             │ │
│  └──────┬───────┘  └─────────────┬───────────────────────────┘ │
└─────────┼──────────────────────────┼────────────────────────────┘
          │                          │
          │ HTTPS                    │ OAuth 2.0 OBO
          ▼                          ▼
┌──────────────────────────────────────────────────────────────────┐
│           Orchestrator (FastAPI)  — Port 8000 (Public)          │
│  • Receives: POST /chat messages with history                    │
│  • Calls: Azure OpenAI GPT-4o with available tools              │
│  • Routes: Tool calls to appropriate MCP servers                │
│  • Aggregates: Results into synthesized response                │
│  • Generates: HTML reports on demand                            │
│  • Manages: Service health, restarts, reliability gates         │
└─────────────────────┬──────────────────────────────────────────┘
                      │
      ┌───────────────┼───────────────┬────────────────┐
      │               │               │                │
      ▼               ▼               ▼                ▼
  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
  │ SQL MCP │  │File Mcp  │  │ Mail MCP │  │OneDrive MCP  │
  │(DAB)    │  │(8001)    │  │(8002)    │  │(8003)        │
  │(5000)   │  └──────────┘  └──────────┘  └──────────────┘
  └────┬────┘
       │  (internal ingress only — not reachable from internet)
       │
      ▼
┌────────────────┐
│ Azure SQL      │
│ Serverless     │
└────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│           Additional MCP Servers (Internal Only)                 │
│  • Knowledge Base (semantic search over SOPs)                    │
│  • Memory (user context, bookmarks)                             │
│  • Document Generation (template-based briefing writer)         │
│  • Analytics (KPI dashboards, trends)                           │
│  • Dashboard (operational metrics)                              │
└──────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│              Secrets & Logging                                   │
│  • Key Vault: OpenAI key, DB conn strings, Graph API secrets    │
│  • Log Analytics: Audit log, performance metrics                │
│  • Managed Identity: Services authenticate without credentials   │
└──────────────────────────────────────────────────────────────────┘
```

For detailed architecture, data flows, and design decisions, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Quick Start (Local Development)

### 1) Clone and configure env

```bash
git clone https://github.com/siddonj/evieai.git
cd evieai
cp .env.example .env
```

Edit `.env` and set **at minimum**:

```env
# Azure OpenAI (required)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Service restart configuration (required for admin restart feature)
PROJECT_NAME=aiagent2
ENVIRONMENT=dev
RESOURCE_GROUP=rg-aiagent2-dev
AZURE_SUBSCRIPTION_ID=<your-subscription-id>

# Optional: Graph API (for O365 Mail and OneDrive)
AZURE_TENANT_ID=<tenant-id>
AZURE_CLIENT_ID=<client-id>
AZURE_CLIENT_SECRET=<client-secret>
AZURE_USER_ID=<upn>
```

See `.env.example` for all available configuration options.

### 2) Start full stack

```bash
docker compose up --build
```

Brings up:
- Orchestrator (port 8000)
- Web UI (port 5173, Vite dev server with HMR)
- MCP servers (ports 8001–8007)
- PostgreSQL (port 5432)
- SQL Data API Builder (port 5000)

### 3) Open app

- **Chat UI**: http://localhost:5173
- **Orchestrator API**: http://localhost:8000
- **Admin Dashboard**: http://localhost:5173/admin

### 4) Try it out

```bash
# In a new terminal:
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What emails are in my inbox?", "history": []}'
```

---

## Service Map (Local Development)

| Service | Port | Purpose |
|---------|------|---------|
| **Orchestrator** | `8000` | Main API (FastAPI, public) |
| **Web UI** | `5173` | React + Vite dev server (auto-reload) |
| **File Share MCP** | `8001` | File search and listing |
| **O365 Mail MCP** | `8002` | Email search via Microsoft Graph |
| **OneDrive MCP** | `8003` | OneDrive file search and download |
| **Memory MCP** | `8004` | User context and bookmarks |
| **Knowledge Base MCP** | `8005` | Semantic search over SOPs |
| **Document Generation MCP** | `8006` | HTML briefing generation |
| **Analytics MCP** | `8007` | KPI and trend dashboard |
| **SQL Data API Builder (DAB)** | `5000` | REST interface to Azure SQL |
| **SQL MCP Wrapper** | `8008` | Adapter for DAB (internal only in prod) |
| **PostgreSQL** | `5432` | Event log and runtime state |
| **Dashboard MCP** | `8009` | Operational metrics |

---

## Deployment

### Unit Tests

```bash
# Run all unit tests (fast, mocked)
python -m pytest tests/unit -v

# Run with coverage
python -m pytest tests/unit --cov=orchestrator --cov-report=html

# Run a specific test file
python -m pytest tests/unit/test_chat.py -v
```

### Integration Tests

```bash
# Start docker-compose first
docker compose up -d

# Run integration tests against live services
python -m pytest tests/integration -v --base-url http://localhost:8000

# Run smoke tests
python -m pytest tests/smoke -v
```

### Frontend Build & Test

```bash
cd web_ui

# Install dependencies
npm install

# Run type checking
npm run type-check

# Build for production
npm run build

# Run tests (if configured)
npm test
```

### Pre-commit Hooks

The repo includes `.pre-commit-config.yaml` for automated checks:

```bash
# Install hooks (one-time)
pre-commit install

# Run manually before committing
pre-commit run --all-files
```

Checks include:
- Ruff linting and formatting
- Terraform validation
- YAML/JSON/TOML parsing
- Trailing whitespace
- File size limits

---

## API Reference

The orchestrator exposes a comprehensive REST API. Key endpoints:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/chat` | POST | Chat with the agent (streaming or batch) |
| `/health` | GET | Service health (always returns 200) |
| `/ready` | GET | Readiness probe (all dependencies reachable) |
| `/restart` | POST | Restart a specific service (admin only) |
| `/actions/approvals` | GET | List pending approvals |
| `/actions/{id}/approve` | POST | Approve an action |
| `/actions/reliability` | GET | Action reliability metrics |
| `/connectors/sync/runs` | GET | List connector sync runs |
| `/connectors/sync/reliability` | GET | Connector reliability metrics |

See [docs/API_REFERENCE.md](docs/API_REFERENCE.md) for the full OpenAPI spec and example requests.

---

## Troubleshooting

### Common Issues

**"Service unreachable" on `/ready`**
- Check MCP server logs: `docker compose logs {service}`
- Verify env vars are set (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY)
- Ensure Docker has at least 8 GB RAM available

**"401/403" from Mail or OneDrive**
- Verify Graph API credentials in `.env`
- Check Azure portal: Entra ID → App registrations → {project_name}-graph-app
- Ensure admin has granted consent for Mail.Read and Files.Read.All
- Verify target user UPN has a valid Microsoft 365 license

**"Tool call failed" in chat**
- Check orchestrator logs: `docker compose logs orchestrator`
- Run health check: `curl http://localhost:8000/ready`
- Verify the tool is enabled (check MCP server logs)
- Retry the request (some transient failures are auto-recovered)

**Slow response times**
- SQL Serverless: First query after auto-pause takes ~10s (normal)
- Check service metrics: `GET http://localhost:8000/health`
- Review Log Analytics for bottlenecks (in Azure deployments)

For more, see:
- [docs/SUPPORT.md](docs/SUPPORT.md) — Operations runbook
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — Deployment troubleshooting
- [docs/DR.md](docs/DR.md) — Disaster recovery playbook

---

## Documentation Index

| Document | Purpose | Audience |
|----------|---------|----------|
| [docs/FEATURES.md](docs/FEATURES.md) | Complete feature reference and capabilities | Everyone |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System design, data flows, multi-client deployment | Architects, developers |
| [docs/OPERATIONAL_GUIDE.md](docs/OPERATIONAL_GUIDE.md) | Daily operations, monitoring, troubleshooting | Operators, admins |
| [docs/API_REFERENCE.md](docs/API_REFERENCE.md) | REST API endpoints, schemas, examples | Developers, integrators |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Step-by-step deployment to Azure | DevOps, site reliability |
| [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md) | Quick checklist for new clients | Site owners |
| [docs/DEPLOYMENT_CONFIG.md](docs/DEPLOYMENT_CONFIG.md) | Environment variables and configuration | DevOps, administrators |
| [docs/SUPPORT.md](docs/SUPPORT.md) | Troubleshooting and runbooks | Operators |
| [docs/DR.md](docs/DR.md) | Disaster recovery and business continuity | Site owners, operators |
| [docs/INSTALL.md](docs/INSTALL.md) | Detailed installation guide | DevOps |
| [terraform/README.md](terraform/README.md) | Infrastructure as code reference | DevOps, architects |
| [AGENTS.md](AGENTS.md) | Development context and conventions | Developers |

---

## Getting Started

**New to EvieAI?** Start here:

1. **[README.md](README.md)** — You are here! Overview and quick start
2. **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — Understand the system design
3. **[docs/FEATURES.md](docs/FEATURES.md)** — Learn what EvieAI can do
4. **Local setup** — `docker compose up --build` and start chatting
5. **Admin features** — Explore `/admin` dashboard

**Deploying to production?**

1. **[docs/DEPLOYMENT_CONFIG.md](docs/DEPLOYMENT_CONFIG.md)** — Environment variable setup
2. **[terraform/README.md](terraform/README.md)** — Infrastructure provisioning
3. **[docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)** — Multi-client deployment steps
4. **[docs/OPERATIONAL_GUIDE.md](docs/OPERATIONAL_GUIDE.md)** — Operations and monitoring

**Running in production?**

1. **[docs/OPERATIONAL_GUIDE.md](docs/OPERATIONAL_GUIDE.md)** — Daily operations, service restart, monitoring
2. **[docs/SUPPORT.md](docs/SUPPORT.md)** — Troubleshooting common issues
3. **[docs/DR.md](docs/DR.md)** — Disaster recovery and backup procedures

---

## Documentation Index

---

## Contributing

EvieAI is an internal platform project. To contribute:

1. **Create a branch** from `main` for your feature or fix
2. **Run tests** locally (`pytest tests/unit`, `npm run build`)
3. **Follow code standards** (ruff format, mypy, eslint)
4. **Commit with descriptive messages** referencing any issues
5. **Push and open a PR** for code review
6. **CI/CD validates** linting, tests, and builds
7. **Merge after approval** — changes deploy automatically via Azure DevOps

See [PLAN.md](PLAN.md) for the feature roadmap and [GAPS.md](GAPS.md) for known limitations.

---

## License

Internal EvieAI platform — proprietary, confidential use only.
