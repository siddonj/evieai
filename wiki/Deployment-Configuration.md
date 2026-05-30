# Deployment Configuration Reference

> Environment variables, settings, and multi-client configuration guide

## Required Environment Variables

These must be set before running EvieAI in Azure:

| Variable | Purpose | Default | Required | Example |
|----------|---------|---------|----------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource URL | — | ✅ | `https://my-openai.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | OpenAI API key | — | ✅ | `sk-aaa...` |
| `AZURE_OPENAI_DEPLOYMENT` | GPT-4o deployment name | — | ✅ | `gpt-4o` |
| `PROJECT_NAME` | Resource prefix for all Azure resources | `aiagent2` | ❌ | `acme-corp` |
| `ENVIRONMENT` | Deployment stage | `dev` | ❌ | `prod` |
| `RESOURCE_GROUP` | Azure resource group name | Auto-constructed from PROJECT_NAME + ENVIRONMENT | ❌ | `rg-acme-corp-prod` |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription ID | Auto-detected | ❌ | `82aff681-2b59-4b43-...` |

## Optional Environment Variables

| Variable | Purpose | Default | Options |
|----------|---------|---------|---------|
| `AZURE_OPENAI_API_VERSION` | OpenAI API version | `2024-10-01-preview` | `2024-08-01-preview` or newer |
| `ENABLE_TEAMS_SSO` | Enable Microsoft Teams single sign-on | `false` | `true` / `false` |
| `ENABLE_APPROVALS` | Enable write-back approval workflow | `true` | `true` / `false` |
| `DATABASE_TYPE` | Primary database | `sql` | `sql` / `postgres` |
| `LOG_LEVEL` | Logging verbosity | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `CORS_ORIGINS` | Allowed cross-origin domains | `*` | Comma-separated list |
| `SQL_SERVER` | Azure SQL server hostname | Auto-detected from Terraform | `my-server.database.windows.net` |
| `SQL_DATABASE` | Database name | `evieai` | Custom name |
| `SQL_USER` | SQL authentication user | `sqladmin` | Custom user |
| `POSTGRES_HOST` | PostgreSQL hostname (if using Postgres) | — | Hostname |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | Port number |
| `GRAPH_CLIENT_ID` | Azure Entra app registration ID | Auto-set by Terraform | UUID |
| `GRAPH_TENANT_ID` | Azure Entra tenant ID | Auto-set by Terraform | UUID |
| `KEY_VAULT_NAME` | Azure Key Vault name | Auto-detected | `kv-acme-corp-prod` |

## Multi-Client Deployment Variables

When deploying to multiple clients, use different values for `PROJECT_NAME` and `ENVIRONMENT`:

### Example: Two Clients

**Client A (Acme Corp - Production):**
```
PROJECT_NAME=acme-corp
ENVIRONMENT=prod
RESOURCE_GROUP=rg-acme-corp-prod
AZURE_SUBSCRIPTION_ID=82aff681-2b59-4b43-aad7-18da14c63df4
```

**Client B (Beta Corp - Staging):**
```
PROJECT_NAME=beta-corp
ENVIRONMENT=staging
RESOURCE_GROUP=rg-beta-corp-staging
AZURE_SUBSCRIPTION_ID=82aff681-2b59-4b43-aad7-18da14c63df4
```

**Result:**
- Client A resources: `acme-corp-orchestrator-prod`, `acme-corp-mcp-sql-prod`, etc.
- Client B resources: `beta-corp-orchestrator-staging`, `beta-corp-mcp-sql-staging`, etc.
- Each client's restart only affects their own services
- Separate databases, vaults, logs per client

## Graph API Permissions

For email and OneDrive integration, the app registration requires:

| API | Permission | Scope | Notes |
|-----|-----------|-------|-------|
| Microsoft Graph | Mail.Read | mail/messages | Read user mailbox |
| Microsoft Graph | Files.Read.All | drives/items | Read OneDrive/SharePoint |
| Microsoft Graph | User.Read | user/profile | Read user identity |

**Setup after Terraform deploy:**
1. Azure Portal → Entra ID → App Registrations → Find app (named `{PROJECT_NAME}-graph`)
2. API Permissions → Grant admin consent (requires Global Admin)
3. Certificates & secrets → Create new (for service-to-service auth)

## Local Development (.env file)

Copy `.env.example` to `.env` and fill in:

```bash
# Azure OpenAI (required for chat to work)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Optional: Service restart configuration
PROJECT_NAME=aiagent2
ENVIRONMENT=dev
RESOURCE_GROUP=rg-aiagent2-dev
AZURE_SUBSCRIPTION_ID=

# Optional: Graph API (if using email/OneDrive)
GRAPH_CLIENT_ID=
GRAPH_TENANT_ID=

# Optional: Database
DATABASE_TYPE=sql
SQL_SERVER=
SQL_DATABASE=evieai
SQL_USER=sqladmin

