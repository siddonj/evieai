# Getting Started with EvieAI

> Your 5-minute quick start guide to EvieAI

## What is EvieAI?

EvieAI is an **AI-powered agentic Q&A platform** that synthesizes answers from multiple enterprise data sources (email, files, databases, dashboards) using a single natural-language question.

**Key benefits:**
- 🤖 One question → Multiple data sources
- ⚡ Instant answers from scattered data
- 📊 Auto-generated reports and briefings
- 🔐 Secure with managed identities and RBAC
- 📱 Works on web, Teams, and via API

## Prerequisites

**For Local Development:**
- Docker Desktop (8+ GB RAM)
- Git
- Bash or PowerShell

**For Azure Deployment:**
- Azure subscription with Owner/Contributor rights
- Terraform installed (`brew install terraform` or `choco install terraform`)
- Azure CLI (`az` command)

## Local Quick Start (5 minutes)

### Step 1: Clone and Configure

```bash
git clone https://github.com/siddonj/evieai.git
cd evieai
cp .env.example .env
```

### Step 2: Edit `.env` (Minimal Setup)

```env
# Azure OpenAI (required)
AZURE_OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=sk-...
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Service restart config
PROJECT_NAME=aiagent2
ENVIRONMENT=dev
RESOURCE_GROUP=rg-aiagent2-dev
AZURE_SUBSCRIPTION_ID=
```

See [[Deployment-Configuration]] for all available variables.

### Step 3: Start the Stack

```bash
docker compose up --build
```

This brings up:
- **Web UI**: http://localhost:5173
- **Orchestrator API**: http://localhost:8000
- **MCP Servers**: Internal services (ports 8001–8007)

### Step 4: Try It Out

Open http://localhost:5173 and ask:
> "What emails are in my inbox?"
> "Show me recent files"
> "Query the customer database"

**Result:** AI queries the right tools and shows you a synthesized answer.

---

## Admin Dashboard

After starting the stack, visit **http://localhost:5173/admin** to see:

✅ **Service Health Monitor**
- Real-time status of all services
- Restart buttons for each service
- Health check history

✅ **Approvals & Actions**
- Pending write-back approvals
- Action history and logs

✅ **Metrics & Reliability**
- Success rates by tool
- Connector sync status
- Circuit breaker state

---

## Next Steps

| Goal | Page |
|------|------|
| Understand capabilities | [[Features]] |
| Learn system design | [[Architecture]] |
| Deploy to Azure | [[Deployment-Checklist]] |
| Deploy to multiple clients | [[Architecture]] (multi-client section) |
| Run in production | [[Operations]] |
| Troubleshoot issues | [[Troubleshooting]] |
| Integrate via REST API | [[API-Reference]] |

---

## Common First Questions

**Q: Does it work with my Azure OpenAI instance?**  
A: Yes! Set `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_API_KEY` in `.env`

**Q: Can I connect to our company database?**  
A: Yes. See [[Features]] → Data Integration → SQL Databases

**Q: Can I query our files on OneDrive?**  
A: Yes. Requires Graph API setup. See [[Deployment-Configuration]]

**Q: How do I restart a service if it crashes?**  
A: Click the restart button in the admin dashboard. See [[Service-Restart]]

**Q: Can I use this in production?**  
A: Yes! See [[Deployment-Checklist]] for multi-client deployment.

---

## Architecture Diagram

```
┌─────────────────────────────────────────┐
│         User Layer                      │
│  Web Browser   │   Microsoft Teams      │
└────────┬───────┼───────────┬────────────┘
         │       │           │
         │ HTTPS │ OAuth 2.0 │
         ▼       ▼           ▼
┌──────────────────────────────────────────┐
│  Orchestrator (FastAPI)                  │
│  • Chat endpoint                         │
│  • Tool routing                          │
│  • Report generation                     │
│  • Service restart                       │
└──────┬───────────────────┬───────────────┘
       │                   │
       ▼                   ▼
┌─────────────────────────────────────────┐
│  MCP Servers (Internal Only)             │
│  • SQL Query  • Email Search             │
│  • File Share • OneDrive Search          │
│  • Analytics  • Knowledge Base           │
└──────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  Data & Services                         │
│  • Azure SQL  • Azure OpenAI             │
│  • Storage    • Key Vault                │
│  • Graph API  • Log Analytics            │
└──────────────────────────────────────────┘
```

---

## Health Checks

Verify everything is running:

```bash
# Service health
curl http://localhost:8000/health

# All dependencies ready
curl http://localhost:8000/ready

# Metrics
curl http://localhost:8000/metrics
```

---

## Troubleshooting

**Service won't start?**
```bash
# Check logs
docker compose logs orchestrator

# Restart everything
docker compose down && docker compose up --build
```

**Can't reach local services?**
```bash
# Make sure Docker has 8+ GB RAM available
# Check: Docker Desktop → Settings → Resources
```

**OpenAI error?**
- Verify `AZURE_OPENAI_ENDPOINT` is correct
- Check `AZURE_OPENAI_API_KEY` is valid
- Confirm `AZURE_OPENAI_DEPLOYMENT` matches your Azure setup

See [[Troubleshooting]] for more help.

---

## Next: [[Features]]

Ready to dive deeper? Check out what EvieAI can do!
