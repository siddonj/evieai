# AI Agentic Q&A Platform — Executive Summary

> **One-pager for stakeholders and decision-makers**  
> ResiQ  |  May 2026

---

## The Problem

Employees waste hours every week hunting for information across disconnected systems — emails, file shares, databases, OneDrive, and analytics dashboards. By the time they find the answer, the decision window has closed.

## The Solution

**ResiQ** is an AI-powered agentic Q&A platform. A user types one natural-language question; the system reasons over the request, calls the right backend tools in parallel, and returns a synthesized answer — or a full briefing document — in seconds.

**Live today:** https://demo.resiq.co

---

## How It Works (30-Second Version)

1. **User asks** a question in the chat UI (web or Teams)
2. **Orchestrator** sends the request to Azure OpenAI GPT-4o with a catalog of available "tools"
3. **OpenAI decides** which tools to call — e.g., query mail, query analytics, query files
4. **MCP servers** execute the tool calls in parallel against real data sources
5. **OpenAI synthesizes** the raw results into a single, natural-language answer
6. **User gets** the answer, tool-call badges, and an optional downloadable report

---

## Architecture at a Glance

```
User (Web / Teams)
       │
       ▼
┌─────────────────┐
│  Static Web App │  ← React UI, CDN edge
│   (public)      │
└────────┬────────┘
         │ HTTPS
         ▼
┌─────────────────┐
│  Orchestrator   │  ← FastAPI + Azure OpenAI GPT-4o
│   (public)      │     Discovers 8 backend tools
└────────┬────────┘
         │ Streamable HTTP (internal VNet)
         ▼
┌─────────────────────────────────────────┐
│  8 MCP Servers (Container Apps)         │
│  SQL • Mail • OneDrive • Files          │
│  Analytics • Knowledge Base • Memory    │
│  Document Generation                    │
└─────────────────────────────────────────┘
         │
    ┌────┴────┬──────────┬────────┐
    ▼         ▼          ▼        ▼
 Azure SQL   MS Graph   Storage   APIs
```

**Key design principle:** The orchestrator is the only public-facing service. All data-access backends are internal-only and unreachable from the internet.

---

## What Can It Do Today?

| Use Case | Example Question | Tools Called |
|----------|-----------------|--------------|
| **Email Intelligence** | "Show unread finance emails with action items" | `query_mail` |
| **Revenue Reports** | "Find Q2 revenue reports in OneDrive" | `query_onedrive` |
| **File Search** | "List all Excel files in the finance share" | `query_files` |
| **Sales Pipeline** | "What is the Q2 pipeline vs. quota?" | `query_analytics` + `query_sql` |
| **Board Prep** | "Prep a board briefing with revenue, pipeline, and risks" | Multi-tool (4+ sources) |
| **SOP Lookup** | "What are the security incident response steps?" | `query_knowledge_base` |
| **Document Gen** | "Generate a 5-page board briefing with action items" | `query_document_generation` |

All 11 demo scenarios pass end-to-end.

---

## Azure Infrastructure (Terraform-Managed)

| Resource | Purpose |
|----------|---------|
| **10 Container Apps** | Orchestrator + 8 MCP servers + SQL adapter |
| **Azure OpenAI** | GPT-4o chat completions with tool-calling |
| **Azure SQL Serverless** | CRM, pipeline, and transactional data |
| **Storage Account** | File shares for the File Share MCP |
| **Key Vault** | All secrets injected at runtime (never in images) |
| **Static Web App** | React UI with global CDN |
| **Log Analytics** | Central logging and metrics |

**Deploy time:** `terraform apply` from a clean checkout takes ~10–15 minutes.

---

## Cost Estimate

| Environment | Monthly Cost | Notes |
|-------------|-------------|-------|
| **Development** | **$145 – $280** | Optimizable to ~$60–$110 with scale-to-zero |
| **Production (100+ users)** | **$980 – $1,650** | Includes Redis cache, always-on SQL, higher OpenAI TPM |

---

## Porting to a New Tenant

| Phase | Duration |
|-------|----------|
| Infrastructure (Terraform) | 3–4 days |
| Data integration (real sources) | 8–12 days |
| Testing & UAT | 5–8 days |
| Go-live + hypercare | 3–5 days |
| **Total** | **~4 – 6 weeks** |

**Data audit prerequisite:** 5–7 days (small org) to 15–25 days (large enterprise) depending on number of sources and compliance requirements.

---

## Security Highlights

- **Network:** MCP servers are internal-only; orchestrator is the sole public face
- **Identity:** System-assigned managed identities; no secrets in container runtime config
- **Secrets:** Azure Key Vault with RBAC; encrypted injection into Container Apps
- **Data:** Parameterized SQL via DAB; least-privilege Graph API scopes
- **Auth:** Teams SSO / On-Behalf-Of flow (feature-flagged)

---

## Next Steps

1. **Review** this summary and the full `ARCHITECTURE.md`
2. **Schedule** a 30-minute demo (live at demo.resiq.co)
3. **Initiate** data audit for target tenant
4. **Plan** pilot group (5–10 users) for UAT

---

*For technical details, see `ARCHITECTURE.md`, `AGENTS.md`, and `GAPS.md` in the repo.*
