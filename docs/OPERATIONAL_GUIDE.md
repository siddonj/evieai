# EvieAI Operational Guide

> Complete operations manual for running and maintaining EvieAI in production.  
> Last updated: May 29, 2026

---

## Table of Contents

1. [Daily Operations](#daily-operations)
2. [Service Restart Procedures](#service-restart-procedures)
3. [Monitoring & Alerting](#monitoring--alerting)
4. [Troubleshooting](#troubleshooting)
5. [Backup & Recovery](#backup--recovery)
6. [Performance Tuning](#performance-tuning)
7. [Scaling & Capacity Planning](#scaling--capacity-planning)

---

## Daily Operations

### Start-of-Day Checks

**Every morning, verify system health:**

```bash
# 1. Check orchestrator health
curl -s https://api.yourdomain.com/health
# Expected: {status: "healthy"}

# 2. Check all dependencies
curl -s https://api.yourdomain.com/ready
# Expected: {status: "ready", dependencies: {...all healthy...}}

# 3. Check action reliability
curl -s https://api.yourdomain.com/actions/reliability
# Expected: success_rate > 95%

# 4. Check connector sync status
curl -s https://api.yourdomain.com/connectors/sync/reliability
# Expected: backlog < 100 items, no dead letters
```

If any check fails, see [Troubleshooting](#troubleshooting).

### Admin Dashboard Review

**Log into admin dashboard at `/admin` and check:**

1. **Service Health** — All services green?
   - Red/yellow = investigate service logs
   - Gray = service not yet started

2. **Approvals Queue** — Any pending approvals?
   - Approve/reject as needed
   - Check for unusual action types

3. **Error Logs** — Any new errors since yesterday?
   - Review MCP server logs
   - Check orchestrator error rate

4. **Restart History** — Any recent unexpected restarts?
   - Unexpected restarts indicate instability
   - Consider scaling up or optimizing

### User Traffic Monitoring

**Check metrics in Log Analytics (Azure portal):**

```kusto
// Daily active users
AzureDiagnostics
| where ResourceType == "CONTAINERAPPS"
| where Name == "orchestrator"
| where status_code == 200
| summarize UniqueUsers = dcount(user_id), RequestCount = count()

// Peak load time
AzureDiagnostics
| where Name == "orchestrator"
| where status_code == 200
| summarize RequestCount = count() by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
| limit 12
```

---

## Service Restart Procedures

### When to Restart a Service

| Scenario | Service | Action |
|----------|---------|--------|
| **High memory usage** | Any MCP | Restart to clear memory leaks |
| **No response to requests** | Mail MCP, OneDrive MCP | Restart Graph API connection |
| **Database connection pool exhausted** | SQL MCP | Restart to reset connection pool |
| **Slow responses** | Orchestrator | Restart if response time >5s |
| **"Unhealthy" status** | Any | Restart if health check fails 3× |
| **After code deployment** | All services | Rolling restart (orchestrator → MCPs) |
| **After credential rotation** | Mail/OneDrive MCPs | Restart to load new credentials from Key Vault |

### Manual Restart via Admin Dashboard

**Step-by-step:**

1. **Log in** to admin dashboard (https://yourdomain.com/admin)
2. **Find service** in the health monitor (e.g., "SQL MCP")
3. **Click "Restart"** button on the service card
4. **Wait for confirmation** — UI shows "Restarting..." then success/error
5. **Verify health** — Should return to green within 10–15 seconds
6. **Check logs** if restart failed

**Expected behavior:**
- In-flight requests complete gracefully (with timeout)
- Container stops and pulls fresh image
- Container starts, health check validates startup
- Service available again (usually <15 seconds total)

### Programmatic Restart via API

If admin dashboard is unavailable:

```bash
# Restart SQL MCP
curl -X POST https://api.yourdomain.com/restart \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}' \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
# {
#   "service": "sql",
#   "status": "restarted",
#   "timestamp": "2026-05-29T14:32:45Z",
#   "message": "Service restarted successfully"
# }
```

### Restart Sequence During Deployment

When deploying a new version, restart in this order to minimize impact:

```
1. MCP Servers (parallel safe)
   - SQL MCP
   - File Share MCP
   - O365 Mail MCP
   - OneDrive MCP
   - Memory MCP
   - Knowledge Base MCP
   - Document Generation MCP
   - Analytics MCP
   - Dashboard MCP

2. Wait 30 seconds for MCP health checks to pass

3. Orchestrator (last, because it depends on MCPs)
   - This will trigger healthchecks to re-discover MCP tools
```

**Why this order?**
- Restarting orchestrator first causes "MCP unreachable" errors
- Restarting MCPs first means orchestrator just reconnects
- Orchestrator restart is safe once all MCPs are healthy

---

## Monitoring & Alerting

### Health Metrics to Track

| Metric | Good Range | Warning | Critical |
|--------|------------|---------|----------|
| **Orchestrator response time** | <500ms | 500–2000ms | >2000ms |
| **MCP response time** | <1000ms | 1–3 sec | >3 sec |
| **Chat request success rate** | >99% | 95–99% | <95% |
| **Tool call success rate** | >95% | 90–95% | <90% |
| **Database connection pool** | <50% | 50–80% | >80% |
| **Error rate** | <0.1% | 0.1–1% | >1% |
| **Restart frequency** | <1/week | 1–3/week | >3/week |
| **SQL Serverless compute** | <80% | 80–90% | >90% |

### Azure Monitor Queries

#### Request Duration Over Time

```kusto
AzureDiagnostics
| where ResourceType == "CONTAINERAPPS"
| where Name == "orchestrator"
| extend DurationSec = duration_ms / 1000
| summarize
    AvgDuration = avg(DurationSec),
    MaxDuration = max(DurationSec),
    p95Duration = percentile(DurationSec, 95)
    by bin(TimeGenerated, 5m)
| render timechart
```

#### Error Rate by Service

```kusto
AzureDiagnostics
| where ResourceType == "CONTAINERAPPS"
| summarize
    TotalRequests = count(),
    Errors = countif(status_code >= 500)
    by Name
| extend ErrorRate = (Errors / TotalRequests) * 100
| order by ErrorRate desc
```

#### Tool Call Success Rate

```kusto
AzureDiagnostics
| where ResourceType == "CONTAINERAPPS"
| where Name == "orchestrator"
| where message like "tool_call"
| summarize
    TotalCalls = count(),
    SuccessCalls = countif(status_code == 200),
    FailedCalls = countif(status_code >= 400)
    by tool_name
| extend SuccessRate = (SuccessCalls / TotalCalls) * 100
| order by SuccessRate asc
```

### Alert Rules (Recommended)

Create these alerts in Azure Monitor:

#### Alert 1: High Error Rate
```
Condition: Error rate > 1% in last 5 min
Severity: Critical
Action: Page on-call engineer, restart orchestrator
```

#### Alert 2: MCP Unreachable
```
Condition: /ready returns dependency error
Severity: Critical
Action: Restart failing MCP service
```

#### Alert 3: Database Slow
```
Condition: SQL query response time > 3 sec
Severity: Warning
Action: Check SQL logs, consider scaling up
```

#### Alert 4: High Container CPU
```
Condition: Container CPU > 90% for 5 min
Severity: Warning
Action: Consider increasing replicas or pod resource limits
```

#### Alert 5: Frequent Restarts
```
Condition: Service restarts > 3 in 1 hour
Severity: Warning
Action: Investigate root cause, check logs
```

---

## Troubleshooting

### Service Returns "Unhealthy" Status

**Diagnosis:**

```bash
# 1. Check specific service logs
docker compose logs orchestrator --tail=100

# OR in Azure:
# Select service in Azure portal → Container Apps → Logs → View logs
```

**Common causes and fixes:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| **"OpenAI unreachable"** | Bad endpoint or API key | Verify AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in Key Vault |
| **"Database connection failed"** | SQL Server firewall or bad conn string | Check SQL_CONNECTION_STRING, allow Azure services in firewall |
| **"Graph API 401"** | Expired credentials or bad refresh token | Rotate AZURE_CLIENT_SECRET, re-grant admin consent |
| **"Memory exhaustion"** | Memory leak in service | Restart service, monitor memory usage |
| **"Port already in use"** | Duplicate process or stale container | Kill process, `docker compose down && up` |

### Chat Requests Timing Out

**Diagnosis:**

```bash
# Check orchestrator response time
curl -w "Response time: %{time_total}s\n" \
  https://api.yourdomain.com/ready
```

**Common causes:**

1. **MCP server slow** — One tool is blocking
   - Check which tool in the error message
   - Restart that MCP service
   - Consider scaling up its compute

2. **Database slow** — SQL query taking >5 seconds
   - Check Azure SQL metrics for CPU/DTU
   - Add database index if query is complex
   - Consider upgrading to higher SKU

3. **OpenAI rate limit** — Hitting API throttle
   - Check OpenAI quota in Azure portal
   - Reduce concurrency or add retry backoff
   - Request TPM increase from Azure support

**Fix:**

```bash
# Restart orchestrator to clear any stuck connections
curl -X POST https://api.yourdomain.com/restart \
  -H "Authorization: Bearer TOKEN" \
  -d '{"service": "orchestrator"}'

# Then retry the chat request
```

### Mail or OneDrive Returns 403 Forbidden

**Diagnosis:**

Mail/OneDrive MCP can reach Microsoft Graph API but doesn't have permissions.

**Root cause:** Admin consent not granted or token expired.

**Fix:**

1. **Check admin consent status:**
   - Azure portal → Entra ID → App registrations
   - Find `{project-name}-graph-app-{environment}`
   - Go to API permissions
   - Look for green checkmarks next to Mail.Read and Files.Read.All

2. **If not granted:**
   - As a Global Admin, click "Grant admin consent for [Tenant]"
   - Wait 1–2 minutes for replication

3. **Rotate credentials if expired:**
   - Go to "Certificates & secrets"
   - Delete old secret, create new one
   - Update AZURE_CLIENT_SECRET in Key Vault
   - Restart Mail/OneDrive MCPs

### Approval Queue Growing (Backlog)

**Diagnosis:**

Approvals are pending and not being processed.

```bash
# Check pending approvals
curl https://api.yourdomain.com/actions/approvals | jq '.pending | length'
```

**Causes:**

1. **Admin not reviewing** — Approvals require manual action
2. **Approval circuit breaker open** — Too many failures
3. **Write-back service down** — Action execution failing

**Fix:**

```bash
# 1. Review and approve pending actions
# Log into admin dashboard → Approvals tab

# 2. If circuit breaker open, reset it
curl -X POST https://api.yourdomain.com/actions/circuit/reset

# 3. Check action execution logs
curl https://api.yourdomain.com/actions/reliability
```

### Knowledge Base Search Returns No Results

**Diagnosis:**

Semantic search over SOPs is not finding documents.

**Causes:**

1. **Knowledge base not indexed** — Documents not in system
2. **Query semantically unrelated** — Words don't match SOPs
3. **Embedding service down** — Vector search unavailable

**Fix:**

```bash
# 1. Check KB status
curl https://api.yourdomain.com/health | jq '.dependencies.knowledge_base'

# 2. Re-index knowledge base (if supported)
# Contact support to re-ingest SOP documents

# 3. Try more specific query
# Instead of "general process", try "new employee onboarding"
```

### Restarting Service Fails

**Diagnosis:**

Restart button shows "Failed: {error message}".

**Common causes:**

| Error | Cause | Fix |
|-------|-------|-----|
| **"Subscription not found"** | AZURE_SUBSCRIPTION_ID env var missing | Verify env var set in Container App |
| **"Container app not found"** | Naming mismatch (PROJECT_NAME or ENVIRONMENT wrong) | Check PROJECT_NAME, ENVIRONMENT env vars match resource names |
| **"Access denied"** | Managed identity missing permissions | Verify managed identity has Container App Contributor role |
| **"CLI not available"** | Docker image missing Azure CLI | Use SDK approach (first attempt) or upgrade image |

**Fix:**

1. **Verify environment variables:**
   ```bash
   az containerapp show -n {PROJECT_NAME}-orchestrator-{ENVIRONMENT} \
     -g {RESOURCE_GROUP} \
     --query "properties.template.containers[0].env" \
     | grep -E "PROJECT_NAME|ENVIRONMENT|AZURE_SUBSCRIPTION_ID"
   ```

2. **Check managed identity role:**
   ```bash
   az role assignment list \
     --scope /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP} \
     --query "[?contains(principalName, 'orchestrator')]"
   ```

3. **If role missing, add it:**
   ```bash
   az role assignment create \
     --role "Contributor" \
     --assignee-object-id {MANAGED_IDENTITY_ID} \
     --scope /subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}
   ```

---

## Backup & Recovery

### What to Back Up

| Component | Frequency | Retention | Location |
|-----------|-----------|-----------|----------|
| **Database** | Daily | 30 days | Azure SQL auto-backup |
| **Blob storage** | Daily | 90 days | Geo-redundant storage |
| **Configuration** | Weekly | 1 year | terraform/ folder (Git) |
| **Secrets** | Weekly | 1 year | Key Vault versioning |
| **Audit logs** | Continuous | 90 days | Log Analytics |

### Database Recovery

**Azure SQL automatic backups:**

```bash
# List available backups
az sql db list-restorable-dropped-databases \
  --resource-group {RESOURCE_GROUP} \
  --server {SQL_SERVER}

# Restore to point-in-time (last 35 days)
az sql db restore \
  --resource-group {RESOURCE_GROUP} \
  --server {SQL_SERVER} \
  --name {DATABASE_NAME} \
  --dest-name {DATABASE_NAME}-restore \
  --time "2026-05-20T10:00:00Z"
```

### Configuration Recovery

**Restore Terraform state:**

```bash
# State stored in Azure Storage (bootstrapped)
# View state history
az storage blob list \
  --container-name tfstate \
  --account-name {STORAGE_ACCOUNT}

# Restore from backup
az storage blob download \
  --container-name tfstate-backup \
  --name terraform.tfstate \
  --account-name {STORAGE_ACCOUNT} \
  --file terraform.tfstate

# Re-apply
terraform apply -state=terraform.tfstate
```

### Key Vault Recovery

**Restore deleted secrets:**

```bash
# List deleted secrets
az keyvault key list-deleted \
  --vault-name {KEY_VAULT_NAME}

# Recover a secret
az keyvault secret recover \
  --vault-name {KEY_VAULT_NAME} \
  --name AZURE_OPENAI_API_KEY
```

---

## Performance Tuning

### Container CPU/Memory Optimization

**Current configuration (per container):**
```
CPU: 0.5 vCPU
Memory: 1 GiB
```

**Tune if experiencing:**

| Issue | Solution |
|-------|----------|
| **CPU throttling** | Increase to 1.0 vCPU |
| **Memory exhaustion** | Increase to 2 GiB |
| **Consistent low usage** | Decrease to 0.25 vCPU (save cost) |

**Apply change:**

```bash
az containerapp update \
  --name {CONTAINER_APP_NAME} \
  --resource-group {RESOURCE_GROUP} \
  --cpu 1.0 \
  --memory "2Gi"
```

### Database Query Optimization

**Identify slow queries:**

```kusto
// Queries taking >1 second
AzureDiagnostics
| where ResourceType == "CONTAINERAPPS"
| where Name == "sql_mcp"
| where duration_ms > 1000
| summarize Count = count(), AvgDuration = avg(duration_ms)
    by query_hash
| order by Count desc
```

**Optimization steps:**

1. **Add database index** (with DBA approval)
   ```sql
   CREATE INDEX idx_customer_id ON Orders(customer_id);
   ```

2. **Reduce query complexity** — Break into smaller queries

3. **Enable result caching** — Cache common queries in Redis

4. **Scale database** — Upgrade to higher vCore tier

### API Response Time Optimization

**Identify bottleneck:**

```bash
# Add tracing header to request
curl -H "X-Trace-ID: trace-123" \
  https://api.yourdomain.com/api/chat \
  -d '{"message": "..."}' \
  -w "\nTotal time: %{time_total}s\n"

# Check logs for timing breakdown
# Log Analytics query:
# AzureDiagnostics
# | where trace_id == "trace-123"
# | order by TimeGenerated
```

**Common bottlenecks and fixes:**

| Bottleneck | Fix |
|------------|-----|
| **OpenAI latency** | Reduce prompt size, enable caching |
| **MCP tool call** | Profile slow tool, add index, scale compute |
| **Network latency** | Use same region for all services |
| **Orchestrator latency** | Increase CPU/memory, reduce parallelism |

---

## Scaling & Capacity Planning

### Horizontal Scaling (Add Replicas)

**Current setup:**
```
Min replicas: 0
Max replicas: 5
Target CPU: 80%
```

**When to scale up:**

```bash
# Monitor CPU usage
az containerapp stats show \
  --name {CONTAINER_APP} \
  --resource-group {RESOURCE_GROUP} \
  --query containers[0].cpu

# If consistently >80%, increase max replicas
az containerapp update \
  --name {CONTAINER_APP} \
  --resource-group {RESOURCE_GROUP} \
  --max-replicas 10
```

### Vertical Scaling (Increase Pod Size)

**When to scale up:**

```bash
# Check memory usage
az containerapp stats show \
  --name {CONTAINER_APP} \
  --resource-group {RESOURCE_GROUP} \
  --query containers[0].memory

# If >800 MiB, increase pod memory
az containerapp update \
  --name {CONTAINER_APP} \
  --resource-group {RESOURCE_GROUP} \
  --memory "2Gi" \
  --cpu "1.0"
```

### Capacity Planning Formula

For N users and 10 chat requests per user per day:

```
Daily requests = N × 10
Peak hour requests = (Daily requests / 8) × 2 (assuming 2x peak)

Container CPU needed (per 100 req/sec):
- Lightweight query (files): 0.1 vCPU
- Medium query (SQL + mail): 0.3 vCPU
- Heavy query (multi-source synthesis): 0.5 vCPU

Example: 500 users, 100 req/sec average
- Assume 50% medium, 50% heavy = avg 0.4 vCPU per req
- Throughput: 1 vCPU → 2.5 req/sec
- Containers needed: ceil(100 / 2.5) = 40 containers
```

### Cost Tracking

**Monthly cost calculation:**

```bash
# Get Container Apps usage
az containerapp metrics show \
  --name {CONTAINER_APP} \
  --resource-group {RESOURCE_GROUP} \
  --metrics cpu-usage memory-usage

# Estimate monthly cost
# CPU: Avg vCPU × $0.000084 × 730 hours
# Memory: Avg GB × $0.000036 × 730 hours
```

---

## Escalation Procedure

### Minor Issue (Response time < 2 min)

1. Check `/health` and `/ready`
2. Review recent logs
3. If MCP issue, restart that service
4. Monitor for 5 minutes

### Major Issue (Critical service down)

1. **Notify team immediately** — Slack #incidents
2. **Assess scope** — How many users affected?
3. **Implement workaround** — Redirect to fallback if available
4. **Restart orchestrator + all MCPs** (failsafe)
5. **If still down after 10 min** → Open severity 1 support ticket

### Escalation Contacts

| Component | Tier 1 | Tier 2 | Tier 3 |
|-----------|--------|--------|--------|
| **Orchestrator** | On-call engineer | Platform lead | CTO |
| **OpenAI API** | Azure support | OpenAI account rep | - |
| **SQL Database** | DBA on-call | Azure support | - |
| **Graph API** | M365 support | Azure support | - |

---

## See Also

- [docs/FEATURES.md](FEATURES.md) — Feature reference
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — System design
- [docs/SUPPORT.md](SUPPORT.md) — Detailed troubleshooting
- [terraform/README.md](../terraform/README.md) — Infrastructure details
