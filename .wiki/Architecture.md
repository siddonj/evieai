# EvieAI Architecture

> High-level system design and component breakdown

## System Overview

```
┌─────────────────────────────────────────────────────────┐
│                    User Layer                           │
│  Web Browser (React)  │  Microsoft Teams (SSO)          │
└────────────┬──────────┴────────────┬─────────────────────┘
             │                       │
             │ HTTPS                 │ OAuth 2.0 (OBO)
             ▼                       ▼
┌──────────────────────────────────────────────────────────┐
│         Orchestrator (FastAPI)                           │
│  • Receives chat messages                               │
│  • Calls Azure OpenAI with available tools              │
│  • Routes tool calls to MCP servers                     │
│  • Synthesizes multi-source responses                   │
│  • Manages service restarts + admin operations          │
└──────────────┬──────────────────┬───────────────────────┘
               │                  │
    ┌──────────┴──────────────────┴─────────────┐
    │                                           │
    ▼ (Streamable HTTP)                        ▼
┌──────────────────────────────────────────────────────────┐
│         MCP Servers (Internal Only - VNet)               │
│  • SQL MCP (DAB) - Port 5000                            │
│  • File Share MCP - Port 8001                           │
│  • Mail MCP - Port 8002                                 │
│  • OneDrive MCP - Port 8003                             │
│  • Memory MCP - Port 8004                               │
│  • KB MCP - Port 8005                                   │
│  • Document Gen MCP - Port 8006                         │
│  • Analytics MCP - Port 8007                            │
│  • Dashboard MCP - Port 8009                            │
└──────┬─────────────────────────────────┬────────────────┘
       │                                 │
       ▼ (Azure Services)                ▼
┌──────────────────────────────────────────────────────────┐
│         Data & Secrets                                   │
│  • Azure OpenAI (GPT-4o)  • Azure SQL Serverless        │
│  • Key Vault              • Storage Account             │
│  • Log Analytics          • PostgreSQL (runtime state)  │
│  • Entra ID (Graph API)                                 │
└──────────────────────────────────────────────────────────┘
```

## Component Breakdown

### Web UI (React + Vite)
- Dark-themed chat interface with streaming
- Admin dashboard for service monitoring
- Multi-turn conversation history
- Settings panel

**Deployment:** Azure Static Web App (free tier, global CDN)

### Orchestrator (FastAPI)
- Central API for all chat requests
- Tool discovery and routing
- Azure OpenAI integration (GPT-4o with tool calling)
- Report generation via Jinja2 templates
- Service restart capability with Azure SDK fallback to CLI

**Deployment:** Azure Container Apps (public ingress)  
**Compute:** 0.5 vCPU, 1 GiB RAM per replica (auto-scales 0–5)

### MCP Servers
All expose tools via Streamable HTTP, run in isolated Container Apps with **internal-only ingress**.

| MCP | Port | Purpose | Key Tool |
|-----|------|---------|----------|
| SQL (DAB) | 5000 | Query Azure SQL | query_sql |
| File Share | 8001 | Search files | query_files |
| O365 Mail | 8002 | Email search (Graph API) | query_mail |
| OneDrive | 8003 | File search (Graph API) | query_onedrive |
| Memory | 8004 | User context/bookmarks | query_memory |
| Knowledge Base | 8005 | Semantic SOP search | query_knowledge_base |
| Doc Gen | 8006 | Report generation | query_document_generation |
| Analytics | 8007 | KPI dashboards | query_analytics |
| Dashboard | 8009 | Operational metrics | query_dashboard |

### Data Layer

**Azure SQL Serverless**
- Serverless compute (auto-pause after 1 hour)
- Automatically scales based on demand
- Backup included

**PostgreSQL** (optional)
- Event log storage
- Bitemporal schema for audit trail
- Runtime state persistence

**Azure Storage**
- File shares for File Share MCP
- Blob storage for generated reports
- Backup storage

**Key Vault**
- OpenAI API key
- SQL connection strings
- Graph API credentials
- Encryption keys

## Request Lifecycle

```
1. User types: "Show me Q2 revenue and unread emails"
              ↓
2. UI → POST /api/chat
   { message, history: [...], user_id }
              ↓
3. Orchestrator → Azure OpenAI
   "Available tools: query_analytics, query_mail"
              ↓
4. OpenAI decides: Call both tools
              ↓
5. Orchestrator → MCP Servers (parallel)
   GET /tools/query_analytics?query=Q2 revenue
   GET /tools/query_mail?filter=unread
              ↓
6. Results aggregated:
   • Analytics: "Q2 revenue $4.2M, +12% YoY"
   • Mail: "12 unread from finance team"
              ↓
7. Orchestrator → OpenAI (synthesis pass)
   Raw results injected into context
              ↓
8. OpenAI generates natural response
   "Q2 revenue is $4.2M, up 12% YoY. You have 12
    unread finance emails..."
              ↓
9. Orchestrator → UI
   Stream response with tool call badges
```

## Security Model

### Network Isolation
- **Public:** Only orchestrator `/api/chat` endpoint
- **Internal:** All MCP servers (unreachable from internet)
- **Managed Identity:** Services authenticate to Azure without credentials

