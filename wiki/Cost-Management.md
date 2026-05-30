# Cost Management

## Overview

EvieAI can be stopped when not in use, reducing monthly costs by **80-90%**. This page explains how to manage your Azure spending.

## Cost Breakdown

### Running 24/7 (Continuous)

| Component | Cost/Month |
|-----------|-----------|
| Container Apps (12 services) | $140-160 |
| SQL Database (Serverless) | $20-30 |
| Storage Account | $10-15 |
| Key Vault | $0.60 |
| Log Analytics | $15-25 |
| **Total** | **$190-240/month** |

### Stopped (Services at 0 Replicas)

| Component | Cost/Month |
|-----------|-----------|
| Container Apps | **$0** |
| SQL Database | **$0** |
| Storage Account | $10-15 |
| Key Vault | $0.60 |
| Log Analytics | $2-5 |
| **Total** | **$13-23/month** |

### Annual Savings

| Usage Pattern | Monthly | Annual Savings |
|---------------|---------|-----------------|
| 8 hours/day | $67 | **$1,600** |
| Weekdays only | $95 | **$1,260** |
| Off-hours only | $35 | **$1,980** |

## Stop/Start Services

### PowerShell (Windows)

```powershell
# Check status
.\scripts\manage-environment.ps1 -Action status

# Start services
.\scripts\manage-environment.ps1 -Action start

# Stop services
.\scripts\manage-environment.ps1 -Action stop
```

### Bash (Linux/Mac)

```bash
# Make executable first
chmod +x scripts/manage-environment.sh

# Check status
./scripts/manage-environment.sh status

# Start services
./scripts/manage-environment.sh start

# Stop services
./scripts/manage-environment.sh stop
```

## Startup/Shutdown Times

| Action | Time | Notes |
|--------|------|-------|
| Stop (scale to 0) | 30-60 sec | Graceful shutdown |
| Start (scale to 1) | 60-120 sec | Pull image & boot |
| Fully Ready | 2-3 min | Health checks pass |

## What Stays Running When Stopped

- ✅ **Static Web App (UI)** — ~$0.40/month
- ✅ **Storage Account** — Data persists
- ✅ **SQL Database** — Data persists, auto-pauses
- ✅ **Key Vault** — Secrets secured

**Zero data loss when stopped!**

## Cost Optimization Strategies

### Strategy 1: Manual On-Demand
Perfect for: Development & testing

**Steps:**
1. Stop services: `manage-environment.ps1 -Action stop`
2. Start when needed: `manage-environment.ps1 -Action start`
3. Savings: 80-90%

### Strategy 2: Scheduled (Recommended)
Perfect for: Business hours only

**Setup with Azure Logic Apps (free tier):**
1. Create Logic App in Azure portal
2. Add Recurrence trigger → Daily at 6 PM
3. Add action: Run PowerShell script
4. Set to stop services
5. Create second Logic App for 8 AM start
6. Savings: 65-70%

**Cost:** ~$0.50/month (mostly free)

### Strategy 3: Hybrid
Perfect for: Enterprise usage patterns

- Stop: Weekends & evenings
- Stop: Lunch hours (12 PM-2 PM)
- Run: Full capacity during peak
- Savings: 50-60%

## View Your Costs

### Current Spending (Last 30 Days)
```bash
az consumption usage list --query "[].{date:usageStart, amount:billableAmount}" -o table
```

### Cost by Service
```bash
az consumption usage list --query "[].{service:meterCategory, cost:billableAmount}" -o table
```

### Set Budget Alert
```bash
az costmanagement budget create --resource-group rg-aiagent2-dev \
  --name "EvieAI Monthly Budget" \
  --category "Cost" \
  --amount 150
```

## Automation with Azure Logic Apps

### Step-by-Step Setup

**1. Create Automation Storage Account**
```bash
az storage account create --name evieaiscripts \
  --resource-group rg-aiagent2-dev \
  --sku Standard_LRS
```

**2. Upload Stop Script**
```bash
az storage blob upload --account-name evieaiscripts \
  --container-name scripts \
  --name manage-environment.ps1 \
  --file scripts/manage-environment.ps1
```

**3. Create Logic App in Portal**
- Automation account → Runbooks
- Add PowerShell runbook
- Paste script content
- Create schedule: Daily 6 PM

**4. Create Alert**
- Budget alert at $150/month
- Email notification when threshold exceeded

## FAQ

**Q: Will I lose data if I stop services?**
A: No. All data in databases and storage persists. Only compute stops.

**Q: How quickly can I restart?**
A: Services are ready in 2-3 minutes from stop command.

**Q: Can I stop just one service?**
A: Yes. Edit the PowerShell script and remove services from the list.

**Q: What about the Static Web App?**
A: It has minimal cost (~$0.40/month). Leave running or serve maintenance page.

**Q: Does SQL auto-pause save more?**
A: Yes! SQL Serverless auto-pauses after 1 hour of no queries. Configure in Azure portal.

**Q: Should I disable monitoring when stopped?**
A: No. Keep logging enabled for 30-day retention to track costs.

**Q: Can I stop services via the admin dashboard?**
A: The restart button only restarts a service. Use PowerShell script for full environment shutdown.

## Checklist: Enable Cost Savings

- [ ] Review current monthly bill
- [ ] Test stop script: `manage-environment.ps1 -Action stop`
- [ ] Verify services stopped: `manage-environment.ps1 -Action status`
- [ ] Test start script: `manage-environment.ps1 -Action start`
- [ ] Verify services healthy
- [ ] (Optional) Set up Azure Logic App for scheduling
- [ ] Set up budget alert at $150/month
- [ ] Document your savings goal
- [ ] Track actual savings monthly

## Support

For detailed information, see [[COST_MANAGEMENT.md]] in docs folder.

**Key Files:**
- `scripts/manage-environment.ps1` — PowerShell control script
- `scripts/manage-environment.sh` — Bash control script
- `docs/COST_MANAGEMENT.md` — Complete cost guide
