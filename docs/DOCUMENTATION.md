# EvieAI Documentation Hub

> Central navigation for all EvieAI documentation.  
> Last updated: May 29, 2026

---

## Quick Navigation

### I'm New to EvieAI

Start with these documents in order:

1. **[README.md](../README.md)** (5 min read)
   - Product overview
   - Technology stack
   - Quick start with Docker
   - Key capabilities overview

2. **[docs/FEATURES.md](FEATURES.md)** (15 min read)
   - Complete feature list
   - Capabilities by category
   - Real-world examples
   - Limitations and roadmap

3. **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** (20 min read)
   - System design
   - Component breakdown
   - Data flows
   - Security model

### I'm Deploying EvieAI

Follow these documents for multi-client deployment:

1. **[docs/DEPLOYMENT_CONFIG.md](DEPLOYMENT_CONFIG.md)** (10 min read)
   - Environment variables explained
   - Configuration options
   - Per-client customization

2. **[docs/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** (15 min read)
   - Step-by-step deployment guide
   - Validation checklist
   - Common issues and solutions

3. **[terraform/README.md](../terraform/README.md)** (15 min read)
   - Infrastructure as code
   - Resource provisioning
   - Day-2 operations

4. **[docs/DEPLOYMENT.md](DEPLOYMENT.md)** (20 min read)
   - Detailed deployment walkthrough
   - Azure setup
   - Post-deployment configuration

### I'm Running EvieAI

Operations and support documents:

1. **[docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md)** (Daily reference)
   - Start-of-day checks
   - Service restart procedures
   - Monitoring and alerting
   - Troubleshooting
   - Performance tuning
   - Scaling guidance

2. **[docs/SUPPORT.md](SUPPORT.md)** (Quick reference)
   - Common issues and solutions
   - Health checks
   - Log analysis
   - Data paths

3. **[docs/DR.md](DR.md)** (Emergency reference)
   - Disaster recovery procedures
   - Backup and restore
   - Failover steps
   - Contact escalation

### I'm Integrating with EvieAI

Developer and integration documents:

1. **[docs/API_REFERENCE.md](API_REFERENCE.md)** (Reference)
   - REST API endpoints
   - Request/response schemas
   - Example requests
   - Error codes

2. **[AGENTS.md](../AGENTS.md)** (Reference)
   - Development conventions
   - Repository structure
   - Common patterns
   - Tool explanations

---

## Complete Document Index

### Product & Features
| Document | Purpose | Length | Audience |
|----------|---------|--------|----------|
| [README.md](../README.md) | Overview, quick start, technology stack | 5 min | Everyone |
| [docs/FEATURES.md](FEATURES.md) | Complete feature catalog, examples, roadmap | 15 min | Everyone |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flows, components | 20 min | Architects, Developers |

### Deployment & Configuration
| Document | Purpose | Length | Audience |
|----------|---------|--------|----------|
| [docs/DEPLOYMENT_CONFIG.md](DEPLOYMENT_CONFIG.md) | Environment variables, configuration reference | 10 min | DevOps, Architects |
| [docs/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) | Step-by-step deployment for new clients | 15 min | Site Owners, DevOps |
| [docs/DEPLOYMENT.md](DEPLOYMENT.md) | Detailed deployment walkthrough | 20 min | DevOps Engineers |
| [terraform/README.md](../terraform/README.md) | Infrastructure as code, Terraform operations | 15 min | DevOps, Architects |
| [docs/INSTALL.md](INSTALL.md) | Installation guide (local and cloud) | 10 min | Developers, DevOps |

### Operations & Support
| Document | Purpose | Length | Audience |
|----------|---------|--------|----------|
| [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md) | Daily operations, monitoring, troubleshooting | 30 min | Operators, Admins |
| [docs/SUPPORT.md](SUPPORT.md) | Common issues, health checks, debugging | 10 min | Operators, Support |
| [docs/DR.md](DR.md) | Disaster recovery, backup, failover | 15 min | Site Owners, Operators |

### Development & Integration
| Document | Purpose | Length | Audience |
|----------|---------|--------|----------|
| [docs/API_REFERENCE.md](API_REFERENCE.md) | REST API endpoints, schemas, examples | 20 min | Developers |
| [AGENTS.md](../AGENTS.md) | Repository structure, conventions, patterns | 20 min | Developers |

### Performance & Planning
| Document | Purpose | Contained In |
|----------|---------|--------------|
| Cost estimation | Pricing model, optimization | [docs/ARCHITECTURE.md](ARCHITECTURE.md#11-cost-analysis) |
| Capacity planning | Scaling formula, metrics | [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md#scaling--capacity-planning) |
| Performance tuning | Bottleneck analysis, optimization | [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md#performance-tuning) |
| Multi-tenant setup | Resource isolation, per-client deployment | [docs/ARCHITECTURE.md](ARCHITECTURE.md#14-multi-client-deployment-architecture) |

---

## Documentation by Role

### Site Owner / Deployment Lead
**You're responsible for getting EvieAI running in your organization.**

**Reading list:**
1. [docs/FEATURES.md](FEATURES.md) — Understand what you're deploying
2. [docs/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) — Follow step-by-step guide
3. [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md) (first section) — Daily health checks
4. [docs/DR.md](DR.md) — Plan for emergencies

**Time investment:** 1.5 hours

### Platform Architect / DevOps
**You're designing and provisioning the infrastructure.**

**Reading list:**
1. [docs/ARCHITECTURE.md](ARCHITECTURE.md) — Understand system design
2. [docs/DEPLOYMENT_CONFIG.md](DEPLOYMENT_CONFIG.md) — Configure for your org
3. [terraform/README.md](../terraform/README.md) — Manage IaC
4. [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md) (scaling section) — Plan capacity
5. [AGENTS.md](../AGENTS.md) — Understand code structure for customization

**Time investment:** 3 hours

### Site Reliability Engineer / Operator
**You're running EvieAI day-to-day.**

**Reading list:**
1. [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md) — Keep as desk reference
2. [docs/SUPPORT.md](SUPPORT.md) — Quick troubleshooting
3. [docs/ARCHITECTURE.md](ARCHITECTURE.md#15-observability--monitoring) — Understand monitoring
4. [docs/DR.md](DR.md) — Emergency procedures
5. [README.md](../README.md) (health checks section) — Quick validation

**Time investment:** 2 hours (plus ongoing reference)

### Developer / Integrator
**You're extending EvieAI or building integrations.**

**Reading list:**
1. [docs/FEATURES.md](FEATURES.md) — Know what's available
2. [docs/ARCHITECTURE.md](ARCHITECTURE.md) (components section) — Understand architecture
3. [docs/API_REFERENCE.md](API_REFERENCE.md) — API contract
4. [AGENTS.md](../AGENTS.md) — Code conventions and structure
5. [README.md](../README.md) (development section) — Local setup

**Time investment:** 2 hours plus deep dives

---

## Feature Lookup Table

### Data Sources

| Feature | Docs Location | Status |
|---------|---------------|--------|
| Email search | [docs/FEATURES.md#email-outlook](FEATURES.md#email-outlook) | ✅ Stable |
| OneDrive search | [docs/FEATURES.md#onedrive--sharepoint](FEATURES.md#onedrive--sharepoint) | ✅ Stable |
| File share search | [docs/FEATURES.md#file-share--local-storage](FEATURES.md#file-share--local-storage) | ✅ Stable |
| SQL database query | [docs/FEATURES.md#sql-databases](FEATURES.md#sql-databases) | ✅ Stable |
| Analytics dashboards | [docs/FEATURES.md#analytics--dashboards](FEATURES.md#analytics--dashboards) | ✅ Stable |
| Knowledge base search | [docs/FEATURES.md#knowledge-base-internal](FEATURES.md#knowledge-base-internal) | ✅ Stable |

### Admin & Operations

| Feature | Docs Location | Status |
|---------|---------------|--------|
| Service health dashboard | [docs/FEATURES.md#real-time-health-dashboard](FEATURES.md#real-time-health-dashboard) | ✅ New (v1.5) |
| Service restart (one-click) | [docs/FEATURES.md#one-click-restart](FEATURES.md#one-click-restart) | ✅ New (v1.5) |
| Service restart (API) | [docs/API_REFERENCE.md](API_REFERENCE.md) | ✅ New (v1.5) |
| Approval workflow | [docs/FEATURES.md#approval-workflow](FEATURES.md#approval-workflow) | ✅ Stable |
| Audit logging | [docs/FEATURES.md#logging--audit](FEATURES.md#logging--audit) | ✅ Stable |
| Circuit breakers | [docs/FEATURES.md#reliability-gates--circuit-breakers](FEATURES.md#reliability-gates--circuit-breakers) | ✅ Stable |

### Chat & Conversation

| Feature | Docs Location | Status |
|---------|---------------|--------|
| Multi-turn conversation | [docs/FEATURES.md#multi-turn-conversation](FEATURES.md#multi-turn-conversation) | ✅ Stable |
| Tool call visibility | [docs/FEATURES.md#user-experience](FEATURES.md#user-experience) | ✅ Stable |
| Streaming responses | [docs/FEATURES.md#multi-turn-conversation](FEATURES.md#multi-turn-conversation) | ✅ Stable |
| Report generation | [docs/FEATURES.md#report-generation](FEATURES.md#report-generation) | ✅ Stable |

### Deployment

| Feature | Docs Location | Status |
|---------|---------------|--------|
| Single-client deployment | [docs/DEPLOYMENT.md](DEPLOYMENT.md) | ✅ Stable |
| Multi-client deployment | [docs/ARCHITECTURE.md#14-multi-client-deployment-architecture](ARCHITECTURE.md#14-multi-client-deployment-architecture) | ✅ New (v1.5) |
| Terraform automation | [terraform/README.md](../terraform/README.md) | ✅ Stable |
| Service restart config | [docs/ARCHITECTURE.md#13-service-restart--admin-operations](ARCHITECTURE.md#13-service-restart--admin-operations) | ✅ New (v1.5) |
| Environment variables | [docs/DEPLOYMENT_CONFIG.md](DEPLOYMENT_CONFIG.md) | ✅ New (v1.5) |

---

## Common Questions & Answers

### How do I get started?
→ Read [README.md](../README.md) and run `docker compose up --build`

### What can EvieAI do?
→ See [docs/FEATURES.md](FEATURES.md) for complete feature list

### How do I deploy to Azure?
→ Follow [docs/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) or [docs/DEPLOYMENT.md](DEPLOYMENT.md)

### How do I deploy to multiple clients?
→ See [docs/ARCHITECTURE.md#14-multi-client-deployment-architecture](ARCHITECTURE.md#14-multi-client-deployment-architecture)

### How do I restart a service?
→ See [docs/OPERATIONAL_GUIDE.md#service-restart-procedures](OPERATIONAL_GUIDE.md#service-restart-procedures)

### Something is broken. Where do I start?
→ Check [docs/SUPPORT.md](SUPPORT.md) for troubleshooting

### What's the API?
→ See [docs/API_REFERENCE.md](API_REFERENCE.md)

### How do I contribute?
→ See [AGENTS.md](../AGENTS.md) for development conventions

### How much does it cost?
→ See cost analysis in [docs/ARCHITECTURE.md#11-cost-analysis](ARCHITECTURE.md#11-cost-analysis)

### How do I scale EvieAI?
→ See [docs/OPERATIONAL_GUIDE.md#scaling--capacity-planning](OPERATIONAL_GUIDE.md#scaling--capacity-planning)

---

## Version History

### v1.5 (May 29, 2026)
- ✅ Added service restart capability (admin dashboard + API)
- ✅ Multi-client deployment support with resource isolation
- ✅ Comprehensive documentation update
- ✅ New [docs/FEATURES.md](FEATURES.md) with complete feature list
- ✅ New [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md) with operational procedures
- ✅ New [docs/DOCUMENTATION.md](DOCUMENTATION.md) (this file) — central navigation hub

### v1.4 (Previous)
- Approval workflow
- Reliability gates
- Circuit breaker safety controls
- Multi-source synthesis

### v1.0
- Initial launch
- Chat interface
- Basic MCP tools
- Azure deployment

---

## Contributing to Documentation

**To update this documentation:**

1. Find the relevant document in `/docs/`
2. Update with clear examples and explanations
3. Commit with message: `docs: {brief description}`
4. Link new docs from this hub for discoverability

**Documentation standards:**

- **Headings:** Use `##` for major sections, `###` for subsections
- **Code blocks:** Include language identifier and explanation
- **Tables:** Use for comparisons and reference data
- **Links:** Cross-link related documents
- **Examples:** Show before/after or input/output

---

## Need Help?

- **Questions about features?** → [docs/FEATURES.md](FEATURES.md)
- **Deployment issues?** → [docs/DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
- **Operational problems?** → [docs/OPERATIONAL_GUIDE.md](OPERATIONAL_GUIDE.md)
- **API integration?** → [docs/API_REFERENCE.md](API_REFERENCE.md)
- **Emergency?** → [docs/DR.md](DR.md)

---

**Last updated:** May 29, 2026  
**Maintained by:** EvieAI Platform Team  
**Next review:** June 15, 2026
