# EvieAI Multi-Client Deployment Checklist

Quick reference for deploying EvieAI to a new client environment.

## Pre-Deployment

### Azure Setup
- [ ] Azure subscription created and accessible
- [ ] Azure OpenAI service deployed with GPT-4o model
- [ ] Resource group created (or will be created by Terraform)
- [ ] Service principal/managed identity configured for Terraform
- [ ] Subscription ID obtained: `az account show --query id -o tsv`

### Client Information Gathered
- [ ] Client name/identifier (e.g., "acme-corp", "client-a")
- [ ] Deployment environment (dev/staging/prod)
- [ ] Required region (eastus, westus, etc.)
- [ ] Admin email address
- [ ] Admin initial password (or policy for password reset)

## Configuration Setup

### Step 1: Prepare Terraform Variables

```bash
# Create client-specific directory
mkdir -p terraform/clients/client-name

# Copy template
cp terraform.tfvars.example terraform/clients/client-name/terraform.tfvars
```

### Step 2: Fill terraform.tfvars

```hcl
# Required
project_name            = "clientname"           # No spaces, lowercase
environment             = "dev"                  # dev|staging|prod
location                = "eastus"               # Azure region
azure_openai_api_key    = "your-key-here"        # From Azure portal
azure_openai_endpoint   = "https://...openai.azure.com/"

# Security
jwt_secret              = "generate-new"         # openssl rand -hex 32
default_admin_email     = "admin@client.com"
default_admin_password  = "Tmp!123456"

# Optional customizations
ui_custom_domain        = null                   # Or "ui.client.com"
container_app_max_replicas = 3
tags = {
  client = "client-name"
  environment = "dev"
  managed_by = "terraform"
}
```

### Step 3: Verify Environment Variables

```bash
# Confirm these will be set by Terraform:
echo "PROJECT_NAME: clientname"
echo "ENVIRONMENT: dev"
echo "RESOURCE_GROUP: rg-clientname-dev"
echo "AZURE_SUBSCRIPTION_ID: $(az account show --query id -o tsv)"
```

## Deployment

### Step 1: Initialize Terraform
```bash
cd terraform/clients/client-name
terraform init -upgrade
```

### Step 2: Plan and Review
```bash
terraform plan -out=tfplan

# Review output - verify:
# - Resource group name matches convention
# - Container apps named correctly: {PROJECT_NAME}-{SERVICE}-{ENVIRONMENT}
# - All services configured with environment variables
```

### Step 3: Apply Configuration
```bash
terraform apply tfplan

# Wait for completion (10-15 minutes)
# Monitor in Azure Portal: Container Apps
```

### Step 4: Verify Deployment

```bash
# Get outputs
terraform output -json

# Check orchestrator is running
ORCH_URL=$(terraform output -raw orchestrator_url)
curl $ORCH_URL/health

# Test health endpoint (service status)
curl $ORCH_URL/ready | jq '.'

# Verify restart configuration is set
az containerapp show \
  --name <PROJECT_NAME>-orchestrator-<ENVIRONMENT> \
  --resource-group <RESOURCE_GROUP> \
  --query "properties.template.containers[0].env[?name=='PROJECT_NAME'].value" \
  -o tsv
```

### Step 5: Access Admin Dashboard

```bash
# Get UI URL
STATIC_WEB_APP_URL=$(terraform output -raw ui_default_hostname)

# Open in browser: https://{STATIC_WEB_APP_URL}
# Navigate to: Settings → Admin Dashboard
# Verify service health and restart buttons
```

## Post-Deployment Validation

### Service Health

- [ ] All 10 services show as "Online" (🟢) in Admin Dashboard
- [ ] Health percentage is at least 90%
- [ ] No error messages in service details

### Restart Functionality

- [ ] Click 🔄 button on any service (e.g., SQL)
- [ ] Button shows ⏳ loading state
- [ ] Status shows "Restart initiated ✓"
- [ ] Service restarts and comes back online

### Database Connectivity

