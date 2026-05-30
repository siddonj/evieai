# Operations Guide

> Daily operations, monitoring, and maintenance procedures

## Daily Standup (5 minutes)

Start each day with:

```bash
ORCH_URL="https://your-orchestrator-url"

# 1. Check service health
curl -s "$ORCH_URL/health" | jq '.dependencies'

# 2. Check recent errors in logs
az monitor metrics list \
  --resource-group "rg-acme-corp-prod" \
  --filter "name eq 'Exceptions' and timespan=2024-05-29T00:00:00Z/2024-05-29T23:59:59Z" \
  --interval PT1H

# 3. Check admin dashboard
# Open: https://your-ui-url/admin
# Verify: All service cards show green status
```

**Expected result:** All services healthy ✅ | No alerts

**If something's red:**
- [ ] Check [[Troubleshooting]] page
- [ ] Review logs in Azure Monitor
- [ ] Contact on-call operator

---

## Service Restart Procedures

### When to Restart

Restart a service when:
- ✋ Service health shows "unhealthy" (red)
- ✋ Tool timeout errors in logs
- ✋ Memory usage consistently >80%
- ✋ After deploying new image version
- ❌ NOT during active user sessions (if avoidable)

### How to Restart (Admin Dashboard)

**Step 1:** Open admin dashboard
```
https://your-ui-url/admin
```

**Step 2:** Find service card
- Look for "SQL MCP", "Mail MCP", "Orchestrator", etc.
- Color indicates status:
  - 🟢 Green = Healthy
  - 🟡 Yellow = Degraded
  - 🔴 Red = Unhealthy

**Step 3:** Click "Restart" button
- You'll see: "Restarting..." (loading state)
- Wait ~10 seconds for restart to complete
- Status changes to: "✓ Restarted at 14:32:45 UTC"

**Step 4:** Verify recovery
- Status should return to 🟢 Green
- Health check passes
- Service responds to tool calls

### How to Restart (API)

```bash
ORCH_URL="https://your-orchestrator-url"

curl -X POST "$ORCH_URL/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}'
```

**Example responses:**

Success (200):
```json
{
  "status": "success",
  "service": "sql",
  "timestamp": "2026-05-29T14:32:45Z",
  "message": "Service restarted successfully"
}
```

Error (403):
```json
{
  "status": "error",
  "service": "sql",
  "message": "Insufficient permissions to restart service",
  "details": "Managed identity missing Container App Contributor role"
}
```

Error (404):
```json
{
  "status": "error",
  "service": "unknown-service",
  "message": "Service not found",
  "details": "Expected format: {PROJECT_NAME}-mcp-{SERVICE_NAME}-{ENVIRONMENT}"
}
```

**Valid service names:**
- `orchestrator`
- `sql`
- `file_share`
- `o365_mail`
- `onedrive`
- `memory`
- `knowledge_base`
- `document_generation`
- `analytics`
- `dashboard`

### Batch Restart (All Services)

```bash
# Restart all MCP services (not orchestrator)
ORCH_URL="https://your-orchestrator-url"

for service in sql file_share o365_mail onedrive memory knowledge_base document_generation analytics dashboard; do
  curl -X POST "$ORCH_URL/restart" \
    -H "Content-Type: application/json" \
    -d "{\"service\": \"$service\"}"
  echo "Restarted $service"
  sleep 5  # Wait 5 seconds between restarts
done
```

---

## Monitoring & Alerting

### Health Metrics Table

| Metric | Healthy Range | Warning | Critical |
|--------|---|---|---|
| **Response Time (p95)** | <2s | 2–5s | >5s |
| **Error Rate** | <0.1% | 0.1–1% | >1% |
| **CPU Usage** | <50% | 50–80% | >80% |
| **Memory Usage** | <60% | 60–85% | >85% |
| **Tool Success Rate** | >99% | 95–99% | <95% |
| **Restart Count (hourly)** | 0 | 1–3 | >3 |
| **Queue Backlog** | 0 | 1–10 | >10 |

