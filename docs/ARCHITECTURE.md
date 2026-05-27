# AI-Powered Agentic Q&A — Architecture Overview

## High-Level Architecture

```
Browser (React UI)          Azure Container Apps              Azure Services
┌──────────────┐         ┌─────────────────────┐         ┌──────────────────┐
│  demo.resiq.co│──HTTPS──│    Orchestrator     │         │  Azure OpenAI     │
│              │         │     (port 8000)      │──API───│  (GPT-4o)         │
│  Streaming   │         │                     │         └──────────────────┘
│  Chat UI     │         │  • Tool calling loop │
│  Card Panel  │         │  • Rate limiter      │         ┌──────────────────┐
│  Export      │         │  • Circuit breaker   │         │  Azure SQL        │
│  History     │         │  • MCP cache (Redis) │         │  (Serverless)     │
└──────────────┘         │  • OBO auth          │         └──────────────────┘
                          │  • Blob reports      │
                          │  • Download proxy    │         ┌──────────────────┐
                          └─────────┬────────────┘         │  Azure Cache      │
                                    │                      │  for Redis        │
                 ┌──────────────────┼──────────────┐       └──────────────────┘
                 │                  │               │
          ┌──────▼──────┐   ┌──────▼──────┐  ┌─────▼──────┐   ┌──────────────┐
          │  SQL MCP    │   │ Files MCP   │  │ Mail MCP   │   │ Analytics    │
          │  (port 8004)│   │ (port 8001) │  │(port 8002) │   │  (port 8007) │
          │  wraps DAB  │   │Local/Azure  │  │Graph API   │   │ Demo KPIs    │
          └──────┬──────┘   │  Files      │  │Outlook     │   │ Trends       │
                 │          └─────────────┘  └─────────────┘   └──────────────┘
          ┌──────▼──────┐                                       ┌──────────────┐
          │   DAB       │   ┌─────────────┐  ┌─────────────┐   │ Memory MCP   │
          │  (port 5000)│   │ OneDrive    │  │ KB MCP      │   │  (port 8004) │
          │  REST/Graph │   │  (port 8003)│  │  (port 8005)│   │ Profiles     │
          └─────────────┘   │ Graph API   │  │ SOPs/Policy │   │ Bookmarks    │
                            └─────────────┘  └─────────────┘   └──────────────┘
                            ┌─────────────┐
                            │ Doc Gen MCP │
                            │  (port 8006)│
                            │ Templates   │
                            └─────────────┘
```

## Component Details

### Orchestrator (Python/FastAPI, port 8000)
- **Entry point:** All chat requests hit `/chat` (batch) or `/chat/stream` (SSE)
- **Tool calling loop:** Up to 5 rounds of OpenAI tool calls. Multi-tool calls run in parallel via `asyncio.gather`
- **Security:** Rate limiter (20 req/min/user), circuit breaker (3 failures, 30s cooldown), prompt injection detection
- **Caching:** Dual-layer (Redis + in-memory fallback). MCP results cached per query for 60s
- **Auth:** Teams SSO / OBO token exchange at `POST /auth/teams-token` (feature-flagged behind `ENABLE_TEAMS_SSO`)
- **Downloads:** Proxy endpoint `GET /download/{service}/{file_name}` forwards to MCP servers
- **Admin:** `GET /admin/mcp-config` lists MCP servers; `POST` enables/disables them

### 8 MCP Servers (Python/FastAPI, ports 8001-8008)
Each MCP server exposes three endpoints:
- `GET /health` — liveness probe
- `GET /mcp` — service info
- `POST /mcp/query` — main tool endpoint (accepts `{"query": "..."}` )
- `GET /mcp/files/{name}/download` — file download (file_share, onedrive)

All MCP servers use demo data when real data sources are unavailable (Graph API, DAB, Azure Files).

### Data Flow (Streaming)
1. Browser sends `POST /chat/stream` with `{"message": "...", "user_id": "..."}`
2. Orchestrator auto-fetches user context from Memory MCP (system prompt only)
3. Sends messages to Azure OpenAI with `stream=True`
4. Streams SSE events: `token` (word-by-word), `tool_start`, `tool_result`, `done`
5. Frontend renders tokens in real-time, shows tool badges, then data cards

### Data Flow (Batch)
Same as streaming, but returns complete `ChatResponse` JSON in one shot. Used as fallback.

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| FastAPI over fastmcp | Full control over streaming, caching, circuit breaker |
| SSE over WebSocket | Simpler, unidirectional, works through proxies |
| requirements.txt over Poetry | Pip is blocked in current dev environment |
| In-memory fallback for all services | Works without Redis, SQL, or Graph API credentials |
| Pinned image digests in Terraform | Predictable deployments, no accidental rollouts |
| System-assigned managed identities | No client secrets in container env vars |

## Infrastructure (Terraform)

49 Azure resources managed in `terraform/main.tf`:
- Resource Group, Log Analytics, ACR, Key Vault (with 9 secrets)
- Azure OpenAI (GPT-4o, S0), SQL Serverless
- Storage Account + File Share + Blob container (reports, 30-day auto-delete)
- Redis Cache (Basic C0)
- Container Apps Environment + 9 Container Apps
- Static Web App + custom domain (demo.resiq.co)
- Entra ID app registration for Graph API
- Azure Monitor alerts (restarts, 5xx, OpenAI throttling)

State stored in Azure Blob (`aiagent2tfstate` / `tfstate` container).
