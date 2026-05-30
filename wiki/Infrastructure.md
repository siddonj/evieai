# Infrastructure & Terraform

> Infrastructure as Code setup, management, and multi-client deployment

## Terraform Overview

EvieAI uses Terraform to provision all Azure infrastructure automatically. No manual resource creation needed!

**Benefits:**
- ✅ Reproducible deployments
- ✅ Version control for infrastructure
- ✅ Multi-client isolation
- ✅ Automatic resource naming
- ✅ Secrets management integration
- ✅ Infrastructure documentation

---

## File Structure

```
terraform/
├─ main.tf              # Resource definitions
├─ variables.tf         # Input variables
├─ outputs.tf          # Output values (URLs, names, etc.)
├─ providers.tf        # Azure provider config
├─ terraform.tfvars    # Values for your deployment
├─ terraform.tfvars.example  # Template
└─ README.md           # Detailed Terraform guide
```

---

## Key Variables (terraform.tfvars)

```hcl
# terraform.tfvars

# Basic Configuration
location                = "eastus"          # Azure region
resource_group_prefix   = "rg"             # Resource group name prefix
app_name                = "acme-corp"       # YOUR CLIENT NAME (no spaces/underscores)
environment             = "prod"            # dev, staging, prod

# OpenAI
openai_capacity         = 100               # Requests per minute (TPM)

# Database
sql_admin_username      = "sqladmin"        # SQL admin user
enable_postgres         = false             # Include PostgreSQL for event logs?

# Features
enable_teams_sso        = true              # Enable Teams single sign-on
enable_approvals        = true              # Enable approval workflow

# Monitoring
log_retention_days      = 90                # How long to keep logs

# Scaling
orchestrator_min_replicas = 1
orchestrator_max_replicas = 5
mcp_min_replicas          = 1
mcp_max_replicas          = 5
```

---

## Creating terraform.tfvars

### For Single Client

```bash
cat > terraform/terraform.tfvars << 'EOF'
location                = "eastus"
resource_group_prefix   = "rg"
app_name                = "mycompany"       # ← Change to your company
environment             = "prod"
openai_capacity         = 100
sql_admin_username      = "sqladmin"
enable_teams_sso        = true
enable_approvals        = true
log_retention_days      = 90
EOF
```

### For Multiple Clients (Separate tfvars Files)

**Client 1 (Acme Corp - Production):**
```bash
cat > terraform/tfvars/acme-prod.tfvars << 'EOF'
location                = "eastus"
app_name                = "acme-corp"
environment             = "prod"
openai_capacity         = 100
sql_admin_username      = "sqladmin"
enable_teams_sso        = true
enable_approvals        = true
log_retention_days      = 90
EOF
```

**Client 2 (Beta Corp - Staging):**
```bash
cat > terraform/tfvars/beta-staging.tfvars << 'EOF'
location                = "eastus"
app_name                = "beta-corp"
environment             = "staging"
openai_capacity         = 50
sql_admin_username      = "sqladmin"
enable_teams_sso        = false
enable_approvals        = true
log_retention_days      = 30
EOF
```

---

## Terraform Workflow

### Step 1: Initialize Terraform

```bash
cd terraform

# Configure backend (where state is stored)
terraform init \
  -backend-config="resource_group_name=rg-terraform-state" \
  -backend-config="storage_account_name=tfstate12345" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=evieai.tfstate"
```

**What it does:**
- Downloads provider plugins
- Sets up backend storage
- Creates `.terraform/` directory

### Step 2: Validate Configuration

```bash
# Format check
terraform fmt -check

# Syntax validation
terraform validate
```

### Step 3: Plan Deployment

```bash
# See what will be created/changed
terraform plan -out=plan.tfplan

# Review output (should show ~20 resources being created)
```

### Step 4: Apply (Create Resources)

```bash
# Actually create the resources
terraform apply plan.tfplan

# Takes 10–15 minutes
```

### Step 5: Capture Outputs

```bash
# Save important values for later
terraform output

# Individual outputs:
terraform output -raw orchestrator_url
terraform output -raw key_vault_name
terraform output -raw sql_server_name
terraform output -raw graph_app_client_id
```

---

## Multi-Client Deployment

Deploy multiple clients to the same subscription with complete isolation:

### Scenario: Two Clients, Same Subscription

**Directory structure:**
```
terraform/
├─ main.tf
├─ variables.tf
├─ outputs.tf
├─ terraform.tfvars       # (ignored by .gitignore)
├─ tfvars/
│  ├─ acme-prod.tfvars
│  ├─ acme-staging.tfvars
│  ├─ beta-prod.tfvars
│  └─ beta-staging.tfvars
└─ .terraform/
   ├─ evieai-acme-prod.tfstate
   ├─ evieai-acme-staging.tfstate
   ├─ evieai-beta-prod.tfstate
   └─ evieai-beta-staging.tfstate
```

### Deploy Client A (Production)

```bash
cd terraform

# Plan
terraform plan \
  -var-file="tfvars/acme-prod.tfvars" \
  -out=plan-acme-prod.tfplan

# Apply
terraform apply plan-acme-prod.tfplan

# Outputs saved to:
# rg-acme-corp-prod
# acme-corp-orchestrator-prod
# acme-corp-mcp-*-prod
```

### Deploy Client B (Staging)

```bash
# Plan
terraform plan \
  -var-file="tfvars/beta-staging.tfvars" \
  -out=plan-beta-staging.tfplan

# Apply
terraform apply plan-beta-staging.tfplan

# Outputs saved to:
# rg-beta-corp-staging
# beta-corp-orchestrator-staging
# beta-corp-mcp-*-staging
```

### Result

