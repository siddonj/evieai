# Disaster Recovery

> Emergency procedures and recovery plans

## Overview

This guide covers emergency scenarios and how to recover from them.

**RTO (Recovery Time Objective):** <1 hour  
**RPO (Recovery Point Objective):** <1 hour of data loss  
**Backup Frequency:** Continuous (Azure manages backups)  

---

## Emergency Contacts

| Severity | Contact | Response Time |
|----------|---------|---|
| **P1** (Complete outage) | Page on-call engineer | <5 minutes |
| **P2** (Partial outage) | Notify team | <15 minutes |
| **P3** (Degradation) | Log ticket | <1 hour |

---

## Common Emergency Scenarios

### Scenario 1: Service Unhealthy (Red Status)

**Symptom:** Admin dashboard shows 🔴 red status for a service

**What to do:**
1. ✅ Click [Restart] button in admin dashboard
2. ✅ Wait ~10 seconds for restart to complete
3. ✅ Verify status returns to 🟢 green
4. ✅ If restart fails, go to Scenario 3 (Service Won't Start)

**Time to fix:** 1–2 minutes

---

### Scenario 2: Chat Response Timeout

**Symptom:** User requests timeout after 10+ seconds

**Diagnosis:**
```bash
# Check all services healthy
curl "https://your-orchestrator/ready" | jq

# Should show all dependencies: true
```

**What to do:**
1. ✅ Check `/ready` endpoint (all dependencies must be `true`)
2. ✅ If any `false`, restart that service:
   ```bash
   curl -X POST "https://your-orchestrator/restart" \
     -H "Content-Type: application/json" \
     -d '{"service": "sql"}'
   ```
3. ✅ Retry chat request
4. ✅ If persists, check database (Scenario 4)

**Time to fix:** 2–5 minutes

---

### Scenario 3: Service Won't Start

**Symptom:** Service shows 🔴 red, restart button returns 403 or times out

**What to do:**

**Step 1: Check managed identity permissions**
```bash
RG="rg-acme-corp-prod"
APP_NAME="acme-corp-orchestrator-prod"

# Get managed identity principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name "$APP_NAME" \
  --resource-group "$RG" \
  --query "principalId" -o tsv)

# Check if it has Container App Contributor role
az role assignment list \
  --assignee "$PRINCIPAL_ID" \
  --resource-group "$RG" \
  --query "[].roleDefinitionName"

# Should see: "Container App Contributor"
```

**Step 2: Fix permissions (if missing)**
```bash
az role assignment create \
  --assignee "$PRINCIPAL_ID" \
  --role "Container App Contributor" \
  --resource-group "$RG"

# Wait 1-2 minutes for propagation
sleep 120
```

**Step 3: Check service logs**
```bash
# View last 50 lines of logs
az containerapp logs show \
  --name "acme-corp-mcp-sql-prod" \
  --resource-group "$RG" \
  --tail 50

# Look for errors:
# - Connection refused → Database unreachable
# - 401 Unauthorized → API key invalid
# - "Address already in use" → Port conflict
```

**Step 4: Manual restart (if button fails)**
```bash
# Restart from Azure CLI (doesn't require SDK)
az containerapp revision restart \
  --name "acme-corp-mcp-sql-prod" \
  --resource-group "$RG"
```

**Time to fix:** 5–10 minutes

---

### Scenario 4: Database Connection Failed

**Symptom:** SQL MCP returns 503, chat says "Cannot query database"

**What to do:**

**Step 1: Verify database exists**
```bash
RG="rg-acme-corp-prod"
SQL_SERVER="acme-corp-sql-prod"

az sql db list \
  --resource-group "$RG" \
  --server "$SQL_SERVER"

# Should list "evieai" database
```

**Step 2: Check firewall rules**
```bash
az sql server firewall-rule list \
  --resource-group "$RG" \
  --server "$SQL_SERVER"

# Should allow Azure services or VNET
```

**Step 3: Add VNET rule (if missing)**
```bash
az sql server vnet-rule create \
  --resource-group "$RG" \
  --server "$SQL_SERVER" \
  --name "allow-container-apps" \
  --vnet-name "vnet-acme-corp-prod" \
  --subnet "container-apps-subnet"
```

**Step 4: Test connection**
```bash
# From container (if you can exec into it)
sqlcmd -S acme-corp-sql-prod.database.windows.net \
       -U sqladmin \
       -P "$SQL_PASSWORD" \
       -d evieai \
       -Q "SELECT 1"
```

**Step 5: Restart SQL MCP**
```bash
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}'
```

**Time to fix:** 5–15 minutes

---

### Scenario 5: Complete Outage (All Services Down)

**Symptom:** Chat API returns 503, no services respond

**What to do:**

**Step 1: Check Azure status page**
```
https://status.azure.com/
```
If region is down, wait for Azure to recover (usually <30 min).

**Step 2: Verify resource group exists**
```bash
az group show --name "rg-acme-corp-prod"

# If not found, infrastructure was deleted
# See "Recovering Deleted Resources" below
```

**Step 3: Check all Container Apps**
```bash
az containerapp list \
  --resource-group "rg-acme-corp-prod" \
  --query "[].{name: name, provisioningState: properties.provisioningState}"

# All should show: "Succeeded"
# If "Failed", see Scenario 3 (Service Won't Start)
```

**Step 4: Restart entire environment**
```bash
# Restart all MCPs sequentially
for service in sql file_share o365_mail onedrive memory knowledge_base document_generation analytics dashboard; do
  curl -X POST "https://your-orchestrator/restart" \
    -H "Content-Type: application/json" \
    -d "{\"service\": \"$service\"}"
  sleep 10
done

# Then restart orchestrator
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "orchestrator"}'
```

**Step 5: Verify recovery**
```bash
curl "https://your-orchestrator/ready" | jq

# All dependencies should be true
```

**Time to fix:** 10–20 minutes

---

### Scenario 6: Data Loss (Accidental Deletion)

**Symptom:** Important data gone from database

**Recovery from backup:**

**Step 1: List available restore points**
```bash
az sql db show \
  --name "evieai" \
  --resource-group "rg-acme-corp-prod" \
  --server "acme-corp-sql-prod" \
  --query "restorePoints" -o table

# Shows timestamps of available backups
```

**Step 2: Restore to specific point-in-time**
```bash
# Restore to 1 hour ago
RESTORE_TIME="2026-05-29T13:32:45Z"  # ← Change to your time

az sql db restore \
  --resource-group "rg-acme-corp-prod" \
  --server "acme-corp-sql-prod" \
  --name "evieai-restored" \
  --source-name "evieai" \
  --restore-point-in-time "$RESTORE_TIME"
```

**Step 3: Verify restored data**
```bash
# Query restored database
sqlcmd -S acme-corp-sql-prod.database.windows.net \
       -U sqladmin \
       -d evieai-restored \
       -Q "SELECT COUNT(*) FROM [your_table]"
```

**Step 4: Promote restored database (if correct)**
```bash
# Rename original (backup)
az sql db rename \
  --name "evieai" \
  --new-name "evieai-backup-$(date +%s)" \
  --server "acme-corp-sql-prod" \
  --resource-group "rg-acme-corp-prod"

# Rename restored to primary
az sql db rename \
  --name "evieai-restored" \
  --new-name "evieai" \
  --server "acme-corp-sql-prod" \
  --resource-group "rg-acme-corp-prod"
```

**Step 5: Restart orchestrator**
```bash
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "orchestrator"}'
```

**Time to fix:** 10–15 minutes

---

### Scenario 7: Recovering Deleted Resources

**Symptom:** Resource group or Container App was deleted

**What to do:**

**Option A: Redeploy from Terraform**

```bash
cd terraform

# If entire resource group was deleted:
terraform apply

# If only some resources deleted:
terraform apply -target=azure_container_app.orchestrator
```

**Option B: Restore from soft-delete**

```bash
# Check if resource is in soft-delete state
az containerapp list --resource-group "rg-acme-corp-prod" \
  --query "[?deletionTime != null]"

# Restore soft-deleted app
az resource recover \
  --name "acme-corp-orchestrator-prod" \
  --resource-type "Microsoft.App/containerApps"
```

**Time to fix:** 10–20 minutes (redeploy) or <1 min (restore)

---

### Scenario 8: Key Vault Secrets Locked

**Symptom:** Services can't read secrets, return 401 Unauthorized

**What to do:**

**Step 1: Check Key Vault status**
```bash
KV_NAME=$(terraform output -raw key_vault_name)

az keyvault show --name "$KV_NAME"
```

**Step 2: If Key Vault soft-deleted, recover it**
```bash
az keyvault recover --name "$KV_NAME"
```

**Step 3: Check secret exists**
```bash
az keyvault secret show \
  --vault-name "$KV_NAME" \
  --name "openai-api-key"
```

**Step 4: If secret missing, recreate it**
```bash
az keyvault secret set \
  --vault-name "$KV_NAME" \
  --name "openai-api-key" \
  --value "sk-YOUR_KEY_HERE"
```

**Step 5: Restart services**
```bash
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "orchestrator"}'
```

**Time to fix:** 5–10 minutes

---

## Backup & Recovery Strategy

### What Gets Backed Up

| Component | Backup Type | Retention | RTO |
|-----------|---|---|---|
| **Database** | Point-in-time restore | 35 days | 5 min |
| **Key Vault** | Soft-delete + purge protection | 90 days | <1 min |
| **Storage** | Geo-redundant | Always | <1 hour |
| **Infrastructure** | Terraform state | Git history | 20 min |
| **Configuration** | Git repository | Forever | <1 min |

### Manual Backup Procedure

**Daily (recommended):**
```bash
# Backup Terraform state
terraform state pull > terraform.tfstate.backup.$(date +%Y-%m-%d)

# Export Key Vault secrets
KV_NAME=$(terraform output -raw key_vault_name)
az keyvault secret list --vault-name "$KV_NAME" > kv-secrets-backup.json

# Commit to Git
git add terraform.tfstate.backup.* kv-secrets-backup.json
git commit -m "Daily backup $(date)"
git push
```

**Weekly (before major changes):**
```bash
# Full database export
az sql db export \
  --name evieai \
  --server acme-corp-sql-prod \
  --resource-group rg-acme-corp-prod \
  --admin-user sqladmin \
  --admin-password "$SQL_PASS" \
  --storage-key-type SharedAccessKey \
  --storage-key "$STORAGE_KEY" \
  --storage-uri "https://storage.blob.core.windows.net/backups/evieai-$(date +%Y-%m-%d).bacpac"
```

---

## Recovery Time Estimates

| Scenario | Time | Automation |
|----------|------|-----------|
| Service restart | 2 min | ✅ One-click |
| Database restore | 10 min | ✅ Automated |
| Redeployment | 20 min | ✅ Terraform |
| Full recovery | 30 min | ✅ Scripts |

---

## Post-Incident Checklist

After recovering from an incident:

- [ ] Verify all services are healthy
- [ ] Test chat functionality end-to-end
- [ ] Check logs for errors
- [ ] Review what went wrong
- [ ] Update runbooks if needed
- [ ] Document incident in wiki
- [ ] Schedule postmortem with team

---

## Prevention

### Monitoring Alerts

Create these alerts to catch issues early:

```bash
# Alert: High error rate
az monitor metrics alert create \
  --name "EvieAI High Error Rate" \
  --resource-group "rg-acme-corp-prod" \
  --condition "total ExceptionCount > 100" \
  --window-size 1h \
  --severity 1

# Alert: Service restart spike
az monitor metrics alert create \
  --name "EvieAI Service Restart Spike" \
  --resource-group "rg-acme-corp-prod" \
  --condition "total RestartCount > 5" \
  --window-size 1h \
  --severity 2

# Alert: Database unavailable
az monitor metrics alert create \
  --name "EvieAI Database Unavailable" \
  --resource-group "rg-acme-corp-prod" \
  --condition "average DatabaseAvailableMemory < 100" \
  --window-size 5m \
  --severity 1
```

### Health Check Frequency

**Recommended schedule:**
- **Every 5 minutes:** Automated health check (`/ready` endpoint)
- **Every 15 minutes:** Error rate review
- **Every hour:** Performance metrics review
- **Daily:** Backup verification
- **Weekly:** Log analysis for trends

---

## Disaster Recovery Drill

Test your recovery procedures monthly:

**Monthly Drill Checklist:**
1. [ ] Simulate service failure (stop a Container App)
2. [ ] Time how long to detect (should be <5 min)
3. [ ] Time how long to restart (should be <2 min)
4. [ ] Verify recovery (test chat, check logs)
5. [ ] Document any issues
6. [ ] Update procedures if needed

---

## Emergency Contacts & Escalation

| Issue | Level | Contact | Time |
|-------|-------|---------|------|
| Single service down | P2 | On-call engineer | <15 min |
| Multiple services down | P1 | Page on-call + manager | <5 min |
| Data loss detected | P1 | DBA + manager | Immediate |
| Security breach | P1 | Security team | Immediate |
| Complete outage | P1 | All hands | Immediate |

---

## Next Steps

- **Daily operations:** [[Operations]]
- **Restart services:** [[Service-Restart]]
- **Troubleshoot issues:** [[Troubleshooting]]
