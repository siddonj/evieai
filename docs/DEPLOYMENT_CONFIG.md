# EvieAI Deployment Configuration Guide

## Overview

This guide explains how to configure EvieAI for deployment across multiple client environments. All configuration is driven by environment variables that can be set via `.env` files, Terraform variables, or Container Apps environment configuration.

## Required vs Optional Configuration

### Required for All Deployments
- **AZURE_OPENAI_ENDPOINT**: Azure OpenAI service endpoint
- **AZURE_OPENAI_API_KEY**: Azure OpenAI API key

### Required for Admin Dashboard Service Restart
- **PROJECT_NAME**: Prefix for Azure resource names (default: `aiagent2`)
- **ENVIRONMENT**: Deployment environment name (default: `dev`)
- **RESOURCE_GROUP**: Azure resource group name
- **AZURE_SUBSCRIPTION_ID**: Azure subscription ID (required for Azure SDK approach)

## Environment Variables Reference

### Azure OpenAI
```env
AZURE_OPENAI_ENDPOINT=https://your-openai-name.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-api-key>
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

**How to get values:**
```bash
# After terraform apply:
terraform output -raw openai_endpoint
terraform output -raw openai_api_key
```

### Azure Deployment & Restart Configuration
```env
# Resource naming convention
PROJECT_NAME=aiagent2
ENVIRONMENT=dev
RESOURCE_GROUP=rg-aiagent2-dev
AZURE_SUBSCRIPTION_ID=<your-subscription-id>
```

**How to get subscription ID:**
```bash
# List all subscriptions:
az account list --output table

# Get current subscription ID:
az account show --query id -o tsv
```

### Database Configuration
```env
# Local development (PostgreSQL)
POSTGRES_DB=evieai
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DSN=postgresql://postgres:postgres@postgres:5432/evieai

# Azure PostgreSQL (for production)
POSTGRES_HOST=your-server.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_USER=pgadmin
POSTGRES_PASSWORD=<your-password>
POSTGRES_DSN=postgresql://pgadmin:<password>@your-server.postgres.database.azure.com:5432/evieai?sslmode=require
```

### Authentication & Security
```env
# JWT secret (generate with: openssl rand -hex 32)
JWT_SECRET=<generate-new-value>

# Default admin user (for first-time setup)
DEFAULT_ADMIN_EMAIL=admin@example.com
DEFAULT_ADMIN_PASSWORD=<secure-password>

# Auth database path (local deployments)
AUTH_DB_PATH=./data/evieai_auth.db
```

### Web UI & CORS
```env
# Allowed origins for API requests
# For local dev:
CORS_ORIGINS=http://localhost:5173

# For Azure deployment with custom domain:
CORS_ORIGINS=https://your-domain.com,https://your-ui-url.com
```

### Microsoft Graph (Optional)
```env
AZURE_TENANT_ID=<your-tenant-id>
AZURE_CLIENT_ID=<your-app-id>
AZURE_CLIENT_SECRET=<your-client-secret>
AZURE_USER_ID=<user-object-id>
```

### File Storage
```env
# Local file share root
LOCAL_SHARE_ROOT=./data/files

# Azure Storage (set automatically by Terraform)
AZURE_STORAGE_ACCOUNT=<account-name>
AZURE_STORAGE_KEY=<account-key>
```

## Deployment Scenarios

### Scenario 1: Local Development

```bash
# 1. Copy template
cp .env.example .env

# 2. Fill in required values (at minimum)
# AZURE_OPENAI_ENDPOINT
# AZURE_OPENAI_API_KEY

# 3. Start services
docker-compose up --build
```

**Note:** Service restart functionality will be limited in local dev (no Azure Container Apps to restart).

### Scenario 2: Azure Container Apps (Single Environment)

```bash
# 1. Initialize Terraform
cd terraform
terraform init

# 2. Create terraform.tfvars
cat > terraform.tfvars << EOF
project_name            = "aiagent2"
environment             = "dev"
location                = "eastus"
azure_openai_api_key    = "your-key-here"
azure_openai_endpoint   = "https://your-openai.openai.azure.com/"
jwt_secret              = "$(openssl rand -hex 32)"
default_admin_email     = "admin@example.com"
default_admin_password  = "secure-password"
EOF

# 3. Review and apply
terraform plan
terraform apply

# 4. Verify environment variables are set
terraform output -json | grep -E "PROJECT_NAME|ENVIRONMENT|RESOURCE_GROUP"
```

**Variables automatically set by Terraform:**
- `PROJECT_NAME` → from `var.project_name`
- `ENVIRONMENT` → from `var.environment`
- `RESOURCE_GROUP` → auto-constructed as `rg-{project_name}-{environment}`
- `AZURE_SUBSCRIPTION_ID` → current subscription

### Scenario 3: Multi-Client Deployment

For deploying to multiple client Azure subscriptions:

```bash
# 1. For each client, create a separate terraform.tfvars:
terraform/client_a/terraform.tfvars
terraform/client_b/terraform.tfvars

