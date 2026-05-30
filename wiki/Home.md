# EvieAI Documentation Wiki

Welcome to the EvieAI wiki! This is your comprehensive guide to understanding, deploying, and operating the AI-powered agentic Q&A platform.

## Quick Navigation

### 👋 New to EvieAI?
Start with these pages in order:
1. **[Getting Started](wiki/Getting-Started)** — Overview and 5-minute quick start
2. **[Features Overview](wiki/Features)** — What EvieAI can do
3. **[Architecture](wiki/Architecture)** — How it works

### 🚀 Deploying EvieAI?
Follow these for multi-client deployment:
1. **[Deployment Configuration](wiki/Deployment-Configuration)** — Environment setup
2. **[Deployment Checklist](wiki/Deployment-Checklist)** — Step-by-step guide
3. **[Infrastructure as Code](wiki/Infrastructure)** — Terraform details

### ⚙️ Running EvieAI?
Operations and support:
1. **[Operations Guide](wiki/Operations)** — Daily checks, monitoring, restart procedures
2. **[Service Restart](wiki/Service-Restart)** — One-click service recovery
3. **[Cost Management](wiki/Cost-Management)** — Reduce costs 80-90% when not in use
4. **[Troubleshooting](wiki/Troubleshooting)** — Common issues and solutions
5. **[Disaster Recovery](wiki/Disaster-Recovery)** — Emergency procedures

### 💻 Integrating with EvieAI?
Developer resources:
1. **[API Reference](wiki/API-Reference)** — REST endpoints
2. **[Architecture](wiki/Architecture)** — System design details

---

## Key Capabilities

- 🤖 **Agentic Q&A** — AI reasons over available data sources
- 🔗 **Multi-Source** — Query email, files, databases, dashboards simultaneously
- 📊 **Report Generation** — Automated briefings and exports
- 🔐 **Secure** — Managed identities, encrypted secrets, RBAC
- 📱 **Multi-Channel** — Web UI, Teams integration, REST API
- ⚙️ **Operational** — Admin dashboard with service monitoring and restart
- 🌍 **Multi-Tenant** — Deploy to multiple client organizations

---

## Latest Updates (v1.5 — May 29, 2026)

✨ **New Features**
- Service restart from admin dashboard (one-click or API)
- Multi-client deployment with resource isolation
- Cost management: Stop services when not in use (save 80-90%)
- Comprehensive operational procedures
- Enhanced monitoring and alerting

📚 **Documentation**
- New [Features Overview](wiki/Features) page
- New [Operations Guide](wiki/Operations) with daily procedures
- New [Cost Management](wiki/Cost-Management) with stop/start scripts
- New [Deployment Configuration](wiki/Deployment-Configuration) with examples
- Updated [Architecture](wiki/Architecture) with multi-client details

---

## Documentation Map

| Page | Purpose | Audience |
|------|---------|----------|
| [Getting Started](wiki/Getting-Started) | Quick intro and setup | Everyone |
| [Features Overview](wiki/Features) | Complete feature list | Everyone |
| [Architecture](wiki/Architecture) | System design and data flows | Architects, Developers |
| [Deployment Configuration](wiki/Deployment-Configuration) | Environment variable reference | DevOps, Architects |
| [Deployment Checklist](wiki/Deployment-Checklist) | Multi-client deployment steps | Site Owners, DevOps |
| [Infrastructure](wiki/Infrastructure) | Terraform and IaC details | DevOps Engineers |
| [Operations Guide](wiki/Operations) | Daily operations and monitoring | Operators, Admins |
| [Service Restart](wiki/Service-Restart) | Admin dashboard restart procedures | Operators |
| [Cost Management](wiki/Cost-Management) | Stop/start services, save 80-90% | Site Owners, Finance |
| [Troubleshooting](wiki/Troubleshooting) | Common issues and fixes | Operators, Support |
| [Disaster Recovery](wiki/Disaster-Recovery) | Emergency procedures | Site Owners, Operators |
| [API Reference](wiki/API-Reference) | REST API endpoints | Developers |

---

## Common Questions

**Q: How do I get started?**  
→ Go to [Getting Started](wiki/Getting-Started) and run `docker compose up --build`

**Q: What can EvieAI do?**  
→ See [Features Overview](wiki/Features) for the complete feature list

**Q: How do I deploy to Azure?**  
→ Follow [Deployment Checklist](wiki/Deployment-Checklist)

**Q: How do I deploy to multiple clients?**  
→ See [Architecture](wiki/Architecture) section on multi-client deployment

**Q: How do I restart a service?**  
→ See [Service Restart](wiki/Service-Restart) page

**Q: Something is broken. Where do I start?**  
→ Check [Troubleshooting](wiki/Troubleshooting)

**Q: How do I reduce costs?**  
→ See [Cost Management](wiki/Cost-Management) — save 80-90% by stopping services

**Q: What's the API?**  
→ See [API Reference](wiki/API-Reference)

---

## Support & Contact

- **Feature questions?** → See [Features Overview](wiki/Features)
- **Deployment issues?** → See [Deployment Checklist](wiki/Deployment-Checklist)
- **Operational problems?** → See [Operations Guide](wiki/Operations)
- **Need emergency help?** → See [Disaster Recovery](wiki/Disaster-Recovery)

---

## Repository Structure

```
evieai/
├─ README.md                    ← Quick start
├─ ARCHITECTURE.md              ← High-level design
├─ docker-compose.yml           ← Local dev environment
├─ pyproject.toml               ← Python config
│
├─ docs/                        ← Detailed documentation
│  ├─ FEATURES.md               ← Feature reference
│  ├─ DEPLOYMENT_CONFIG.md      ← Configuration guide
│  ├─ DEPLOYMENT_CHECKLIST.md   ← Deployment steps
│  ├─ DEPLOYMENT.md             ← Detailed deployment
│  ├─ OPERATIONAL_GUIDE.md      ← Operations manual
│  ├─ SUPPORT.md                ← Troubleshooting
│  ├─ API_REFERENCE.md          ← API docs
│  └─ DR.md                     ← Disaster recovery
│
├─ .wiki/                       ← Wiki (this content)
│
├─ orchestrator/                ← FastAPI core
│  ├─ app/
│  └─ requirements.txt
│
├─ mcp_servers/                 ← Data/tool services
│  ├─ sql/
│  ├─ file_share/
│  ├─ o365_mail/
│  └─ ...
│
├─ web_ui/                      ← React frontend
│  ├─ src/
│  └─ package.json
│
└─ terraform/                   ← Infrastructure
   ├─ main.tf
   └─ README.md
```

---

**Last Updated:** May 29, 2026  
**Version:** 1.5  
**Status:** Production Ready
