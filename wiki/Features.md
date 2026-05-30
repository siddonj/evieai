# EvieAI Features Overview

> Complete list of EvieAI capabilities

## Chat & Conversation

- **Multi-turn conversations** — Full history context, cross-turn references understood
- **Natural language interface** — No special syntax, ask questions naturally
- **Streaming responses** — Real-time answer delivery as tools execute
- **Tool call visibility** — See which data sources were queried (badges like 📧 query_mail)
- **Multi-language support** — English, Spanish, French, Mandarin, and more

## Data Integration

### Email (Outlook)
- Full mailbox search across all folders
- Filter by sender, date range, subject, keywords, unread status
- Identify and extract attachments
- Multi-account support

**Example:** "Show me all unread emails from my manager"

### OneDrive & SharePoint
- File name and metadata search
- Document preview with content snippets
- Shared files access
- Folder structure awareness
- Version history tracking

**Example:** "Find the latest marketing deck"

### SQL Databases
- Parameterized query execution
- Multi-table joins and aggregations
- Schema flexibility (no code changes to add tables)
- Auto-scaling serverless databases

**Example:** "Show Q2 sales by region"

### File Shares
- Full-text search across files
- Support for PDF, Word, Excel, PowerPoint, text, JSON, CSV
- Metadata extraction (size, date, author)
- Directory structure navigation

**Example:** "Find all PDFs about compliance"

### Analytics & Dashboards
- KPI cards and trend analysis
- Week-over-week and month-over-month comparisons
- Predictive forecasts
- Benchmark comparisons

**Example:** "What's our Q2 revenue trend?"

### Knowledge Base (Internal)
- Semantic search over SOPs and policies
- FAQ indexing
- Best practices lookup
- Compliance guideline retrieval

**Example:** "What's the process for onboarding a vendor?"

## Agentic Reasoning

- **Automatic tool selection** — LLM decides which data sources to query
- **Parallel execution** — Multiple tools called simultaneously
- **Dependency awareness** — Understands tool call order
- **Error recovery** — Graceful fallbacks if tools fail
- **Multi-source synthesis** — Combines 5+ sources into one answer
- **Hallucination prevention** — All facts are source-attributed
- **Conversation management** — Clarifies ambiguous queries, suggests related questions

## Report Generation

- **Automated briefings** — Multi-section documents from Q&A results
- **HTML output** — Print-ready, email-friendly formatting
- **Custom templates** — Branded reports via Jinja2
- **Data visualization** — Tables, charts, highlighted metrics
- **Export options** — HTML, PDF (via print), email delivery

**Report types:**
- Board meeting prep
- Daily digests
- Compliance reports
- Customer briefings

## Administration & Operations

### Service Health Monitoring
- Real-time status dashboard for all services
- Response time metrics
- Error rate tracking
- Uptime percentages (7/30 days)
- Last restart timestamp

### Service Restart (NEW in v1.5)
- One-click restart from admin dashboard
- Restart via REST API
- Graceful shutdown with request completion
- Automatic reimage on restart
- Health validation before returning
- Multi-client isolation (each client manages own services)
- Audit trail of all restart events

### Approval Workflow
- List of pending approvals with details
- One-click approve/reject buttons
- Full audit trail (who approved, when, why)
- Execution logs showing results

### Reliability Metrics
- Action success rate tracking
- Tool timeout monitoring
- Connector sync backlog visibility
- Error threshold gates
- Circuit breaker status (open/closed)

## Security & Compliance

### Authentication
- Azure Entra ID single sign-on
- OAuth 2.0 token management
- Automatic token refresh
- Session isolation per user

### Data Protection
- HTTPS/TLS 1.2+ encryption in transit
- Azure Key Vault for secrets (encrypted at rest)
- Transparent Data Encryption for SQL databases
- Encrypted backup storage

### Multi-Tenant Isolation (NEW in v1.5)
- Separate resource groups per client
- Independent Container Apps per client
- Dedicated databases per client
- Service-level RBAC isolation
- No cross-tenant data access

### Compliance
- Comprehensive audit logging
- GDPR support (right to deletion, data export)
- Configurable log retention (90-day default)
- Regional data residency options
- Least-privilege Graph API scopes (Mail.Read, Files.Read.All)

## Deployment & Scalability

### Infrastructure
- Serverless Container Apps (auto-scaling 0–10 replicas)
- Serverless SQL database (auto-pause after 1 hour)
- Azure Blob Storage for files and reports
- Azure Key Vault for secret storage
- Log Analytics for centralized logging

### Multi-Client Deployment (NEW in v1.5)
- Deploy to unlimited client organizations
- Complete resource isolation per client
- Automatic resource naming per client
- Independent service restart per client
- Terraform automation for repeatable deployments

### Scaling Options
- Horizontal: Add replicas (0–10 per service)
- Vertical: Increase CPU/memory per pod
- Database: Scale compute tier up or down
- API: Automatic rate limiting and throttling

### Cost Optimization
- Consumption-based pricing (pay for what you use)
- Auto-pause SQL after 1 hour inactivity
- Optional reserved capacity for predictable workloads
- Per-client budget controls and alerts

## API & Integration

- **REST API** — OpenAPI specification available
- **Streaming chat** — SSE or WebSocket for real-time responses
- **Tool discovery** — Automatic schema loading
- **Webhook support** — Event-driven integrations
- **Rate limiting** — Configurable per user/IP
- **Error handling** — Standardized error codes and messages

## Limitations & Known Issues

**Current limitations:**
- Complex multi-tool prompts may timeout on first attempt (retry works)
- SQL Serverless cold start adds ~10 seconds after auto-pause
- Admin consent for Graph API must be manually granted post-deploy
- Teams SSO is feature-flagged (can be disabled)
- Chat history not encrypted at rest

**Coming soon:**
- Vector embeddings for semantic knowledge base search
- Multi-step approval workflows with escalation
- Custom MCP tool development kit
- Federated chat across multiple EvieAI instances
- Prompt caching to reduce token usage

---

## Feature Checklist

Use this to track which features are enabled in your deployment:

- [ ] Chat interface with streaming
- [ ] Email search (Graph API Mail.Read)
- [ ] OneDrive search (Graph API Files.Read.All)
- [ ] SQL database query
- [ ] File share search
- [ ] Analytics dashboard integration
- [ ] Knowledge base search
- [ ] Report generation
- [ ] Admin dashboard
- [ ] Service restart (UI)
- [ ] Service restart (API)
- [ ] Approval workflow
- [ ] Teams SSO (optional)
- [ ] Multi-client deployment
- [ ] Audit logging to Log Analytics

---

## Feature by Data Source Size

| Data Source | Supported Size | Latency |
|-------------|---|---|
| Email (mailbox) | Unlimited | <500ms |
| OneDrive | Unlimited | <1s |
| SQL database | 100M+ rows | <2s (indexed queries) |
| File share | 10K+ files | <3s |
| Knowledge base | 10K+ pages | <2s |
| Analytics cache | Real-time | <500ms |

---

## Next Steps

- **Deploy locally**: See [[Getting-Started]]
- **Deploy to Azure**: See [[Deployment-Checklist]]
- **Integrate via API**: See [[API-Reference]]
- **Run in production**: See [[Operations]]
