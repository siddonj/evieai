# Troubleshooting

> Common issues and how to fix them

## Deployment Issues

### Docker Build Fails

**Error:** `docker: command not found` or `Docker daemon not running`

**Fix:**
```bash
# Start Docker Desktop
# Mac: open /Applications/Docker.app
# Windows: Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
# Linux: sudo systemctl start docker

# Wait 30 seconds for Docker to fully start
docker ps  # Should show running containers
```

---

### Terraform Apply Fails with "Backend Error"

**Error:** `Error: Invalid backend configuration` or `Authentication failed`

**Fix:**
```bash
# 1. Check Azure CLI is authenticated
az account show  # Should show your subscription

# 2. If not, login
az login

# 3. Verify storage account exists (terraform state backend)
STORAGE_ACCOUNT="tfstate12345"
az storage account show \
  --resource-group "rg-terraform-state" \
  --name "$STORAGE_ACCOUNT"

# 4. If not, create it
az group create --name "rg-terraform-state" --location "eastus"
az storage account create \
  --name "$STORAGE_ACCOUNT" \
  --resource-group "rg-terraform-state"

# 5. Create container for state
az storage container create \
  --account-name "$STORAGE_ACCOUNT" \
  --name "tfstate"

# 6. Re-run terraform init with backend config
terraform init \
  -backend-config="resource_group_name=rg-terraform-state" \
  -backend-config="storage_account_name=$STORAGE_ACCOUNT" \
  -backend-config="container_name=tfstate" \
  -backend-config="key=evieai.tfstate"
```

---

### Container Apps Fail to Start

**Error in logs:** `CrashLoopBackOff` or `ImagePullBackOff`

**Diagnosis:**
```bash
# Check Container App status
az containerapp show \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "rg-acme-corp-prod" \
  --query "properties.provisioningState"

# Get detailed error logs
az containerapp logs show \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "rg-acme-corp-prod" \
  --tail 50
```

**Common causes:**

| Cause | Fix |
|-------|-----|
| Image not pushed to ACR | `az acr build ...` to build and push image |
| Registry authentication failed | `az acr login --name aiagent2acrdev` |
| Missing environment variables | Check Container App env vars with `az containerapp show ... --query "properties.template.containers[0].env"` |
| Database connection timeout | Verify SQL firewall allows VNET |
| OpenAI API key invalid or expired | Rotate key in Key Vault |

**Fix environment variables:**
```bash
az containerapp update \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "rg-acme-corp-prod" \
  --set-env-vars \
    AZURE_OPENAI_ENDPOINT="https://your-openai.openai.azure.com/" \
    AZURE_OPENAI_API_KEY="sk-..." \
    AZURE_OPENAI_DEPLOYMENT="gpt-4o" \
    PROJECT_NAME="acme-corp" \
    ENVIRONMENT="prod" \
    RESOURCE_GROUP="rg-acme-corp-prod"
```

---

## Service Health Issues

### Service Shows "Unhealthy" 🔴

**Step 1: Check if it's a transient issue**
```bash
# Wait 30 seconds and check again
# (Azure Container Apps may be restarting)

curl "https://your-orchestrator/ready"
```

**Step 2: If still unhealthy, restart the service**
```bash
# From admin dashboard: Click [Restart] button
# Or from CLI:
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}'
```

**Step 3: If restart doesn't help**
```bash
# Check logs
az containerapp logs show \
  --name "acme-corp-mcp-sql-prod" \
  --resource-group "rg-acme-corp-prod" \
  --tail 100 | grep -i error

# Common errors:
# - "Connection refused" → Database unreachable
# - "401 Unauthorized" → API key invalid
# - "Timeout" → Service overloaded or database cold start
```

---

### Chat Response Timeout

**Symptom:** Waiting >10 seconds for response, then error

