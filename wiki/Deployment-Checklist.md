# Deployment Checklist

> Step-by-step guide to deploy EvieAI to Azure

## Pre-Deployment (Day 0)

### Prerequisites
- [ ] Azure subscription with Owner/Contributor role
- [ ] Terraform installed (`terraform version` shows v1.5+)
- [ ] Azure CLI installed (`az --version` shows v2.50+)
- [ ] Git credentials configured (`git config --list`)
- [ ] Docker Desktop running (for local testing)

### Secrets Collection
Gather these values before starting:

- [ ] Azure OpenAI endpoint: `https://_____.openai.azure.com/`
- [ ] Azure OpenAI API key: `sk-_____`
- [ ] Azure OpenAI deployment name: (e.g., `gpt-4o`)
- [ ] Azure subscription ID: (36-char UUID from `az account show`)
- [ ] Client name for PROJECT_NAME: (e.g., `acme-corp`)
- [ ] Deployment environment: (e.g., `prod`, `staging`, `dev`)

### Terraform Setup

```bash
cd terraform

# Initialize backend
terraform init \
  -backend-config="resource_group_name=rg-terraform-state" \
  -backend-config="storage_account_name=tfstate12345" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=evieai.tfstate"

# Validate configuration
terraform fmt -check && terraform validate
```

**If this fails:**
- [ ] Check backend storage account exists
- [ ] Verify you have Storage Blob Data Contributor role
- [ ] Check Azure CLI is authenticated: `az account show`

---

## Phase 1: Infrastructure Deployment (10–15 minutes)

### Step 1.1: Create terraform.tfvars

```bash
cat > terraform/terraform.tfvars << 'EOF'
location                = "eastus"
resource_group_prefix   = "rg"
app_name                = "acme-corp"        # ← Change to your client name
environment             = "prod"             # ← Change to your environment
openai_capacity         = 100
sql_admin_username      = "sqladmin"
enable_teams_sso        = true
enable_approvals        = true
log_retention_days      = 90
EOF
```

- [ ] File created with correct values
- [ ] PROJECT_NAME matches your client: `acme-corp`
- [ ] ENVIRONMENT matches deployment stage: `prod`

### Step 1.2: Plan Terraform

```bash
cd terraform
terraform plan -out=plan.tfplan
```

Review output. Expected resources:
- 1 Resource Group (`rg-acme-corp-prod`)
- 1 Azure OpenAI account
- 1 SQL Database
- 1 Container Registry
- 9 Container Apps (orchestrator + 8 MCPs)
- 1 Storage Account
- 1 Key Vault
- 1 Static Web App
- 1 Log Analytics workspace

- [ ] Plan shows no errors
- [ ] Resource count matches (~20 total)
- [ ] No warnings about deprecated APIs

### Step 1.3: Apply Terraform

```bash
terraform apply plan.tfplan
```

⏱️ **Expected time:** 10–15 minutes

- [ ] All resources created successfully
- [ ] No failed deployments in output
- [ ] Terraform shows outputs (orchestrator_url, etc.)

### Step 1.4: Capture Terraform Outputs

```bash
# Save for later steps
terraform output -raw orchestrator_url > /tmp/orch_url.txt
terraform output -raw key_vault_name > /tmp/kv_name.txt
terraform output -raw sql_server_name > /tmp/sql_server.txt
```

Write down these values:
- [ ] **Orchestrator URL:** (from `orchestrator_url` output)
- [ ] **Key Vault Name:** (from `key_vault_name` output)
- [ ] **SQL Server:** (from `sql_server_name` output)
- [ ] **App Registration ID:** (from `graph_app_client_id` output)

---

## Phase 2: Secrets Configuration (5 minutes)

### Step 2.1: Set OpenAI API Key in Key Vault

```bash
KV_NAME=$(terraform output -raw key_vault_name)

az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "openai-api-key" \
  --value "sk-YOUR_KEY_HERE"
```

- [ ] Secret set successfully (shows "created")
- [ ] No permission errors

### Step 2.2: Set Graph API Secret (if using Email/OneDrive)

If you plan to enable email or OneDrive integration:

```bash
az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "graph-client-secret" \
  --value "YOUR_SECRET_HERE"
```

- [ ] Secret set successfully
- [ ] Value copied from Entra ID app registration

---

## Phase 3: Grant Admin Consent for Graph API (5 minutes)

