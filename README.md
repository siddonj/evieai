# EvieAI

Production-ready agentic Q&A platform for multifamily/real-estate workflows.

## What this repo contains

- **Orchestrator** (`orchestrator/`): FastAPI service that handles chat, tool-calling, connector sync, approvals/write-back, and reliability gates.
- **MCP servers** (`mcp_servers/`): data/tool services (files, mail, OneDrive, memory, KB, docs, analytics, dashboard, SQL wrapper).
- **Web UI** (`web_ui/`): React + Vite admin/chat frontend.
- **Infra as code** (`terraform/`): Azure deployment.
- **Runtime docs** (`docs/`): architecture, deployment, API reference, DR.

> Note: some internal IDs and image names still use legacy `aiagent2` naming. Product name is **EvieAI**.

---

## Quick start (local, Docker)

### Prereqs

- Docker Desktop (or Docker Engine + Compose v2)
- 8+ GB RAM available to Docker
- Git

### 1) Clone and configure env

```bash
git clone https://github.com/siddonj/evieai.git
cd evieai
cp .env.example .env
```

Edit `.env` and set at minimum:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`

### 2) Start full stack

```bash
docker compose up --build
```

### 3) Open app

- Web UI: `http://localhost:5173`
- Orchestrator API: `http://localhost:8000`

---

## Service map (local)

- Orchestrator: `8000`
- DAB (SQL Data API Builder): `5000`
- File MCP: `8001`
- Mail MCP: `8002`
- OneDrive MCP: `8003`
- Memory MCP: `8004`
- Knowledge Base MCP: `8005`
- Document Generation MCP: `8006`
- Analytics MCP: `8007`
- SQL MCP wrapper: `8008`
- PostgreSQL MCP: `8010`
- Dashboard MCP: `8009`
- Web UI (Vite): `5173`

---

## Required configuration

### Root `.env`

Use `.env.example` as source of truth. Key groups:

1. **LLM**: Azure OpenAI endpoint/key/deployment
2. **Orchestrator ↔ MCP URLs**
3. **Storage / Graph API (optional by feature)**
4. **Connector runtime and reliability controls**
5. **Write-back actions / approval policy controls**

### Web UI env

Create `web_ui/.env` from `web_ui/.env.example` if you need to override API URL:

```bash
cp web_ui/.env.example web_ui/.env
```

---

## Run and validate

### Health checks

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/actions/reliability
curl -s http://localhost:8000/connectors/sync/reliability
```

### Unit tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r tests/requirements.txt
pytest -q tests/unit
```

### Frontend build

```bash
cd web_ui
npm ci
npm run build
```

---

## Support / operations

See **`docs/SUPPORT.md`** for:

- startup/shutdown and logs
- production smoke checks
- common failures and fixes
- write-back/approval troubleshooting

---

## Production deployment

- Primary IaC path: `terraform/` (Azure resources + container apps + SWA)
- Deployment details: `docs/DEPLOYMENT.md`
- Architecture: `docs/ARCHITECTURE.md`
- API reference: `docs/API_REFERENCE.md`

---

## Current admin/write-back UI

In `Settings → Approvals` you can now:

- view pending approvals
- approve/reject actions
- execute approved actions
- open/close connector circuit breakers
- view action + connector reliability snapshots

---

## License / usage

Internal project repository for EvieAI platform development and deployment.