**Diagnosis:**
```bash
# 1. Check if orchestrator is healthy
curl "https://your-orchestrator/health"

# 2. Check if all MCP servers are healthy
curl "https://your-orchestrator/ready"

# 3. Check orchestrator logs for "Timeout" errors
az containerapp logs show \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "rg-acme-corp-prod" \
  --tail 50 | grep -i "timeout\|error"

# 4. Check MCP server response times
# (Look in logs for slow queries)
```

**Common causes and fixes:**

| Cause | Fix |
|-------|-----|
| SQL database cold start | This is normal (~10s). SQL Serverless auto-pauses after 1h inactivity. |
| Large result set | Reduce query scope or add database indexes |
| Network latency | Check VNET connectivity, NSG rules |
| OpenAI timeout | Increase request timeout in config |

**Retry the chat:**
- First timeout is often cold start
- Second attempt usually succeeds
- If consistent timeouts, contact support

---

## Graph API Issues

### Email Search Returns 403 (Forbidden)

**Cause:** Admin consent not granted or missing permissions

**Fix:**
```bash
# 1. Check if admin consent was granted
# Azure Portal → Entra ID → App Registrations
# → Find "{PROJECT_NAME}-graph"
# → API Permissions
# → Look for "✓ Granted for [Your Tenant]"

# 2. If no checkmark, request admin consent
# Ask Global Admin to:
#   1. Portal → Entra ID → App Registrations → {name}
#   2. API Permissions → "Grant admin consent for [Tenant]"
#   3. Confirm in popup

# 3. Wait 1-2 minutes for propagation

# 4. Retry email query
```

---

### OneDrive Search Returns 404

**Cause:** Drive/file not found or user doesn't have access

**Fix:**
```bash
# 1. Verify you have access to the file
# (Try opening in OneDrive web directly)

# 2. Check if Graph API has Files.Read.All permission
# Portal → Entra ID → App Registrations → {name}
# → API Permissions → Should show "Files.Read.All"

# 3. If missing, add it:
#   a. API Permissions → Add a permission
#   b. Microsoft Graph → Delegated permissions
#   c. Search "Files.Read.All"
#   d. Check and click "Add permissions"
#   e. Request admin consent

# 4. Retry search
```

---

## Database Issues

### "Cannot connect to database" Error

**Diagnosis:**
```bash
# 1. Verify SQL Server is running
az sql server show \
  --resource-group "rg-acme-corp-prod" \
  --name "acme-corp-sql-prod"

# 2. Check firewall rules allow Container Apps VNET
az sql server firewall-rule list \
  --resource-group "rg-acme-corp-prod" \
  --server "acme-corp-sql-prod"

# 3. Test connection from CLI
sqlcmd -S acme-corp-sql-prod.database.windows.net \
       -U sqladmin \
       -P "$SQL_PASSWORD" \
       -d evieai \
       -Q "SELECT 1"
```

**Common fixes:**

| Issue | Fix |
|-------|-----|
| Firewall blocks connection | Add VNET service endpoint: `az sql server vnet-rule create ...` |
| Database doesn't exist | Create database: `az sql db create --name evieai ...` |
| User doesn't exist | Create user: `CREATE LOGIN sqladmin WITH PASSWORD='...'` |
| SQL Server auto-paused | This is normal for serverless. First query ~10s. |

---

### Slow Database Queries

**Symptom:** Chat times out waiting for SQL results

**Diagnosis:**
```kusto
# In Azure Log Analytics, run:
customMetrics
| where name == "sql_query_duration"
| top 10 by todouble(value) desc
| extend query = tostring(customDimensions.query)
| project timestamp, value, query
```

**Fix slow queries:**

```sql
-- Identify missing indexes
SELECT * FROM sys.dm_db_missing_index_details WHERE database_id = DB_ID()

-- Create index on commonly filtered columns
CREATE NONCLUSTERED INDEX idx_customer_id 
ON customers(customer_id)
INCLUDE (order_count, total_spent)
```

---

## OpenAI API Issues

### "Invalid API key" (401)