✅ Two completely isolated deployments:
```
Subscription
├─ rg-acme-corp-prod/
│  ├─ acme-corp-orchestrator-prod
│  ├─ acme-corp-mcp-sql-prod
│  ├─ acme-corp-mcp-mail-prod
│  └─ ... (other MCPs)
│
└─ rg-beta-corp-staging/
   ├─ beta-corp-orchestrator-staging
   ├─ beta-corp-mcp-sql-staging
   ├─ beta-corp-mcp-mail-staging
   └─ ... (other MCPs)
```

Each client:
- ✅ Has separate resource group
- ✅ Has separate Container Apps
- ✅ Has separate database
- ✅ Has separate secrets in Key Vault
- ✅ Service restart only affects own services
- ✅ Logs isolated in separate Log Analytics tables

---

## Managing Terraform State

### Backup State

```bash
# Manual backup (before major changes)
terraform state pull > terraform.tfstate.backup

# Stored backup (in Azure Storage with versioning)
# Automatic via backend storage account
```

### View State

```bash
# List all resources in state
terraform state list

# Show specific resource config
terraform state show aws_resource_group.main
```

### Destroy Infrastructure

```bash
# WARNING: This deletes all resources!

terraform destroy \
  -var-file="tfvars/acme-prod.tfvars" \
  --auto-approve
```

---

## Updating Infrastructure

### Add New Environment Variable

**1. Update Terraform:**
```hcl
# main.tf - in Container App definition
env {
  name  = "NEW_VARIABLE"
  value = "some-value"
}
```

**2. Plan & Apply:**
```bash
terraform plan
terraform apply
```

**3. Resources updated automatically**

### Scale Replicas

**1. Update tfvars:**
```hcl
orchestrator_max_replicas = 10  # Instead of 5
```

**2. Plan & Apply:**
```bash
terraform plan -out=plan.tfplan
terraform apply plan.tfplan
```

### Change Resource Size

**1. Update Terraform:**
```hcl
# main.tf
cpu    = "1.0"      # Instead of 0.5
memory = "2.0Gi"    # Instead of 1.0Gi
```

**2. Plan & Apply:**
```bash
terraform apply
```

---

## Troubleshooting Terraform

### "Invalid backend configuration"

```bash
# Verify backend storage account exists
STORAGE="tfstate12345"
az storage account show --name "$STORAGE"

# If not found, create it
az group create --name "rg-terraform-state" --location "eastus"
az storage account create \
  --name "$STORAGE" \
  --resource-group "rg-terraform-state" \
  --sku Standard_LRS

# Create container
az storage container create \
  --account-name "$STORAGE" \
  --name "tfstate"

# Retry init
terraform init -backend-config="..."
```

### "Resource already exists"

```bash
# If resource was manually created outside Terraform:
terraform import azure_resource_group.rg /subscriptions/{sub}/resourceGroups/{rg-name}
```

### "Permission denied"

```bash
# Verify Azure CLI is authenticated
az account show

# If not, login
az login

# Verify you have Contributor role
az role assignment list --assignee $(az account show --query "user.name" -o tsv)
```

### Plan Shows Unwanted Changes

```bash
# Review terraform.tfvars file
cat terraform/terraform.tfvars

# Ensure all values are as intended
# If values are correct, changes may be from provider updates
# Run: terraform apply (to update)
```

---

## Terraform Best Practices

### 1. Use .gitignore

```bash
# .gitignore
terraform.tfvars         # Never commit secrets
tfvars/*.tfvars         # Never commit client-specific configs
.terraform/
*.tfstate
*.tfstate.*
.terraform.lock.hcl     # Commit this (dependency lock)
```

### 2. Code Review Before Apply

```bash
# Always review plan before applying
terraform plan -out=plan.tfplan

# Read output carefully
# Look for destructive changes (anything marked "must replace")
```

### 3. Use Separate Backends Per Client

```bash
# Different state files = different clients isolated
# Store state in separate Storage containers or accounts
```

### 4. Tag All Resources

```hcl
# Add to all resources
tags = {
  client      = var.app_name
  environment = var.environment
  managed_by  = "terraform"
  created_at  = timestamp()
}
```

### 5. Regular State Cleanup

```bash
# Remove stale resources
terraform state rm path/to/resource

# Or in Terraform code, remove resource block and re-apply
```

---

## Terraform Outputs

Useful values created by Terraform:

```bash
# Orchestrator endpoint
terraform output orchestrator_url
# Output: https://acme-corp-orchestrator-prod.yellowpond-123.eastus.azurecontainerapps.io

# Web UI URL
terraform output ui_default_hostname
# Output: acme-corp-ui-prod.azurestaticapps.net

# Key Vault name
terraform output key_vault_name
# Output: kv-acme-corp-prod

# SQL Server
terraform output sql_server_name
# Output: acme-corp-sql-prod

# Graph App ID
terraform output graph_app_client_id
# Output: 00000000-0000-0000-0000-000000000000

# Container Registry
terraform output acr_login_server
# Output: aiagent2acrdev.azurecr.io
```

---

## Cost Estimation

Before deploying, estimate costs:

```bash
# View estimated costs (if using Terraform Cloud)
terraform plan -json | jq '.resource_changes[] | select(.change.actions != ["no-op"])'

# Manual calculation
# Container Apps: ~$45–90/month per client
# Azure OpenAI: ~$60–120/month per client
# SQL Serverless: ~$15–35/month per client
# Storage + Vault + Logs: ~$20–30/month per client
# ─────────────────────────────────────────────────
# Total: ~$140–275/month per client
```

---

## Next Steps

- **Deploy:** [[Deployment-Checklist]]
- **Understand architecture:** [[Architecture]]
- **Troubleshoot issues:** [[Troubleshooting]]
