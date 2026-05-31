# Terraform Landing Zone

This directory contains all Azure infrastructure for the AI Q&A app. It is designed for someone with **no prior Azure experience**.

## What It Provisions

1. **Resource Group** — logical container for all resources
2. **Log Analytics Workspace** — central logging for Container Apps
3. **Azure Container Registry (ACR)** — stores Docker images
4. **Azure Key Vault** — stores all secrets (OpenAI keys, SQL password, Graph credentials)
5. **Azure OpenAI** — GPT-4o deployment
6. **Azure SQL Server + Database** — serverless tier for relational data
7. **Azure PostgreSQL Flexible Server + Database** — operational and analytics workloads
8. **Azure Storage Account + File Share** — cloud file storage for File Share MCP
9. **Azure Container Apps Environment + MCP Apps** — orchestrator (public) + MCP servers (internal), including dashboard views
10. **Azure Static Web App** — hosts the React chat UI

## Prerequisites

- Azure subscription ([create free](https://portal.azure.com))
- Terraform 1.7+ installed
- Azure CLI installed and logged in:
  ```bash
  az login
  az account set --subscription "Your Subscription Name"
  ```

## One-Time Bootstrap: Terraform Backend

Terraform needs a place to store its state file. We use an Azure Storage container.

Run these **once** (they are intentionally outside Terraform to avoid chicken-and-egg):

```bash
# 1. Create a resource group for Terraform state
az group create --name rg-terraform-state --location eastus2

# 2. Create a storage account (name must be globally unique, 3-24 lowercase letters)
az storage account create \
  --name aiqatfstate123 \
  --resource-group rg-terraform-state \
  --location eastus2 \
  --sku Standard_LRS

# 3. Create a container inside the storage account
az storage container create \
  --name tfstate \
  --account-name aiqatfstate123
```

> **Important:** Replace `aiqatfstate123` with your own unique name.

Create a backend config file from the example:

```bash
cp backend.hcl.example backend.hcl
```

Edit `backend.hcl` and set `storage_account_name` and `key` for your environment.

## Configuration

Copy the example variables file and edit it:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
- Set `project_name` (short, alphanumeric, e.g. `aiqa`)
- Set `environment` (`dev` or `prod`)
- Set `location` (e.g. `eastus2`, `swedencentral`, `westus3`)
- Set `sql_admin_password` (strong password, min 8 chars)
- Set `postgres_admin_password` (strong password, min 8 chars)
- Set `target_user_upn` (the O365 user whose mail/files the app will read)
- Set `jwt_secret` (generate with `openssl rand -hex 32`)

## Environment Variables (Automatically Configured by Terraform)

Terraform automatically configures several critical environment variables in the Container Apps, including those needed for the admin dashboard's service restart functionality:

| Variable | Purpose | Set By | Value |
|----------|---------|--------|-------|
| `PROJECT_NAME` | Prefix for all Azure resources | Terraform | `var.project_name` |
| `ENVIRONMENT` | Deployment environment name | Terraform | `var.environment` |
| `RESOURCE_GROUP` | Azure resource group name | Terraform | Auto-constructed from project_name + environment |
| `AZURE_SUBSCRIPTION_ID` | Azure subscription for SDK calls | Terraform | Auto-detected from current context |
| `AZURE_OPENAI_ENDPOINT` | OpenAI service endpoint | Terraform + Key Vault | From `var.azure_openai_endpoint` |
| `AZURE_OPENAI_API_KEY` | OpenAI API key (secret) | Terraform + Key Vault | From `var.azure_openai_api_key` |
| `MCP_*_URL` | MCP service endpoints | Terraform | Auto-constructed from Container App FQDNs |

### What This Means for Multi-Client Deployments

When you run `terraform apply`, all Container Apps are automatically configured with:

```
PROJECT_NAME = aiagent2              # from terraform.tfvars project_name
ENVIRONMENT = dev                    # from terraform.tfvars environment
RESOURCE_GROUP = rg-aiagent2-dev     # auto-constructed
AZURE_SUBSCRIPTION_ID = 82aff681...  # your current subscription
```

**This enables service restart functionality automatically** — the admin dashboard can restart any Container App by name using these variables.

For multi-client deployments:
```
# Client A (terraform/client_a/terraform.tfvars)
project_name = "clienta"
environment = "prod"
# Results in:
# PROJECT_NAME = clienta
# RESOURCE_GROUP = rg-clienta-prod
# Services named: clienta-mcp-sql-prod, clienta-orchestrator-prod, etc.

# Client B (terraform/client_b/terraform.tfvars)
project_name = "clientb"
environment = "staging"
# Results in:
# PROJECT_NAME = clientb
# RESOURCE_GROUP = rg-clientb-staging
# Services named: clientb-mcp-sql-staging, clientb-orchestrator-staging, etc.
```

See [docs/DEPLOYMENT_CONFIG.md](../docs/DEPLOYMENT_CONFIG.md) for detailed environment variable reference and [docs/DEPLOYMENT_CHECKLIST.md](../docs/DEPLOYMENT_CHECKLIST.md) for multi-client setup guide.

## Deploy

```bash
cd terraform

# Initialize Terraform (downloads providers and configures backend)
terraform init -backend-config=backend.hcl

# One-time: register Container Apps resource provider if your subscription is not registered yet
az provider register --namespace Microsoft.App --wait

# Preview changes
terraform plan

# Create everything (takes ~10–15 minutes)
terraform apply

# Destroy everything when finished
terraform destroy
```

### If `terraform apply` fails with region or registration errors

- `MissingSubscriptionRegistration: Microsoft.App`
  Run:
  ```bash
  az provider register --namespace Microsoft.App --wait
  ```
- `ProvisioningDisabled` when creating Azure SQL Server
  Your subscription cannot provision SQL in that region. Change `location` in `terraform.tfvars` to another supported value (for this repo: `westus3` or `swedencentral`) and re-run `terraform plan` then `terraform apply`.

## After First Deploy

Terraform outputs the following values. Save them — you will need them for local development and GitHub Actions:

- `orchestrator_url` — public API endpoint
- `ui_default_hostname` — chat UI URL
- `acr_login_server` — Docker registry URL
- `key_vault_name` — secret storage
- `openai_endpoint` — Azure OpenAI base URL
- `sql_connection_string` — ADO.NET connection string for DAB
- `postgres_server_fqdn` — PostgreSQL host
- `postgres_database_name` — PostgreSQL database name
- `postgres_dsn` — PostgreSQL DSN (sensitive)

## Day-2 Deployments (Terraform-First)

For client environments, treat Terraform as the source of truth for runtime image versioning.

### Promote a new orchestrator build

1. Build and push a new image to ACR:
  ```bash
  az acr build -r <acr-name> -t orchestrator:latest -f orchestrator/Dockerfile .
  ```
2. Capture the pushed digest from build output (`sha256:...`).
3. Update `orchestrator_image_digest` in `terraform.tfvars`.
4. Apply with Terraform:
  ```bash
  terraform plan
  terraform apply
  ```

This prevents configuration drift from manual `az containerapp update` commands.

### Static Web App note

Terraform provisions the Static Web App resource, but app content deployment still happens via CI/CD or SWA deployment tooling. Keep that deployment step in your release pipeline, and keep infrastructure changes in Terraform.

### Authenticating the Graph API App (One-Time Manual Step)

Terraform creates the Entra ID app registration, but **admin consent for Microsoft Graph permissions must be granted in the Azure portal** by a Global Administrator:

1. Go to [portal.azure.com](https://portal.azure.com) → Microsoft Entra ID → App registrations
2. Find your app (named `{project_name}-graph-app-{environment}`)
3. API permissions → Grant admin consent for [tenant]
4. Confirm green checkmarks next to `Mail.Read`, `Files.Read.All`, `User.Read.All`

Without this step, the Mail and OneDrive MCP servers will return `403 Forbidden`.

## Architecture

```
┌─────────────────────────────────────────────┐
│           Azure Container Apps Env            │
│  ┌─────────────┐                              │
│  │ Orchestrator│ ←── Public ingress (HTTPS)   │
│  │   :8000     │                              │
│  └──────┬──────┘                              │
│         │                                     │
│  ┌──────┴──────┬──────────┬──────────┐        │
│  │ SQL MCP     │ File MCP │ Mail MCP │ OneDrive│
│  │ (DAB):5000  │ :8001    │ :8002    │ :8003   │
│  │ Internal    │ Internal │ Internal │ Internal│
│  └─────────────┴──────────┴──────────┴─────────┘│
└─────────────────────────────────────────────┘
         │
    ┌────┴────┐
    ▼         ▼
 Key Vault  Azure OpenAI
 (secrets)   (GPT-4o)
    │
    ▼
 SQL DB    Storage    Entra ID App
```

## Costs

See `PLAN.md` Section 10.12 for a detailed cost breakdown. At rest with `--min-replicas 0` on all Container Apps, expect **under $5/day for development**.

## Security Notes

- **Secrets are managed centrally in Key Vault and container secrets.** Container Apps reference secrets via `secret_name`; Terraform injects secret values from Key Vault and sensitive variables.
- **Container image pulls use managed identity.** Each Container App has `AcrPull` on ACR; registry admin credentials are not used for runtime pulls.
- **Internal ingress only** for all MCP servers. They cannot be reached from the internet.
- **SQL Server firewall** blocks all IPs except Azure services (required for Container Apps).
- **PostgreSQL firewall** blocks all IPs except Azure services (required for Container Apps and trusted Azure workloads).
- **Key Vault** uses RBAC (not legacy access policies) and grants only `Secrets User` role to specific managed identities.
