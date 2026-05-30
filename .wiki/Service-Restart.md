# Service Restart Guide

> How to restart EvieAI services via admin dashboard or API

## Overview

The service restart feature allows operators to recover failed services without portal access, SSH, or container orchestration knowledge.

**Who can restart:** Admins with access to the admin dashboard or API key  
**When needed:** Service unhealthy, timeout errors, memory leak detected  
**Duration:** ~10 seconds per service  
**Impact:** Graceful shutdown + reimage + health check  

---

## Admin Dashboard Restart (Easiest)

### Prerequisites
- [ ] Admin account with dashboard access
- [ ] Service is unhealthy or needs recovery
- [ ] Wait for previous restarts to finish (avoid cascade)

### Step-by-Step

**1. Open Admin Dashboard**
```
https://your-app.azurestaticapps.net/admin
```

**2. Find the Service Card**

Look for cards like:
- 🔴 "SQL MCP" — Red circle = unhealthy
- 🟡 "Mail MCP" — Yellow = degraded
- 🟢 "Orchestrator" — Green = healthy

**3. Click "Restart" Button**

The card shows:
```
┌─────────────────────────┐
│ SQL MCP                 │
│ Status: 🔴 Unhealthy   │
│                         │
│ Last restart: 2h ago    │
│ Response time: 5.2s     │
│                         │
│   [Restart] [Details]   │  ← Click here
└─────────────────────────┘
```

**4. Confirm Action**

A dialog appears:
```
⚠️  Restart SQL MCP?

This will:
• Stop the current service
• Pull fresh image from registry
• Start new service
• Validate health checks

Duration: ~10 seconds
Continue?  [Cancel] [Restart]
```

Click **[Restart]**

**5. Wait for Completion**

Button shows:
- "Restarting..." (loading animation) — Wait
- "✓ Restarted at 14:32:45 UTC" (green) — Success!
- "✗ Restart failed: Forbidden (403)" (red) — Check logs

**6. Verify Recovery**

- [ ] Status card turns 🟢 green
- [ ] Response time returns to <2s
- [ ] No error messages in dashboard

---

## API Restart (Programmatic)

### Request Format

```bash
curl -X POST "$ORCHESTRATOR_URL/restart" \
  -H "Content-Type: application/json" \
  -d '{
    "service": "sql"
  }'
```

### Valid Service Names

| Service | Name | Port | Restarts |
|---------|------|------|----------|
| SQL Database API | `sql` | 5000 | Query execution |
| File Share Search | `file_share` | 8001 | File indexing |
| Email Search | `o365_mail` | 8002 | Mailbox queries |
| OneDrive Search | `onedrive` | 8003 | Cloud file access |
| Memory/Context | `memory` | 8004 | User bookmarks |
| Knowledge Base | `knowledge_base` | 8005 | SOP searches |
| Doc Generation | `document_generation` | 8006 | Report generation |
| Analytics | `analytics` | 8007 | KPI dashboards |
| Dashboard | `dashboard` | 8009 | Metrics display |
| Orchestrator | `orchestrator` | 8000 | Chat API |

### Example Requests

**Restart SQL**
```bash
curl -X POST "https://acme-prod.yellowpond-123.eastus.azurecontainerapps.io/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}'
```

**Restart All MCPs (Sequential)**
```bash
#!/bin/bash
ORCH="https://your-orchestrator-url"

services=(sql file_share o365_mail onedrive memory knowledge_base document_generation analytics dashboard)

for service in "${services[@]}"; do
  echo "Restarting $service..."
  curl -X POST "$ORCH/restart" \
    -H "Content-Type: application/json" \
    -d "{\"service\": \"$service\"}"
  sleep 5  # Wait between restarts
  echo "Done: $service"
done
```

**Restart with Bearer Token (if auth enabled)**
```bash
curl -X POST "https://your-orchestrator-url/restart" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"service": "sql"}'
```

### Response Codes

| Status | Code | Meaning | Action |
|--------|------|---------|--------|
| ✅ Success | 200 | Service restarted | No action needed |
| ⚠️ Bad Request | 400 | Invalid service name | Check service list above |
| ❌ Unauthorized | 401 | No auth token | Provide valid bearer token |
| ❌ Forbidden | 403 | Insufficient permissions | Check managed identity role |
| ❌ Not Found | 404 | Service doesn't exist | Verify service name and PROJECT_NAME |
| ❌ Server Error | 500 | Azure API error | Check logs, retry in 30s |

### Success Response

```json
{
  "status": "success",
  "service": "sql",
  "timestamp": "2026-05-29T14:32:45.123456Z",
  "message": "Service restarted successfully"
}
```

### Error Responses

**Invalid service:**
```json
{
  "status": "error",
  "service": "invalid-service",
  "message": "Service not found",
  "details": "Valid services: sql, file_share, o365_mail, onedrive, memory, knowledge_base, document_generation, analytics, dashboard, orchestrator"
}
```

**Permission denied:**
```json
{
  "status": "error",
  "service": "sql",
  "message": "Insufficient permissions",
  "details": "Managed identity requires Container App Contributor role on resource group rg-acme-corp-prod"
}
```

**Azure service error:**
```json
{
  "status": "error",
  "service": "sql",
  "message": "Azure API error",
  "details": "ContainerAppsClient.revision_restart() failed: The operation was canceled."
}
```