# Example: client_a/terraform.tfvars
project_name            = "clienta-prop"
environment             = "prod"
location                = "eastus"
azure_openai_api_key    = "client-a-key"
azure_openai_endpoint   = "https://clienta-openai.openai.azure.com/"
# ... other variables

# 2. Deploy each client
cd terraform/client_a
terraform init
terraform apply -auto-approve

cd ../client_b
terraform init
terraform apply -auto-approve
```

**Each deployment will have:**
- Unique resource group: `rg-clienta-prod`, `rg-clientb-prod`
- Unique container apps: `clienta-prop-orchestrator-prod`, etc.
- Unique service restart configuration
- Independent databases and secrets

### Scenario 4: Update Service Restart Configuration

If you need to update restart settings after deployment:

```bash
# Option 1: Update Terraform and apply
terraform apply -var="environment=prod"

# Option 2: Set via Azure Portal (Container Apps → Environment variables)
az containerapp update \
  --name aiagent2-orchestrator-dev \
  --resource-group rg-aiagent2-dev \
  --set-env-vars \
    PROJECT_NAME=aiagent2 \
    ENVIRONMENT=dev \
    RESOURCE_GROUP=rg-aiagent2-dev \
    AZURE_SUBSCRIPTION_ID=<your-subscription-id>

# Option 3: Update .env and redeploy Docker containers
# (for local development or manual deployment)
```

## Environment Variable Validation

The orchestrator validates deployment configuration at startup:

```python
# From orchestrator/app/main.py
PROJECT_NAME = os.getenv("PROJECT_NAME", "aiagent2")          # defaults to aiagent2
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")                  # defaults to dev
RESOURCE_GROUP = os.getenv("RESOURCE_GROUP", f"rg-{PROJECT_NAME}-{ENVIRONMENT}")
AZURE_SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID", "") # must be set for restart
```

**Defaults mean:**
- Service restart works with default naming (common case)
- Custom naming requires explicit configuration
- Missing AZURE_SUBSCRIPTION_ID falls back to Azure CLI

## Troubleshooting Configuration

### Service Restart Not Working

**Symptom:** "Restart" button shows error or is unavailable

**Diagnosis:**
```bash
# Check orchestrator logs
docker logs orchestrator | grep -i restart
# or in Azure:
az containerapp logs show \
  --name aiagent2-orchestrator-dev \
  --resource-group rg-aiagent2-dev

# Verify environment variables are set
az containerapp show \
  --name aiagent2-orchestrator-dev \
  --resource-group rg-aiagent2-dev \
  --query "properties.template.containers[0].env" -o table
```

**Solutions:**
1. Ensure `AZURE_SUBSCRIPTION_ID` is set
2. Verify managed identity has Container App Contributor role
3. Confirm `PROJECT_NAME` and `ENVIRONMENT` match deployed apps
4. Check Azure CLI is available in container image

### Configuration Mismatch

**Symptom:** Restart targets wrong service or fails silently

**Verify naming convention matches:**
```bash
# Expected format: {PROJECT_NAME}-mcp-{SERVICE_NAME}-{ENVIRONMENT}
# Example: aiagent2-mcp-sql-dev

# List all container apps:
az containerapp list -g <RESOURCE_GROUP> --output table

# Verify orchestrator config
docker exec orchestrator env | grep -E "PROJECT_NAME|ENVIRONMENT|RESOURCE_GROUP"
```

## Checklist for Multi-Client Deployment

- [ ] Each client has unique `PROJECT_NAME` and `ENVIRONMENT`
- [ ] `RESOURCE_GROUP` name follows convention: `rg-{project_name}-{environment}`
- [ ] `AZURE_SUBSCRIPTION_ID` set and verified
- [ ] Azure OpenAI credentials copied to each deployment
- [ ] Terraform state stored securely (Azure Storage backend recommended)
- [ ] Managed identities configured with Container App Contributor role
- [ ] `.env` files gitignored (never commit credentials)
- [ ] Container Apps reachable from orchestrator (internal ingress configured)
- [ ] Health checks passing on all services

## Configuration as Code Best Practices

1. **Use Terraform variables** for all deployments
2. **Store secrets in Key Vault**, not in Terraform state
3. **Use managed identities** instead of connection strings
4. **Separate `.tfvars` files** per client/environment
5. **Document custom naming** if deviating from convention
6. **Test restart functionality** post-deployment:
   ```bash
   # Call restart endpoint (requires auth)
   curl -X POST http://orchestrator-url/restart \
     -H "Content-Type: application/json" \
     -d '{"service": "sql"}'
   ```

## Next Steps

- Review [INSTALL.md](./INSTALL.md) for step-by-step setup
- Check [DEPLOYMENT.md](./DEPLOYMENT.md) for CI/CD pipeline configuration
- See [terraform/README.md](../terraform/README.md) for Terraform-specific details