### Data Protection
- **Secrets:** Azure Key Vault (encrypted, versioned, rotatable)
- **Transit:** HTTPS/TLS 1.2+
- **At rest:** Database encryption (TDE), blob encryption
- **Backups:** Geo-redundant, encrypted

### Access Control
- **Azure RBAC:** Per-service role assignments
- **Graph API:** Least-privilege scopes (Mail.Read, Files.Read.All)
- **Database:** Read-only user for queries (no insert/update)
- **Audit:** All actions logged (chat, restarts, approvals)

## Multi-Client Deployment (NEW in v1.5)

Deploy EvieAI to multiple client organizations with complete isolation:

### Naming Convention
```
Client: "acme-corp" | Environment: "prod"
         ↓
Resource Group:     rg-acme-corp-prod
Orchestrator:       acme-corp-orchestrator-prod
SQL MCP:            acme-corp-mcp-sql-prod
Mail MCP:           acme-corp-mcp-mail-prod
OneDrive MCP:       acme-corp-mcp-onedrive-prod
... (all other MCPs)
```

**Benefit:** Each client's resources completely isolated. No cross-contamination.

### Service Restart in Multi-Client
Each orchestrator reads its own `PROJECT_NAME` and `ENVIRONMENT` env vars, so restarts are automatically scoped to that client's services:

```
Client A Admin Dashboard
  PROJECT_NAME=acme-corp
  ENVIRONMENT=prod
             ↓
Constructs: acme-corp-mcp-sql-prod
             ↓
Restart only Client A's services
✗ Client B unaffected
```

### Cost Per Client
| Component | Cost | Notes |
|-----------|------|-------|
| Container Apps | $45–90/mo | Min 0 replicas (consumption) |
| OpenAI (GPT-4o) | $60–120/mo | 10K TPM, ~2M tokens/mo |
| SQL Serverless | $15–35/mo | Auto-pause |
| Storage + Vault + Logs | $20–30/mo | |
| **Total/Client** | **$140–275/mo** | Linear scaling with clients |

## Service Restart Architecture (NEW in v1.5)

### Flow
```
Admin Dashboard (click "Restart" button)
             ↓
POST /restart {service: "sql"}
             ↓
Orchestrator reads:
  PROJECT_NAME=aiagent2
  ENVIRONMENT=dev
  RESOURCE_GROUP=rg-aiagent2-dev
  AZURE_SUBSCRIPTION_ID=82aff681...
             ↓
Constructs app name: aiagent2-mcp-sql-dev
             ↓
Attempt 1: Azure SDK
  ContainerAppsAPIClient.revision_restart()
  (requires Contributor role on managed identity)
             ↓
Fallback: Azure CLI
  az containerapp revision restart
             ↓
Azure Container Apps restarts service
  • Stops current revision
  • Pulls fresh image
  • Starts new revision
  • Health check validates
             ↓
Response to UI
  "✓ Service restarted at 14:32:45 UTC"
```

### Environment Variables (Auto-Set by Terraform)
| Variable | Purpose | Source |
|----------|---------|--------|
| PROJECT_NAME | Resource prefix | terraform.tfvars |
| ENVIRONMENT | Deployment stage | terraform.tfvars |
| RESOURCE_GROUP | Azure RG name | Auto-constructed |
| AZURE_SUBSCRIPTION_ID | Subscription ID | Auto-detected |

No manual configuration needed for Azure deployments—Terraform sets these automatically!

## Observability

### Health Endpoints
```
GET /health               → Is service alive?
GET /ready                → Are dependencies reachable?
GET /metrics              → Prometheus format metrics
```

### Logging
- All logs streamed to Azure Log Analytics
- Pre-built KQL queries for:
  - MCP response times
  - Tool call success rates
  - Error rates by service
  - Restart events
  - Approval audit trail

### Monitoring
- CPU/memory usage per service
- Response time percentiles (p50, p95, p99)
- Error rate thresholds
- Connector sync backlog

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Web Framework | FastAPI | Latest |
| UI | React + TypeScript | 18+ |
| Build | Vite | Latest |
| LLM | Azure OpenAI | GPT-4o |
| Container | Docker | 20.10+ |
| Orchestration | Azure Container Apps | - |
| Database | Azure SQL Serverless / PostgreSQL | - |
| IaC | Terraform | 1.5+ |
| Code Quality | Ruff + mypy | Latest |
| Testing | pytest | 7.0+ |

## Cost Estimation (Single Client)

| Resource | Usage | Monthly Cost |
|----------|-------|--------------|
| Container Apps (0.5 vCPU × 1GB × 3.5 replicas avg) | 1,260 vCPU-hours | $30–45 |
| OpenAI (GPT-4o) | 10K TPM, ~2M tokens | $60–120 |
| SQL Serverless | 50 active hours/mo | $15–35 |
| Storage + Vault + Logs | Standard usage | $20–30 |
| UI (Static Web App) | Free tier | $0 |
| **Total** | | **$125–230/mo** |

See [[Deployment-Configuration]] for cost optimization strategies.

---

## Next Steps

- **Deploy locally:** [[Getting-Started]]
- **Deploy to Azure:** [[Deployment-Checklist]]
- **Run in production:** [[Operations]]