### KQL Queries (Azure Log Analytics)

**Tool Success Rates (Last 24h)**
```kusto
customMetrics
| where name == "tool_call"
| extend result = tostring(customDimensions.result)
| summarize success = countif(result == "success"), total = count() by bin(timestamp, 1h)
| extend success_rate = (success * 100.0) / total
| order by timestamp desc
```

**Response Time Percentiles**
```kusto
customMetrics
| where name == "chat_response_time"
| summarize p50 = percentile(value, 50),
            p95 = percentile(value, 95),
            p99 = percentile(value, 99) by bin(timestamp, 1h)
| order by timestamp desc
```

**Service Restart Events**
```kusto
customEvents
| where name == "service_restart"
| extend service = tostring(customDimensions.service),
         status = tostring(customDimensions.status)
| summarize count() by service, status, bin(timestamp, 1h)
```

**Error Rate by Service**
```kusto
traces
| where severityLevel >= 2  // Warnings and errors
| extend service = tostring(customDimensions.service)
| summarize error_count = count() by service, bin(timestamp, 1h)
```

### Setting Up Alerts

**Alert 1: Service Restart Rate Spike**
```bash
az monitor metrics alert create \
  --name "High Service Restart Rate" \
  --resource-group "rg-acme-corp-prod" \
  --scopes "/subscriptions/{sub-id}/resourcegroups/rg-acme-corp-prod" \
  --condition "total RestartCount > 5 during 1h" \
  --window-size 1h \
  --evaluation-frequency 15m \
  --action create --action-group-name "OnCall" \
  --severity 2
```

**Alert 2: High Error Rate**
```bash
az monitor metrics alert create \
  --name "High Error Rate" \
  --resource-group "rg-acme-corp-prod" \
  --scopes "/subscriptions/{sub-id}/resourcegroups/rg-acme-corp-prod" \
  --condition "total ExceptionCount > 100 during 1h" \
  --window-size 1h \
  --evaluation-frequency 5m \
  --action create --action-group-name "OnCall" \
  --severity 1
```

**Alert 3: Service Timeout**
```bash
az monitor metrics alert create \
  --name "Service Response Time High" \
  --resource-group "rg-acme-corp-prod" \
  --scopes "/subscriptions/{sub-id}/resourcegroups/rg-acme-corp-prod" \
  --condition "average ResponseTime > 5000 ms during 5m" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --action create --action-group-name "OnCall" \
  --severity 2
```

---

## Scaling & Capacity Planning

### CPU/Memory Tuning

**If services show high CPU (>80%):**
```bash
# Scale up CPU allocation
az containerapp update \
  --name {app-name} \
  --resource-group {rg} \
  --cpu 1.0
```

**If services show high memory (>85%):**
```bash
# Scale up memory allocation
az containerapp update \
  --name {app-name} \
  --resource-group {rg} \
  --memory 2.0Gi
```

### Replica Count Tuning

**Current replicas too low (errors on spike):**
```bash
# Increase min/max replicas
az containerapp update \
  --name {app-name} \
  --resource-group {rg} \
  --min-replicas 3 \
  --max-replicas 10
```

**Current replicas too high (unnecessary cost):**
```bash
# Decrease min/max replicas
az containerapp update \
  --name {app-name} \
  --resource-group {rg} \
  --min-replicas 1 \
  --max-replicas 5
```

### Capacity Formula

For N concurrent users:
```
Orchestrator Replicas = ceiling(N / 100)  + 1 reserve
SQL MCP Replicas      = ceiling(N / 150)  + 1 reserve
Other MCPs            = ceiling(N / 200)  + 1 reserve
```

**Example:** 1000 concurrent users
```
Orchestrator:  10 replicas + 1 = 11 replicas
SQL:           7 replicas + 1 = 8 replicas
Others:        5 replicas + 1 = 6 replicas
```

---

## Backup & Recovery

### What to Backup