---

## How It Works Under the Hood

```
Admin clicks "Restart"
      ↓
POST /restart {service: "sql"}
      ↓
Orchestrator reads env vars:
  PROJECT_NAME=acme-corp
  ENVIRONMENT=prod
  RESOURCE_GROUP=rg-acme-corp-prod
  AZURE_SUBSCRIPTION_ID=82aff681...
      ↓
Constructs Container App name:
  acme-corp-mcp-sql-prod
      ↓
Attempts Azure SDK:
  DefaultAzureCredential() → get managed identity
  ContainerAppsAPIClient().revision_restart(
    resource_group=rg-acme-corp-prod,
    container_app_name=acme-corp-mcp-sql-prod
  )
      ↓
If SDK fails (401, 403, timeout):
  Fall back to Azure CLI:
  az containerapp revision restart
    --name acme-corp-mcp-sql-prod
    --resource-group rg-acme-corp-prod
      ↓
Azure Container Apps:
  1. Stop current revision gracefully
  2. Wait for in-flight requests to complete
  3. Pull fresh image from registry
  4. Start new revision
  5. Run health checks
      ↓
Orchestrator returns:
  {
    "status": "success",
    "timestamp": "2026-05-29T14:32:45Z"
  }
      ↓
Admin Dashboard:
  • Status changes to 🟢 green
  • "Restarted" badge appears
  • Auto-refreshes health metrics
```

---

## Troubleshooting Restarts

### Problem: "Forbidden (403)"

**Cause:** Managed identity doesn't have Container App Contributor role

**Fix:**
```bash
RG="rg-acme-corp-prod"
APP_NAME="acme-corp-orchestrator-prod"

# Get managed identity principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query "principalId" -o tsv)

# Assign role
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Container App Contributor" \
  --resource-group "$RG"

# Wait 1-2 minutes for role propagation
sleep 120

# Retry restart
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}'
```

### Problem: "Service not found (404)"

**Cause:** Wrong PROJECT_NAME or ENVIRONMENT env var

**Fix:**
```bash
# Check orchestrator env vars
RG="rg-acme-corp-prod"
APP_NAME="acme-corp-orchestrator-prod"

az containerapp show \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query "properties.template.containers[0].env" \
  -o table

# Should see:
# Name                      Value
# PROJECT_NAME              acme-corp
# ENVIRONMENT               prod
# RESOURCE_GROUP            rg-acme-corp-prod
# AZURE_SUBSCRIPTION_ID     82aff681...

# If missing, update Container App
az containerapp update \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --set-env-vars \
    PROJECT_NAME=acme-corp \
    ENVIRONMENT=prod \
    RESOURCE_GROUP=rg-acme-corp-prod \
    AZURE_SUBSCRIPTION_ID=82aff681...
```

### Problem: "Service doesn't respond after restart"

**Cause:** Health check failing or service crash loop

**Fix:**
```bash
# 1. Check logs
az containerapp logs show \
  --name acme-corp-mcp-sql-prod \
  --resource-group rg-acme-corp-prod \
  --tail 50

# 2. Check health endpoint
curl "https://acme-corp-orchestrator-prod/health"

# 3. If logs show config error, verify:
#    - Database connection string valid
#    - Secrets in Key Vault exist
#    - API keys not expired

# 4. Manual restart (without orchestrator)
az containerapp revision restart \
  --name acme-corp-mcp-sql-prod \
  --resource-group rg-acme-corp-prod
```

### Problem: "Restart takes >30 seconds"

**Cause:** Image pull delay or slow startup

**Usual:** Takes 10–15 seconds  
**Acceptable:** Up to 30 seconds  
**Concerning:** >30 seconds

**Optimization:**
```bash
# 1. Pre-pull image to all container nodes
#    (Azure Container Apps does this, but can retry)

# 2. Check database cold start
#    SQL Serverless may take 10s to wake from pause
#    This is normal — no action needed

# 3. If consistently >30s, increase CPU
az containerapp update \
  --name acme-corp-mcp-sql-prod \
  --resource-group rg-acme-corp-prod \
  --cpu 1.0
```

---

## Multi-Client Restart Safety

When you have multiple clients deployed:

```
Client A (acme-corp-prod):
  Orchestrator → PROJECT_NAME=acme-corp
               → ENVIRONMENT=prod
               → Restart only: acme-corp-mcp-sql-prod
                              (Client B's services unaffected ✓)

Client B (beta-corp-staging):
  Orchestrator → PROJECT_NAME=beta-corp
               → ENVIRONMENT=staging
               → Restart only: beta-corp-mcp-sql-staging
                              (Client A's services unaffected ✓)
```

✅ **Safe:** Each client automatically isolated

⚠️ **Caution:** If env vars are wrong, restarts may affect wrong client

**Verify before mass restart:**
```bash
# List all MCPs for your client
az containerapp list \
  --resource-group "rg-acme-corp-prod" \
  --query "[].name" -o tsv

# Expected output:
# acme-corp-orchestrator-prod
# acme-corp-mcp-sql-prod
# acme-corp-mcp-file-share-prod
# ... (only acme-corp services)

# If you see other clients' services, STOP and check env vars
```

---

## Next Steps

- **Admin operations:** [[Operations]]
- **Troubleshoot issues:** [[Troubleshooting]]
- **API reference:** [[API-Reference]]
