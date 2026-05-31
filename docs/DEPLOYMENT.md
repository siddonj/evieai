# Deployment Guide

## Prerequisites

- Azure CLI with Owner/Contributor on subscription `82aff681-2b59-4b43-aad7-18da14c63df4`
- Docker Desktop (Linux containers)
- Terraform 1.7+
- Node.js 20 LTS
- Python 3.11+

---

## Quick Start (Local Dev)

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env
# For Azure OpenAI:
#   LLM_PROVIDER=azure-openai
#   AZURE_OPENAI_ENDPOINT=...
#   AZURE_OPENAI_API_KEY=...
# For obot.ai:
#   LLM_PROVIDER=obot-ai
#   OBOT_BASE_URL=...
#   OBOT_API_KEY=...
#   OBOT_MODEL=...
#   OBOT_API_REQUIRED=false   # only if your self-hosted obot endpoint does not enforce API auth

# 2. Start full stack
docker compose up --build

# 3. Open UI
# http://localhost:5173 (Vite dev server with hot reload)
```

Services available:
- Orchestrator: `http://localhost:8000`
- Web UI: `http://localhost:5173`
- All MCP servers: `http://localhost:8001` through `http://localhost:8008`
- Context Forge Gateway (optional): `http://localhost:8100`

To enable local gateway mode, set in `.env`:

```bash
CONTEXT_FORGE_ENABLED=true
CONTEXT_FORGE_BASE_URL=http://context-forge:8100
CONTEXT_FORGE_FALLBACK_MODE=mcp
```

---

## Infrastructure Deployment

```bash
# One-time: bootstrap terraform backend (if not done)
cd terraform
# See terraform/bash1.sh for backend bootstrap commands

# Deploy/update infrastructure
cd terraform
terraform init
terraform plan      # review changes
terraform apply     # deploy (takes 10-15 minutes)
```

### What gets created
- 49 Azure resources (see `terraform/main.tf`)
- Key Vault secrets for all connections
- Container Apps with auto-scaling
- Static Web App with custom domain
- Azure Monitor alerts

### Post-deployment manual steps
1. **Admin consent:** Azure Portal → Entra ID → App registrations → `aiagent2-graph-app-dev` → API permissions → Grant admin consent
2. **Run SQL migrations + seed:** (one-time) populate SQL with demo data

```bash
# Run schema migrations (includes property-management tables such as units/leases/work_orders)
export DATABASE_CONNECTION_STRING="<sql-connection-string>"
python mcp_servers/sql/migrate.py

# Seed synthetic multifamily + property-management data
python mcp_servers/sql/seed/seed.py
```

The seeded property-management dataset is synthetic and inspired by common PMS workflows
(Entrata/Yardi-style domains), not copied from proprietary vendor data.
  
---

## Application Deployment

### Orchestrator

```bash
# Build
cd <repo-root>
docker build -f orchestrator/Dockerfile -t aiagent2acrdev.azurecr.io/orchestrator:latest .

# Push
az acr login --name aiagent2acrdev
docker push aiagent2acrdev.azurecr.io/orchestrator:latest

# Deploy (update Container App to pick up new image)
az containerapp update \
  --name aiagent2-orchestrator-dev \
  --resource-group rg-aiagent2-dev \
  --image aiagent2acrdev.azurecr.io/orchestrator:latest
```

### LLM Provider Cutover (Safe Sequence)

1. Deploy code with `LLM_PROVIDER=azure-openai` (no behavior change).
2. Set obot vars in your environment/pipeline/terraform vars:
   - `OBOT_BASE_URL`
   - `OBOT_API_KEY`
   - `OBOT_MODEL`
  - optional: `OBOT_API_REQUIRED=false` for trusted no-auth self-hosted endpoints
3. Switch `LLM_PROVIDER` to `obot-ai`.
4. Validate at runtime:

```bash
curl https://<orchestrator-url>/admin/llm-provider
```

Expected response should include:
- `"provider": "obot-ai"`
- `"supported": true`
- `"configured": true`
- `"missing_env_vars": []`

### Web UI

```bash
cd web_ui
npm install
npm run build

# Deploy to Static Web App
npx @azure/static-web-apps-cli deploy dist \
  --deployment-token "<SWA_TOKEN>" \
  --env production
```

Get `SWA_TOKEN`:
```bash
az staticwebapp secrets list \
  --name aiagent2-ui-dev \
  -g rg-aiagent2-dev \
  --query "properties.apiKey" -o tsv
```

### MCP Servers (when modified)

Same pattern as orchestrator — build with appropriate Dockerfile, push, update Container App:

```bash
docker build -f mcp_servers/<service>/Dockerfile -t aiagent2acrdev.azurecr.io/<name>:latest .
docker push aiagent2acrdev.azurecr.io/<name>:latest
az containerapp update --name aiagent2-mcp-<name>-dev -g rg-aiagent2-dev --image aiagent2acrdev.azurecr.io/<name>:latest
```

### Context Forge Gateway (Azure Container Apps)

Use Terraform for the full automated setup:

```bash
cd terraform
terraform plan -var "context_forge_enabled=true"
terraform apply -var "context_forge_enabled=true"
```

Optional rollout variables:
- `context_forge_image` (default `ghcr.io/ibm/mcp-context-forge:latest`)
- `context_forge_api_key`
- `context_forge_timeout_seconds`
- `context_forge_fallback_mode` (`mcp` or `error`)

When enabled, orchestrator routes MCP calls via Context Forge and can auto-fallback to direct MCP mode when configured.

---

## CI/CD (Azure DevOps)

Two pipelines auto-deploy on push to `main`:

### Terraform Pipeline (`.azure-pipelines/terraform.yml`)
- **PR to main:** `fmt` → `validate` → `plan`
- **Push to main:** `fmt` → `validate` → `plan` → `apply`

Requires pipeline variables: `ARM_CLIENT_ID`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID`

### Build & Deploy Pipeline (`.azure-pipelines/deploy.yml`)
- **Push to main:** `lint` → `build images` → `update Context Forge` → `update orchestrator + MCP apps` → `deploy SWA`

Requires service connections: `azure-sc`, `acr-sc`  
Requires variable group: `aiagent2-secrets` (contains `SWA_TOKEN`)

---

## Verification

```bash
# Health checks
curl https://api.resiq.co/health
curl https://api.resiq.co/ready

# Gateway admin checks
curl https://api.resiq.co/admin/gateway-config
curl https://api.resiq.co/admin/gateway-health
curl https://api.resiq.co/admin/gateway-reliability

# Test chat
curl -X POST https://api.resiq.co/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me the sales pipeline", "user_id": "test"}'

# View logs
az containerapp logs show \
  --name aiagent2-orchestrator-dev \
  -g rg-aiagent2-dev \
  --tail 50

# See current revision
az containerapp show \
  --name aiagent2-orchestrator-dev \
  -g rg-aiagent2-dev \
  --query "{rev: properties.latestRevisionName, img: properties.template.containers[0].image}"
```

---

## Tearing Down

```bash
cd terraform
terraform destroy
```

Note: Key Vault soft-delete may require manual purge before re-creation.