**Fix:**
```bash
# 1. Verify key in Key Vault
KV_NAME=$(terraform output -raw key_vault_name)
az keyvault secret show \
  --vault-name "$KV_NAME" \
  --name "openai-api-key" \
  --query "value" -o tsv

# 2. Check if key is valid
# (Keys expire or may be rotated)
# Portal → Azure OpenAI → Keys and endpoints
# → Regenerate if needed

# 3. Update Key Vault secret
az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "openai-api-key" \
  --value "sk-NEW_KEY_HERE"

# 4. Restart orchestrator to pick up new key
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "orchestrator"}'
```

---

### "Invalid deployment name" (400)

**Fix:**
```bash
# 1. Check deployment name in Azure OpenAI
# Portal → Azure OpenAI → Model deployments
# List should include your AZURE_OPENAI_DEPLOYMENT value

# 2. If not found, create deployment
# → Select model (e.g., gpt-4o)
# → Name it (e.g., "gpt-4o")

# 3. Update environment variable
az containerapp update \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "rg-acme-corp-prod" \
  --set-env-vars AZURE_OPENAI_DEPLOYMENT="gpt-4o"

# 4. Restart orchestrator
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "orchestrator"}'
```

---

### "Rate limit exceeded" (429)

**Symptoms:** Requests fail with 429, may recover after waiting

**Fix:**
```bash
# 1. Check current TPM (Tokens Per Minute)
# Portal → Azure OpenAI → Deployments
# → View capacity (e.g., "100 TPM")

# 2. Increase capacity if needed
# → Click deployment
# → → Adjust capacity
# → → Select higher TPM (e.g., 200)
# → → Apply

# 3. Implement retry logic in code
# (Orchestrator already has exponential backoff)
```

---

## Admin Dashboard Issues

### Service Cards Don't Update

**Fix:**
```bash
# 1. Hard refresh browser
# Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

# 2. Check if /ready endpoint works
curl "https://your-orchestrator/ready" | jq

# 3. If /ready returns error, check orchestrator logs
az containerapp logs show \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "rg-acme-corp-prod"

# 4. Restart orchestrator
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "orchestrator"}'
```

---

### Restart Button Returns "Forbidden"

**Fix:** See [[Service-Restart]] → Troubleshooting Restarts → "Forbidden (403)"

---

## Multi-Client Issues

### Services from Wrong Client Show Up

**Cause:** Environment variables set incorrectly

**Fix:**
```bash
# 1. Verify correct Container App
RG="rg-acme-corp-prod"
az containerapp show \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "$RG" \
  --query "properties.template.containers[0].env" \
  -o table

# Should show:
# PROJECT_NAME = acme-corp
# ENVIRONMENT  = prod

# 2. If wrong, update:
az containerapp update \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "$RG" \
  --set-env-vars \
    PROJECT_NAME="acme-corp" \
    ENVIRONMENT="prod"

# 3. Restart orchestrator
curl -X POST "https://acme-prod.../restart" \
  -d '{"service": "orchestrator"}'
```

---

## Support & Escalation

| Issue | Next Step |
|-------|-----------|
| Database connectivity | Check SQL firewall, verify credentials |
| API timeouts | Check service health, restart if needed |
| Graph API 403 | Request admin consent in Entra ID |
| OpenAI 401 | Rotate API key |
| Service restart fails | Verify managed identity has `Container App Contributor` role |
| Issue persists after troubleshooting | Collect logs and contact support |

**Collect diagnostic info:**
```bash
RG="rg-acme-corp-prod"

# Capture current state
az containerapp list --resource-group "$RG" -o json > apps.json
az containerapp logs show \
  --name "acme-corp-orchestrator-prod" \
  --resource-group "$RG" \
  --tail 100 > logs.txt

# Include in support ticket
```

---

## Next Steps

- **Restart a service:** [[Service-Restart]]
- **Run daily operations:** [[Operations]]
- **Check deployment status:** [[Deployment-Checklist]]