| Component | Frequency | Retention | How |
|-----------|-----------|-----------|-----|
| Azure SQL Database | Daily | 35 days | Automatic (Azure manages) |
| PostgreSQL (if used) | Daily | 7 days | `pg_dump` to Storage |
| Key Vault secrets | Manual | Versioned | Azure Key Vault versioning (auto) |
| Terraform state | Per deploy | All versions | Azure Storage versioning (auto) |
| Configuration | Per change | Git history | Git repository |

### Database Backup

**Check SQL backup status:**
```bash
az sql db show \
  --name evieai \
  --resource-group {rg} \
  --server {sql-server} \
  --query "restorePoints"
```

**Restore to point-in-time:**
```bash
az sql db restore \
  --name evieai-restored \
  --resource-group {rg} \
  --server {sql-server} \
  --source-server {sql-server} \
  --source-name evieai \
  --restore-point-in-time "2026-05-28T14:30:00Z"
```

### Key Vault Recovery

**Export secrets:**
```bash
KV_NAME=$(terraform output -raw key_vault_name)

for secret in openai-api-key graph-client-secret; do
  az keyvault secret show \
    --vault-name "$KV_NAME" \
    --name "$secret" \
    --query "value" -o tsv > "$secret.txt"
done
```

**Restore secret version:**
```bash
az keyvault secret set-attributes \
  --vault-name "$KV_NAME" \
  --name "openai-api-key" \
  --version {version-id}
```

---

## Escalation Procedures

### Issue Severity Levels

| Level | Examples | Response Time | Actions |
|-------|----------|---|---|
| **P1 (Critical)** | Complete outage, data loss, security breach | Immediate (<5m) | Page on-call, escalate to lead |
| **P2 (High)** | Partial outage, service degradation >5 min | <15 minutes | Notify team, restart services |
| **P3 (Medium)** | Single feature broken, workaround available | <1 hour | Log issue, plan fix |
| **P4 (Low)** | UI glitch, performance improvement | Business hours | Track in backlog |

### Escalation Contacts

| Component | On-Call | Backup | Manager |
|-----------|---------|--------|---------|
| Platform (Orchestrator) | @platform-oncall | @platform-backup | @director |
| Data Layer (SQL) | @dba-oncall | @dba-backup | @data-director |
| Infrastructure | @devops-oncall | @devops-backup | @infra-director |

---

## Performance Tuning

### Query Optimization

**Slow SQL queries?**
```kusto
# Find slowest queries (last 24h)
customMetrics
| where name == "sql_query_duration"
| top 10 by todouble(value) desc
| extend query_text = tostring(customDimensions.query)
| project timestamp, value, query_text
```

**Fix:** Add indexes
```sql
-- If query filters on customer_id
CREATE NONCLUSTERED INDEX idx_customer_id 
ON customers(customer_id);
```

### API Response Time Analysis

**Identify slow endpoints:**
```kusto
customMetrics
| where name == "http_request_duration"
| extend endpoint = tostring(customDimensions.endpoint)
| summarize avg_duration = avg(value),
            p95 = percentile(value, 95) by endpoint
| order by avg_duration desc
```

---

## Cost Management

### Monthly Spend Review

```bash
# Get month-to-date spend
az costmanagement query create \
  --scope "/subscriptions/{sub-id}" \
  --timeframe "MonthToDate" \
  --granularity "Daily" \
  --aggregation '{"totalCost": {"name": "PreTaxCost", "function": "Sum"}}'
```

### Cost Optimization Checklist

- [ ] Container replicas set to min necessary (scale to 0 when idle?)
- [ ] SQL database on serverless tier (auto-pause enabled?)
- [ ] Log retention set to 30–90 days (not forever)
- [ ] Unused resources cleaned up (old app versions, test deployments)
- [ ] Reserved instances for predictable workloads (if budget allows)

---

## Next Steps

- **Emergency restart:** [[Service-Restart]]
- **Troubleshoot issues:** [[Troubleshooting]]
- **Understand architecture:** [[Architecture]]
- **Check deployment status:** [[Deployment-Checklist]]
