# Terraform Landing Zone

This directory contains all Azure infrastructure for the AI Q&A app. It is designed for someone with **no prior Azure experience**.

## What It Provisions

1. **Resource Group** — logical container for all resources
2. **Log Analytics Workspace** — central logging for Container Apps
3. **Azure Container Registry (ACR)** — stores Docker images
4. **Azure Key Vault** — stores all secrets (OpenAI keys, SQL password, Graph credentials)
5. **Azure OpenAI** — GPT-4o deployment
6. **Azure SQL Server + Database** — serverless tier for relational data
7. **Azure Storage Account + File Share** — cloud file storage for File Share MCP
8. **Azure Container Apps Environment + 5 Apps** — orchestrator (public) + 4 MCP servers (internal)
9. **Azure Static Web App** — hosts the React chat UI

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
- Set `target_user_upn` (the O365 user whose mail/files the app will read)

## Deploy

```bash
cd terraform

# Initialize Terraform (downloads providers and configures backend)
terraform init

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

- `MANIFEST_UNKNOWN` when creating Container Apps
  The custom Docker images (`mcp-files`, `mcp-mail`, `mcp-onedrive`, `orchestrator`) have not been pushed to ACR yet. The Terraform config currently uses `mcr.microsoft.com/azuredocs/containerapps-helloworld:latest` as a placeholder so infrastructure provisioning can complete. Once you have built and pushed the real images, update the four `image` lines in `main.tf` (search for `TODO: replace placeholder`) from the placeholder back to:
  ```
  ${azurerm_container_registry.main.login_server}/mcp-files:latest
  ${azurerm_container_registry.main.login_server}/mcp-mail:latest
  ${azurerm_container_registry.main.login_server}/mcp-onedrive:latest
  ${azurerm_container_registry.main.login_server}/orchestrator:latest
  ```
  Then re-run `terraform apply` to roll out the new revisions.

## After First Deploy

Terraform outputs the following values. Save them — you will need them for local development and GitHub Actions:

- `orchestrator_url` — public API endpoint
- `ui_default_hostname` — chat UI URL
- `acr_login_server` — Docker registry URL
- `key_vault_name` — secret storage
- `openai_endpoint` — Azure OpenAI base URL
- `sql_connection_string` — ADO.NET connection string for DAB

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

- **No secrets in environment variables.** Container Apps use `secretref:` syntax that resolves secrets from Key Vault at runtime via managed identity.
- **Internal ingress only** for all MCP servers. They cannot be reached from the internet.
- **SQL Server firewall** blocks all IPs except Azure services (required for Container Apps).
- **Key Vault** uses RBAC (not legacy access policies) and grants only `Secrets User` role to specific managed identities.