### Step 3.1: Open Azure Portal

1. Navigate to: **Azure Portal → Entra ID → App Registrations**
2. Search for: `{app_name}-graph` (e.g., `acme-corp-graph`)
3. Click on it

- [ ] App found in portal

### Step 3.2: Grant Admin Consent

1. Click **API Permissions** (left sidebar)
2. Look for button **"Grant admin consent for [Tenant]"**
3. Click button → Confirm in popup

- [ ] Button clicked and confirmed
- [ ] Status shows green checkmarks next to Mail.Read and Files.Read.All

**Note:** Requires Global Admin role. If you don't have it, contact your admin.

---

## Phase 4: Application Deployment (10 minutes)

### Step 4.1: Build and Push Docker Images

```bash
# Set variables
REGISTRY=$(terraform output -raw acr_login_server)
az acr login --name aiagent2acrdev

# Build orchestrator
az acr build \
  --registry aiagent2acrdev \
  --image orchestrator:latest \
  --file orchestrator/Dockerfile .

# Build all MCPs
for service in sql file_share o365_mail onedrive memory knowledge_base document_generation analytics dashboard; do
  az acr build \
    --registry aiagent2acrdev \
    --image mcp-$service:latest \
    --file mcp_servers/$service/Dockerfile .
done

# Build web UI
az acr build \
  --registry aiagent2acrdev \
  --image web-ui:latest \
  --file web_ui/Dockerfile .
```

⏱️ **Expected time:** 5–10 minutes (first build slower)

- [ ] Orchestrator image pushed: `orchestrator:latest`
- [ ] All 9 MCP images pushed
- [ ] Web UI image pushed: `web-ui:latest`
- [ ] No ACR authentication errors

### Step 4.2: Verify Container Apps

```bash
RG=$(terraform output -raw resource_group_name)
az containerapp list --resource-group "$RG" -o table
```

Should see:
- [ ] `{app_name}-orchestrator-{environment}` (public ingress)
- [ ] `{app_name}-mcp-sql-{environment}` (internal ingress)
- [ ] `{app_name}-mcp-file-share-{environment}` (internal ingress)
- [ ] `{app_name}-mcp-o365-mail-{environment}` (internal ingress)
- [ ] ... (other MCPs)

---

## Phase 5: Health Verification (5 minutes)

### Step 5.1: Check Orchestrator Health

```bash
ORCH_URL=$(terraform output -raw orchestrator_url)

# Health check
curl -s "$ORCH_URL/health" | jq .

# Readiness check
curl -s "$ORCH_URL/ready" | jq .
```

Expected response (all `true`):
```json
{
  "status": "healthy",
  "dependencies": {
    "openai": true,
    "database": true,
    "graph": true,
    "vault": true
  }
}
```

- [ ] `/health` returns 200
- [ ] `/ready` returns 200
- [ ] All dependencies show `true`

**If `/ready` shows any dependency as `false`:**
- [ ] Check logs: `az containerapp logs show --name {app-name} -g {rg}`
- [ ] Verify environment variables: `az containerapp show --name {app-name} -g {rg} --query "properties.template.containers[0].env"`
- [ ] Retry in 30 seconds (Container App may still be starting)

### Step 5.2: Test Admin Dashboard

```bash
UI_URL=$(terraform output -raw ui_default_hostname)
echo "Open browser to: https://$UI_URL"
```

- [ ] Browser opens to EvieAI chat interface
- [ ] Login page works (if Teams SSO enabled)
- [ ] Admin dashboard accessible at `/admin`

---

## Phase 6: Post-Deployment Verification (10 minutes)

### Step 6.1: Service Restart Test

**From Admin Dashboard:**
1. Navigate to https://{ui_url}/admin
2. Find "SQL MCP" service card
3. Click "Restart" button
4. Wait for "Service restarted" message

- [ ] Button click succeeds
- [ ] Status shows green (restarted)
- [ ] No error messages

**From CLI (alternative):**
```bash
ORCH_URL=$(terraform output -raw orchestrator_url)

curl -X POST "$ORCH_URL/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}'
```

Expected response:
```json
{
  "status": "success",
  "service": "sql",
  "timestamp": "2026-05-29T14:32:45Z",
  "message": "Service restarted successfully"
}
```

- [ ] Endpoint responds with 200
- [ ] Status is "success"
- [ ] Timestamp recorded

