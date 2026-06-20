# EvieAI Features & Capabilities

> Comprehensive feature list for EvieAI — the AI-powered agentic Q&A platform.  
> Last updated: May 29, 2026

---

## Table of Contents

1. [Chat & Conversation](#chat--conversation)
2. [Data Integration](#data-integration)
3. [Agentic Reasoning](#agentic-reasoning)
4. [Report Generation](#report-generation)
5. [Administration & Operations](#administration--operations)
6. [Security & Compliance](#security--compliance)
7. [Deployment & Scalability](#deployment--scalability)
8. [Developer Experience](#developer-experience)

---

## Chat & Conversation

### Multi-Turn Conversation
- **Context persistence** — Full conversation history sent with each request, enabling LLM to understand cross-turn references
- **Streaming responses** — Answers stream to UI in real-time as data arrives, not waiting for complete synthesis
- **Message history** — UI stores and displays conversation timeline with user avatars and timestamps
- **Session management** — Isolate chat sessions by user or organization (optional feature-flag)

### Natural Language Interface
- **Plain English queries** — No special syntax; ask questions the way humans naturally speak
- **Multi-language ready** — LLM supports English, Spanish, French, Mandarin, and others
- **Semantic understanding** — "emails from Q2" and "June-July-August messages" both understood correctly
- **Spell tolerance** — Minor misspellings don't break queries

### User Experience
- **Dark theme UI** — Reduces eye strain in long work sessions
- **Markdown rendering** — Code blocks, tables, lists rendered beautifully
- **Tool call visibility** — Badges show which systems were queried ("📧 query_mail", "📊 query_analytics")
- **Evidence-first work packets** — Chat responses can include a structured summary with reconciliation status, source-based evidence cards, suggested actions, and export affordances
- **Copy-to-clipboard** — One-click copy of answers for pasting into reports/emails
- **Mobile responsive** — Works on tablets and phones (web UI)

---

## Data Integration

### Microsoft 365

#### Email (Outlook)
- **Full mailbox search** — Query across all folders (Inbox, Sent, Archive, etc.)
- **Advanced filters** — By sender, date range, subject, keywords, unread status
- **Attachments** — Identify and count attachments, extract metadata
- **Multi-account** — Retrieve mailbox data for the authenticated user
- **Rate limiting** — Handles Microsoft Graph API throttling automatically

**Example queries:**
- "Show me all unread emails from my manager"
- "Find emails about the Q2 revenue report from last month"
- "What feedback did the product team send me?"

#### OneDrive & SharePoint
- **File search** — Query file names, metadata, modification dates
- **Document preview** — Retrieve content snippets for context
- **Shared files** — Access files shared with the user
- **Folder structure awareness** — Understand hierarchy and relationships
- **Version history** — Track document versions and changes

**Example queries:**
- "Show me the latest marketing deck"
- "Find Excel files with 'budget' in the name"
- "What documents did Sarah share with me?"

#### Teams Integration (Optional)
- **Sideloaded tab** — EvieAI available as a Teams tab in any channel
- **SSO login** — Transparent Entra ID authentication (no extra login)
- **Context awareness** — Know which team/channel context for sharing results
- **Rich formatting** — Send formatted messages and adaptive cards back to Teams

### SQL Databases

#### Data Query Capability
- **Parameterized queries** — Safe SQL execution via Microsoft Data API Builder
- **Schema flexibility** — No code changes needed to add new database tables
- **Complex joins** — Multi-table aggregations and relationships supported
- **Performance** — Serverless SQL auto-scales for variable workloads

**Example queries:**
- "Show me Q2 sales by region"
- "List the top 10 customers by revenue"
- "What contracts expire in the next 30 days?"

#### Data Types Supported
- Numbers, text, dates, booleans
- JSON columns (nested data)
- Time series data
- Geospatial data (with extensions)

### File Share & Local Storage

#### File Search
- **Full-text search** — Search file names and content
- **Format support** — PDF, Word, Excel, PowerPoint, text, JSON, CSV
- **Metadata extraction** — File size, modification date, author
- **Directory structure** — Understand folder hierarchy

**Example queries:**
- "Find all PDFs about compliance"
- "Show me Excel files modified in the last week"
- "Search the Finance folder for 'tax'"

### Analytics & Dashboards

#### Pre-Calculated Metrics
- **KPI cards** — Revenue, growth %, conversion rate, etc.
- **Trend analysis** — Week-over-week, month-over-month comparisons
- **Forecasts** — Predictive insights (e.g., "revenue on track to hit $5M this quarter")
- **Benchmarks** — Compare performance against goals or competitors

**Example queries:**
- "What's our Q2 revenue trend?"
- "Are we on track to hit the $10M annual target?"
- "Show me top products by sales"

### Knowledge Base (Internal)

#### Semantic Search
- **SOP search** — Find relevant standard operating procedures
- **Policy lookup** — Answer compliance questions automatically
- **FAQ indexing** — Quick answers to frequently asked questions
- **Best practices** — Suggest relevant guides and recommendations

**Example queries:**
- "What's the process for onboarding a new vendor?"
- "What are the data retention policies?"
- "How do we handle customer escalations?"

---

## Agentic Reasoning

### Tool Selection
- **Automatic routing** — LLM decides which data sources to query
- **Parallel execution** — Multiple tools called simultaneously for speed
- **Dependency awareness** — Understand tool call order (e.g., get customer ID before querying orders)
- **Error recovery** — Graceful fallbacks if a tool fails

### Multi-Source Synthesis
- **Unified context** — Combine results from 5+ sources into one answer
- **Relevance ranking** — Prioritize most relevant results for the user
- **Contradiction resolution** — Flag if different sources disagree
- **Source attribution** — Tell user which systems provided each fact

### Conversation Management
- **Question clarification** — Ask follow-up questions if query is ambiguous
- **Context awareness** — Remember prior answers within conversation
- **Scope validation** — Warn if query is too broad or outside system capabilities
- **Suggestion** — Proactively suggest related queries ("Next, you might ask...")

### Reliability & Safety
- **Hallucination prevention** — Cite sources for all facts
- **Confidence scoring** — Indicate uncertainty ("I found 3 matches, but none are exact")
- **Rate limiting** — Prevent tool call loops or runaway queries
- **Timeout handling** — Graceful degradation if a tool is slow

---

## Report Generation

### Automated Briefing Creation
- **Multi-section documents** — Executive summary, details, action items, appendices
- **HTML output** — Print-ready, email-friendly formatting
- **Custom templates** — Jinja2 templates for branded reports
- **Data visualization** — Tables, charts, and key metrics highlighted

### Report Types
- **Board meeting prep** — Compiled from multiple sources (email, analytics, documents)
- **Daily digest** — Curated highlights from overnight emails and updates
- **Compliance report** — SOPs and policies extracted and formatted
- **Customer briefing** — Account summary with key metrics and contacts

**Example:**
```
Board Meeting Briefing — Q2 2026

📊 Executive Summary
  • Revenue: $4.2M (+12% YoY)
  • Customer churn: 2.1% (stable)
  • Product roadmap: 8/12 features complete

📧 Recent Communication
  • Board member John Smith sent 3 emails
  • CFO Mary Johnson forwarded 2 budget updates
  • Key question: "Are we tracking for Series B?"

✅ Action Items
  • Prepare investor deck by Friday
  • Finalize Q3 budget
  • Schedule board dinner Thursday 6pm
```

### Export Options
- **HTML** — View in browser, print to PDF
- **PDF** — Direct generation (future enhancement)
- **Email** — Send directly to recipients
- **Sharing** — Copy link to share with read-only access
- **Work packet consistency** — Export suggestions can be driven from the same structured packet shown in chat, so summary and evidence stay aligned

### Governed Document Workflows
- **Document drafting from work packets** — Executive briefings, board reports, and operational reports can be drafted from grounded chat outcomes.
- **Approval at finalization** — Drafting stays fast, but final export requires explicit user approval with destination and format selection.
- **Recorded execution chain** — Approved artifacts can be stored to a selected destination and followed by a recorded announcement action.

---

## Administration & Operations

### Service Monitoring

#### Real-Time Health Dashboard
- **Service status** — Green/yellow/red for orchestrator and all MCP servers
- **Response times** — Latency metrics for each service
- **Error rates** — % of failed requests in last hour
- **Last restart** — Timestamp of most recent restart event
- **Uptime** — % availability over 7/30 days

#### Health Check Endpoints
```bash
# Liveness probe — service is running
GET /health
→ {status: "healthy"}

# Readiness probe — all dependencies reachable
GET /ready
→ {status: "ready", dependencies: {
    "openai": "reachable",
    "sql_mcp": "reachable",
    "mail_mcp": "reachable",
    ...
  }}

# Detailed metrics
GET /metrics
→ [Prometheus-format metrics]
```

### Service Restart Capability

#### One-Click Restart
- **From admin UI** — Click "Restart" button on any service card
- **Graceful shutdown** — Waits for in-flight requests to complete (with timeout)
- **Automatic reimage** — Pulls fresh container image
- **Health validation** — Confirms service is healthy before returning
- **No downtime** — Orchestrator remains available; only target service restarted

#### Restart Scoping
- **Multi-client isolation** — Each client can only restart their own services
- **Audit trail** — All restart events logged with timestamp, initiator, outcome
- **Rate limiting** — Prevent restart loops (e.g., max 1 restart per service per minute)
- **Rollback** — If restart fails, reverts to previous stable revision

**Example admin flow:**
```
1. Admin sees "SQL MCP — red (unhealthy)"
2. Clicks "Restart SQL MCP"
3. UI shows "Restarting... please wait"
4. Service restarts (~10 seconds)
5. UI shows "✓ Restarted at 14:32:45 UTC"
6. Health re-checked automatically
```

### Approval Workflow

#### Pending Approvals List
- **Action type** — "Delete customer record", "Bulk email to list", etc.
- **Requester** — Who initiated the action
- **Timestamp** — When request was made
- **Details** — What exactly will happen
- **Approve/Reject buttons** — One-click action

#### Audit Trail
- **Full history** — All approvals/rejections with decision maker
- **Timestamp** — Exact time of decision
- **Reason** — Optional comment from approver
- **Execution log** — Did the approved action succeed?

### Reliability Gates & Circuit Breakers

#### Reliability Metrics
- **Action success rate** — % of actions that executed without error
- **Tool timeout rate** — % of tool calls that exceeded time limit
- **Connector backlog** — Pending sync jobs in queue
- **Error threshold** — Configurable limit (e.g., stop querying DB if error rate > 10%)

#### Automatic Failsafes
- **Circuit breaker (open)** — If error rate exceeds threshold, stop using that tool
- **Fallback** — Route query to alternative data source
- **Throttling** — Reduce request rate if service is overloaded
- **Bypass** — Admin can manually disable/enable tools

**Example:** If SQL MCP has 5 consecutive timeouts, circuit breaker opens, and future queries skip SQL until manual reset.

---

## Security & Compliance

### Authentication & Authorization

#### Identity Management
- **Entra ID SSO** — Transparent login via Microsoft Entra (Teams, web)
- **No credential storage** — No passwords in environment variables
- **Token refresh** — Automatic OAuth token refresh on expiry
- **Session isolation** — Each user has independent conversation history

#### Role-Based Access Control (RBAC)
- **Admin role** — Can restart services, approve actions, view audit logs
- **Power user role** — Can chat, generate reports, approve simple actions
- **Read-only role** — Can view dashboards and knowledge base only
- **Custom roles** — Define fine-grained permissions per organization

### Data Protection

#### Encryption
- **In transit** — All connections use HTTPS/TLS 1.2+
- **At rest** — Secrets stored in Azure Key Vault (encrypted with service-managed keys)
- **Database** — Transparent Data Encryption (TDE) for SQL Server
- **Backups** — Encrypted storage of database backups

#### Data Isolation
- **Multi-tenant** — Each client's data stored in separate resource group
- **No cross-tenant access** — Service-level isolation via Azure RBAC
- **Query parameterization** — Prevents SQL injection
- **Scope limiting** — User can only see mail/files they own or have access to

### Compliance

#### Logging & Audit
- **Comprehensive audit trail** — All chat sessions, approvals, restarts logged
- **Retention** — 90-day default retention (configurable per client)
- **Export** — Audit logs exportable for compliance review
- **KQL queries** — Pre-built queries for compliance reporting

#### Data Residency
- **Regional selection** — Deploy to Azure region of choice (US, Europe, Asia-Pac)
- **Data sovereignty** — Compliance with regional data residency laws
- **GDPR support** — Right to deletion, data export, consent management
- **Backup locations** — Geo-redundant backup with configurable regions

#### Permissions Model
- **Graph API scopes** — Least privilege: Mail.Read, Files.Read.All (not Write)
- **SQL permissions** — Read-only database user for queries
- **Key Vault access** — Managed identity only, no explicit credentials
- **Storage access** — Shared Access Signature (SAS) with time-limited tokens

---

## Deployment & Scalability

### Infrastructure

#### Compute
- **Container Apps** — Serverless, auto-scaling microservices
- **Min replicas: 0** — Pay only when running (consumption pricing)
- **Max replicas: 5–10** — Scale horizontally under load
- **CPU/Memory** — 0.5 vCPU / 1 GiB per container (configurable)

#### Storage
- **Azure SQL Serverless** — Database auto-pauses after 1 hour inactivity
- **Azure Blob Storage** — File shares, backups, generated reports
- **Key Vault** — Secrets with automatic rotation capability
- **Log Analytics** — Centralized logging and monitoring

#### Networking
- **Public ingress** — Only orchestrator `/api/chat` endpoint is public
- **Internal-only MCPs** — All data services unreachable from internet
- **VNet isolation** — Optional VNet for complete network isolation
- **Managed identity** — Services authenticate without credentials

### Multi-Tenant Deployment

#### Resource Isolation
- **Separate resource groups** — Each client has own RG (rg-{client}-{env})
- **Independent Container Apps** — One orchestrator + 8 MCPs per client
- **Dedicated databases** — Each client has isolated SQL and PostgreSQL
- **Separate Key Vaults** — No shared secrets between clients

#### Terraform Automation
- **Client-specific tfvars** — `terraform/clients/{client}/terraform.tfvars`
- **Modular modules** — Reusable Bicep modules for consistency
- **State per client** — Separate state files, no cross-contamination
- **Output documentation** — Terraform outputs saved to client deployment folder

### Scaling Metrics

#### Horizontal Scaling (Replicas)
- **1K chat requests/day** — Min 0, avg 1 replica
- **10K chat requests/day** — Min 1, avg 2–3 replicas
- **100K chat requests/day** — Min 2, avg 5–10 replicas
- **CPU throttling** — Automatic if exceeds 80% on all replicas

#### Database Scaling
- **Small (<100 users)** — GP_S_Gen5_2 serverless (auto-pause)
- **Medium (100–1K users)** — GP_Gen5_4 (always-on)
- **Large (>1K users)** — GP_Gen5_8 or higher
- **Compute scaling** — Instant without downtime

### Cost Optimization

#### Consumption Pricing
- **Container Apps** — $0.024 per vCPU-second
- **SQL Serverless** — $0.000035 per second (paused: $0)
- **Storage** — $0.0184 per GB/month
- **Data transfer** — Free within region

#### Budget Controls
- **Per-client budgets** — Set spending limits per client
- **Alerts** — Notify when exceeding 80% of budget
- **Autoscale policies** — Max replicas to prevent runaway costs
- **Reserved capacity** (future) — For dedicated/production clients

---

## Developer Experience

### Local Development

#### Docker Compose Setup
- **One command** — `docker compose up --build` brings entire stack
- **Hot reload** — Frontend and backend auto-reload on code changes
- **Volume mounts** — Code changes reflected immediately
- **Debugging** — Pdb breakpoints, logging, local testing

#### Development Tools
- **Python linter** — Ruff format, check, and fix
- **Type checker** — mypy strict mode for main services
- **Tests** — pytest with mocking for OpenAI and Graph API
- **Pre-commit hooks** — Auto-format before git commit

### API & SDK

#### REST API
- **OpenAPI/Swagger** — Full spec at `/openapi.json`
- **Interactive docs** — Swagger UI at `/docs`
- **Client libraries** — Python client stub available
- **Rate limiting** — Configurable per user/IP

#### MCP Specification
- **Model Context Protocol** — Standard tool definition format
- **Extensibility** — Add custom tools without modifying orchestrator
- **Type safety** — Zod schemas for tool parameters
- **Tool discovery** — Automatic tool schema loading on startup

### CI/CD Pipeline

#### Automated Testing
- **Unit tests** — Fast, mocked tests (< 5 seconds)
- **Integration tests** — Against live docker-compose services
- **Smoke tests** — Quick pre-deploy validation
- **Code quality** — Linting, type checking, test coverage

#### Image Building & Registry
- **ACR integration** — Automated Docker builds on push
- **Image tagging** — Semantic versioning (v1.2.3)
- **Digest pinning** — Container Apps pin specific image digests
- **Rollback** — Easy revert to previous version via Terraform

#### Deployment Automation
- **Azure DevOps Pipelines** — Trigger on main branch push
- **GitHub Actions** — Alternative CI provider (configuration included)
- **Manual approval** — Human sign-off before production deploy
- **Gradual rollout** — Canary deployments to validate changes

---

## Limitations & Known Issues

### Current Limitations
- Complex multi-tool prompts may timeout on first attempt (retry works)
- SQL Serverless cold start adds ~10s after auto-pause
- Admin consent for Graph API must be granted manually post-deploy (not automated)
- Teams SSO is feature-flagged (can be disabled per deployment)
- Chat history not encrypted at rest (logged plaintext for debugging)

### Future Enhancements
- Graceful shutdown before restart
- Vector search for knowledge base embeddings
- Multi-step approval workflows with escalation
- Custom MCP tool development kit
- Federated chat across multiple instances
- Prompt caching to reduce token usage
- Streaming partial results during synthesis

---

## Support & Documentation

For more information:
- **[docs/ARCHITECTURE.md](ARCHITECTURE.md)** — Technical design and data flows
- **[docs/DEPLOYMENT.md](DEPLOYMENT.md)** — Deployment guide
- **[docs/API_REFERENCE.md](API_REFERENCE.md)** — REST API endpoints
- **[docs/SUPPORT.md](SUPPORT.md)** — Operations runbook
- **[README.md](../README.md)** — Quick start
