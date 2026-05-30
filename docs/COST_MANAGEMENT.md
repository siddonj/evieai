# EvieAI Cost Management Guide

## Overview
Running EvieAI 24/7 has significant Azure costs. This guide shows how to reduce costs by 80-90% when the application is not in use.

## Cost Breakdown

### Monthly Cost - All Running (24/7)

| Component | Type | Cost/Month | Notes |
|-----------|------|-----------|-------|
| **Container Apps** | Compute | $140-160 | 12 services × 0.5 vCPU × 730 hours |
| SQL Serverless | Compute | $20-30 | Auto-pauses when idle |
| Storage Account | Storage | $10-15 | Blobs, file shares, tables |
| Key Vault | Management | $0.60 | Monthly minimum |
| Log Analytics | Monitoring | $15-25 | Data ingestion & retention |
| Application Insights | Monitoring | $5-10 | Optional |
| **TOTAL (24/7)** | | **$190-240** | Running continuously |

### Monthly Cost - Shutdown

| Component | Type | Cost/Month | Notes |
|-----------|------|-----------|-------|
| **Container Apps** | Compute | **$0** | Scaled to 0 replicas |
| SQL Serverless | Compute | **$0** | Auto-paused (no queries) |
| Storage Account | Storage | $10-15 | Still storing files/data |
| Key Vault | Management | $0.60 | Still configured |
| Log Analytics | Monitoring | $2-5 | Minimal retention |
| Application Insights | Monitoring | $0-2 | Minimal ingestion |
| **TOTAL (Stopped)** | | **$13-23** | Most services stopped |

### Potential Savings
- **Running 24/7:** ~$200/month = $2,400/year
- **Running 8 hours/day:** ~$67/month = $804/year (savings: $1,600/year)
- **Running weekdays only:** ~$95/month = $1,140/year (savings: $1,260/year)

## How It Works

### Scaling to 0 Replicas
When you set min/max replicas to 0 on a Container App, Azure:
- Stops all running instances
- Stops charging compute costs
- Keeps the app definition intact
- Allows restart within 30 seconds

### What Remains Running
- **Static Web App** (UI) - Minimal costs, ~$0.40/month
- **Storage Account** - Always needed for data
- **Key Vault** - Always needed for secrets
- **SQL Database** - Auto-pauses on inactivity

## Cost Management Scripts

### PowerShell (Windows)
```powershell
# Start the environment
.\scripts\manage-environment.ps1 -Action start

# Check status
.\scripts\manage-environment.ps1 -Action status

# Stop the environment
.\scripts\manage-environment.ps1 -Action stop
```

### Bash (Linux/Mac)
```bash
# Make executable
chmod +x scripts/manage-environment.sh

# Start the environment
./scripts/manage-environment.sh start

# Check status
./scripts/manage-environment.sh status

# Stop the environment
./scripts/manage-environment.sh stop
```

## Startup/Shutdown Times

| Action | Time | Impact |
|--------|------|--------|
| **Stop** (scale to 0) | 30-60 seconds | Services terminate gracefully |
| **Start** (scale to 1) | 60-120 seconds | Services pull image and start |
| **Full Ready** | 2-3 minutes | Health checks pass, API ready |

## Cost Optimization Strategies

### Strategy 1: Manual On-Demand
- Stop services when not actively using
- Start services 1-2 minutes before needed
- Best for: Development/testing
- Savings: 80-90%

### Strategy 2: Schedule-Based (Recommended)
- Automatically stop at 6 PM each day
- Automatically start at 8 AM each day
- Use Azure Automation or Azure Logic Apps
- Best for: Business hours only use
- Savings: 65-70%

### Strategy 3: Hybrid
- Stop weekends and evenings
- Stop during lunch hours
- Run full capacity during peak usage
- Best for: Enterprise with specific usage patterns
- Savings: 50-60%

## Implementing Scheduled Shutdown

### Option A: Azure Function on Schedule
```powershell
# Create an Azure Function that runs daily at 6 PM
az functionapp create --resource-group rg-aiagent2-dev \
  --consumption-plan-location eastus \
  --runtime powershell \
  --functions-version 4 \
  --name "stop-evieai-scheduler"

# Set timer trigger: 0 0 18 * * * (6 PM daily)
```

### Option B: Azure Automation
1. Create automation account
2. Create runbook with script content
3. Create schedule: Daily at 6 PM and 8 AM
4. Total cost: ~$15/month (breakeven at 1 hour daily savings)

### Option C: Azure Logic Apps (Easiest)
1. Create Logic App
2. Add "Recurrence" trigger (6 PM daily)
3. Add action: "Run script" → call your stop script
4. Repeat for 8 AM start
5. Cost: ~$0.50/month (free tier mostly)

## Monitoring Costs

### View Current Spending
```bash
# Last 30 days
az consumption usage list --query "[].{date:usageStart, amount:billableAmount}" -o table

# By service
az consumption usage list --query "[].{service:meterCategory, cost:billableAmount}" -o table
```

### Set Budget Alerts
```bash
# Create budget with alert at $150/month
az costmanagement budget create --resource-group rg-aiagent2-dev \
  --name "EvieAI Monthly Budget" \
  --category "Cost" \
  --amount 150 \
  --time-grain "Monthly"
```

## Checklist for Cost Optimization

- [ ] Review current monthly costs
- [ ] Choose cost strategy (on-demand vs scheduled)
- [ ] Test stop script: `manage-environment.ps1 -Action stop`
- [ ] Verify services stopped: `manage-environment.ps1 -Action status`
- [ ] Test start script: `manage-environment.ps1 -Action start`
- [ ] Verify services running and healthy
- [ ] For scheduled: Set up Azure Logic App or Automation
- [ ] Set up budget alerts in Azure portal
- [ ] Document your cost savings

## FAQ

**Q: Will data be lost if I stop services?**
A: No. Data in databases, storage, and Key Vault persists. Only running instances stop.

**Q: How long does startup take?**
A: Typically 2-3 minutes from stop command to fully healthy.

**Q: Can I stop individual services?**
A: Yes, modify the script to only stop specific services.

**Q: What about the Static Web App (UI)?**
A: It has minimal cost (~$0.40/month). You can leave it running or use DNS redirect to maintenance page.

**Q: Does auto-pause on SQL Database save more?**
A: Yes, SQL auto-pauses when idle. Configure auto-pause delay to 1 hour for maximum savings.

**Q: Should I stop services during testing?**
A: Only if you want to test startup/shutdown behavior. Otherwise leave running for efficiency.

## Recommendations

1. **Development:** Use manual stop/start when not actively developing
2. **Staging:** Use scheduled stop (off-hours) or keep running
3. **Production:** Keep running unless low traffic periods
4. **Testing:** Use manual control + isolated test environment

## Next Steps

1. Run `manage-environment.ps1 -Action status` to verify script works
2. Stop services manually: `manage-environment.ps1 -Action stop`
3. Monitor your Azure bill to confirm savings
4. If recurring pattern emerges, set up Azure Logic App for automation
5. Review quarterly to optimize schedule based on actual usage

## Support

For issues:
- Check that all Container Apps exist: `az containerapp list -g rg-aiagent2-dev`
- Verify Azure CLI is installed: `az --version`
- Check authentication: `az account show`