```bash
# Test PostgreSQL access
az containerapp exec \
  --name <PROJECT_NAME>-mcp-postgres-<ENVIRONMENT> \
  --resource-group <RESOURCE_GROUP> \
  --command psql -h $POSTGRES_HOST -U $POSTGRES_USER -d evieai -c "SELECT 1"
```

### Logging & Monitoring

```bash
# View recent logs
az containerapp logs show \
  --name <PROJECT_NAME>-orchestrator-<ENVIRONMENT> \
  --resource-group <RESOURCE_GROUP> \
  --follow

# Check for restart errors
az containerapp logs show \
  --name <PROJECT_NAME>-orchestrator-<ENVIRONMENT> \
  --resource-group <RESOURCE_GROUP> | grep -i restart
```

## Troubleshooting Quick Reference

| Issue | Solution |
|-------|----------|
| Container app not reachable | Check ingress configuration, verify CORS_ORIGINS |
| Restart button shows error | Verify AZURE_SUBSCRIPTION_ID set, check managed identity role |
| Services failing health check | Check MCP_*_URL environment variables, verify internal ingress |
| PostgreSQL connection failed | Verify POSTGRES_DSN, check firewall rules for Azure PostgreSQL |
| OpenAI failures | Verify endpoint and key, check quota/limits in Azure portal |

## Configuration Files Location

For multi-client deployment:

```
evieai/
├── terraform/
│   ├── main.tf                    # Shared across all clients
│   ├── clients/
│   │   ├── client-a/
│   │   │   └── terraform.tfvars   # Client A configuration
│   │   └── client-b/
│   │       └── terraform.tfvars   # Client B configuration
│   └── README.md                  # Terraform-specific docs
├── docs/
│   ├── DEPLOYMENT_CONFIG.md       # This file - full reference
│   ├── INSTALL.md                 # Step-by-step installation
│   └── DEPLOYMENT.md              # CI/CD and production deployment
└── .env.example                   # Local development template
```

## Environment Variable Summary Table

| Variable | Local Dev | Azure | Required | Default | Source |
|----------|-----------|-------|----------|---------|--------|
| PROJECT_NAME | ✓ | ✓ | No | aiagent2 | .env or terraform |
| ENVIRONMENT | ✓ | ✓ | No | dev | .env or terraform |
| RESOURCE_GROUP | ✗ | ✓ | Yes (Azure) | rg-{PROJECT_NAME}-{ENVIRONMENT} | terraform auto |
| AZURE_SUBSCRIPTION_ID | Optional | ✓ | Yes | (none) | terraform auto |
| AZURE_OPENAI_ENDPOINT | ✓ | ✓ | Yes | (none) | terraform/Key Vault |
| AZURE_OPENAI_API_KEY | ✓ | ✓ | Yes | (none) | terraform/Key Vault |

## Commands by Scenario

### List all client deployments
```bash
az containerapp list --resource-group rg-* --output table
```

### Check specific client's restart config
```bash
CLIENT=acme
ENV=prod
az containerapp show -n ${CLIENT}-orchestrator-${ENV} -g rg-${CLIENT}-${ENV} \
  --query "properties.template.containers[0].env" -o table
```

### Update restart config without Terraform
```bash
az containerapp update \
  -n aiagent2-orchestrator-dev \
  -g rg-aiagent2-dev \
  --set-env-vars \
    PROJECT_NAME=aiagent2 \
    ENVIRONMENT=dev \
    RESOURCE_GROUP=rg-aiagent2-dev \
    AZURE_SUBSCRIPTION_ID=12345678-1234-1234-1234-123456789012
```

### Monitor deployment progress
```bash
WATCH="watch -n 5"  # Linux/Mac
# On Windows: use PowerShell -or- refresh manually
az containerapp list --resource-group rg-clientname-dev --output table
```

## Contact & Support

For issues or questions during deployment:

1. Check [DEPLOYMENT_CONFIG.md](./DEPLOYMENT_CONFIG.md) for detailed reference
2. Review [terraform/README.md](../terraform/README.md) for Terraform specifics
3. Check orchestrator logs: `az containerapp logs show ...`
4. Verify all environment variables are set correctly

---

**Last Updated:** 2026-05-29  
**EvieAI Version:** 1.0.0