# Optional: Features
LOG_LEVEL=INFO
ENABLE_APPROVALS=true
CORS_ORIGINS=http://localhost:5173,http://localhost:8000
```

Then run:
```bash
docker compose up --build
```

## Azure Terraform Deployment

### Step 1: Create terraform.tfvars

```hcl
# terraform.tfvars
location                = "eastus"
resource_group_prefix   = "rg"
app_name                = "acme-corp"  # CLIENT NAME
environment             = "prod"        # DEPLOYMENT STAGE
openai_capacity         = 100           # Requests per minute
sql_admin_username      = "sqladmin"
enable_teams_sso        = true
enable_approvals        = true
log_retention_days      = 90
```

### Step 2: Set Secrets in Key Vault

```bash
# Terraform will create the Key Vault, then add these secrets:

az keyvault secret set \
  --vault-name "kv-${APP_NAME}-${ENVIRONMENT}" \
  --name "openai-api-key" \
  --value "sk-..."

az keyvault secret set \
  --vault-name "kv-${APP_NAME}-${ENVIRONMENT}" \
  --name "graph-client-secret" \
  --value "..."
```

### Step 3: Deploy Infrastructure

```bash
cd terraform
terraform init -backend-config="..."
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

**Terraform outputs:**
```
orchestrator_url        = https://acme-corp-orchestrator-prod.yellowpond-...
sql_server_name         = acme-corp-sql-prod
key_vault_name          = kv-acme-corp-prod
acr_login_server        = aiagent2acrdev.azurecr.io
ui_default_hostname     = acme-corp-ui-prod.azurestaticapps.net
```

### Step 4: Grant Admin Consent for Graph API

```bash
# Open Azure Portal → Entra ID → App Registrations
# Find: acme-corp-graph
# → API Permissions → Grant admin consent (button, requires Global Admin)
```

## Cost Optimization

### Strategy 1: Reduce Container Replicas
```hcl
# terraform.tfvars
min_replicas = 0          # Scale down to 0 when idle
max_replicas = 5          # Instead of 10
```

**Impact:** Save ~$20/month per service

### Strategy 2: Use Serverless Database
```hcl
# Terraform already defaults to serverless
# No changes needed - auto-pauses after 1 hour inactivity
```

**Impact:** Save ~$15/month

### Strategy 3: Reduce Log Retention
```hcl
log_retention_days = 30   # Instead of 90
```

**Impact:** Save ~$5/month

### Strategy 4: Single Region
```hcl
location = "eastus"       # Stay in one region (no geo-replication cost)
```

**Impact:** Save ~$10/month

**Total optimization:** ~$50/month per client

## Validation Checklist

Before deploying to production:

- [ ] All required env vars set (OPENAI_*, PROJECT_NAME, ENVIRONMENT)
- [ ] Graph API app registration created and consented
- [ ] Key Vault contains all secrets (OpenAI key, Graph secret)
- [ ] SQL Server created with correct admin user
- [ ] Static Web App source connected (GitHub/DevOps)
- [ ] Container Apps have system-assigned managed identities
- [ ] Managed identities have `Container App Contributor` role
- [ ] Resource group naming matches: `rg-{PROJECT_NAME}-{ENVIRONMENT}`
- [ ] All service names follow: `{PROJECT_NAME}-mcp-{SERVICE}-{ENVIRONMENT}`
- [ ] CORS_ORIGINS includes your Static Web App URL
- [ ] Log Analytics workspace created and linked
- [ ] Backup policy set for databases

## Troubleshooting Configuration Issues

**Problem: "Service restart returns 403 (Forbidden)"**
- Check: Orchestrator's managed identity has `Container App Contributor` role on resource group
- Fix: `az role assignment create --assignee $PRINCIPAL_ID --role "Container App Contributor" --resource-group $RG_NAME`

**Problem: "Cannot connect to database"**
- Check: SQL firewall allows Container Apps VNET
- Check: SQL auth user has CONNECT permission
- Fix: Add app service to SQL firewall rules

**Problem: "Graph API returns 403 for Mail.Read"**
- Check: Admin consent granted (not just API permission added)
- Check: App registration ID matches GRAPH_CLIENT_ID env var
- Fix: Azure Portal → API Permissions → Grant admin consent

**Problem: "OpenAI returns 401 (Unauthorized)"**
- Check: AZURE_OPENAI_API_KEY is valid and not expired
- Check: AZURE_OPENAI_ENDPOINT has trailing slash: `https://...openai.azure.com/`
- Check: AZURE_OPENAI_DEPLOYMENT matches actual deployment in Azure
- Fix: Regenerate key in Azure OpenAI resource → Keys → Regenerate

## Next Steps

- **Deploy now:** [[Deployment-Checklist]]
- **Understand architecture:** [[Architecture]]
- **Run in production:** [[Operations]]