### Step 6.2: Chat Test

1. Open https://{ui_url}
2. Type: `"What's your current status?"`
3. Wait for response

Expected: AI responds with status message

- [ ] Chat interface responsive
- [ ] Response appears within 5 seconds
- [ ] No JavaScript errors in browser console

### Step 6.3: Monitoring Setup

```bash
RG=$(terraform output -raw resource_group_name)

# Create alert rule for service restarts
az monitor metrics alert create \
  --name "EvieAI Service Restart Alert" \
  --resource-group "$RG" \
  --scopes "/subscriptions/{subscription-id}/resourcegroups/$RG" \
  --condition "total RestartCount > 5" \
  --window-size 1h \
  --evaluation-frequency 15m
```

- [ ] Alert rule created
- [ ] Alert will trigger if >5 restarts/hour

---

## Phase 7: Multi-Client Deployment (if applicable)

### Step 7.1: Deploy Second Client

```bash
# Create new tfvars for Client B
cat > terraform/terraform.prod-client-b.tfvars << 'EOF'
location                = "eastus"
resource_group_prefix   = "rg"
app_name                = "beta-corp"       # ← Different client
environment             = "prod"
openai_capacity         = 100
sql_admin_username      = "sqladmin"
enable_teams_sso        = true
enable_approvals        = true
log_retention_days      = 90
EOF

# Plan and apply with separate state
terraform plan \
  -var-file="terraform.prod-client-b.tfvars" \
  -out=plan-client-b.tfplan

terraform apply plan-client-b.tfplan
```

- [ ] Second client deployed to separate resource group
- [ ] Resource names use `beta-corp` prefix
- [ ] Orchestrator restarts only `beta-corp-*` services

---

## Phase 8: Final Checklist

### Security
- [ ] Key Vault contains all secrets (OpenAI key, Graph secret)
- [ ] Managed identities have correct roles (Container App Contributor)
- [ ] Storage account has firewall rules (if applicable)
- [ ] Database has minimal permissions (read-only user for queries)

### Operations
- [ ] Health endpoints working (`/health`, `/ready`)
- [ ] Service restart tested and working
- [ ] Admin dashboard accessible
- [ ] Chat tested with sample question
- [ ] Alert rules created for monitoring

### Documentation
- [ ] Terraform outputs documented
- [ ] Client name and environment recorded: `{app_name}-{environment}`
- [ ] Key Vault name noted: (for secrets rotation)
- [ ] Admin contact assigned for Graph API consent
- [ ] Runbook created for your team (see [[Operations]])

---

## Troubleshooting Deployment

### Container Apps not starting?
```bash
# Check logs
az containerapp logs show \
  --name {app-name} \
  --resource-group {rg} \
  --tail 50

# Check environment variables
az containerapp show \
  --name {app-name} \
  --resource-group {rg} \
  --query "properties.template.containers[0].env"
```

### Service restart returns 403?
```bash
# Verify managed identity has Container App Contributor role
RG=$(terraform output -raw resource_group_name)
PRINCIPAL_ID=$(az containerapp identity show \
  --name {app-name} \
  --resource-group "$RG" \
  --query "principalId" -o tsv)

# Add role if missing
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Container App Contributor" \
  --resource-group "$RG"
```

### OpenAI returns 401?
```bash
# Verify API key
KV_NAME=$(terraform output -raw key_vault_name)
az keyvault secret show \
  --vault-name "$KV_NAME" \
  --name "openai-api-key" \
  --query "value" -o tsv
```

### Database connection fails?
```bash
# Verify firewall allows Container Apps
SQL_SERVER=$(terraform output -raw sql_server_name)
az sql server firewall-rule list \
  --resource-group "$RG" \
  --server "$SQL_SERVER" \
  -o table
```

---

## Success Criteria

✅ **Deployment successful when:**
1. All Terraform resources created (terraform apply succeeded)
2. `/health` endpoint responds with all dependencies `true`
3. Admin dashboard loads and displays services
4. Service restart works from dashboard
5. Chat test question returns response
6. Managed identity roles verified
7. Key Vault secrets stored
8. Monitoring alerts created

---

## Next Steps

- **Run daily operations:** [[Operations]]
- **Troubleshoot issues:** [[Troubleshooting]]
- **Monitor service health:** [[Operations]] → Monitoring & Alerting
- **Deploy second client:** Repeat Phase 7 with new client name
