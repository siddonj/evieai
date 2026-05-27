# Data Retention & Privacy Policy

Last updated: May 2026

---

## What Data We Store

| Data | Location | Purpose | Retention |
|------|----------|---------|-----------|
| Chat messages | Not persisted | Messages are processed in-memory for the current session only | Ephemeral — deleted on container restart |
| User profile | Memory MCP (in-memory only) | Personalization (name, role, preferences, bookmarks) | Ephemeral — reset on container restart |
| Contacts & Companies | SQL Database (`aiagent2-db-dev`) | CRM demo data (sample sales pipeline) | Indefinite (demo data — no real PII) |
| Generated reports | Azure Blob Storage (`reports` container) | User-requested document generation (HTML) | 30 days (auto-deleted via lifecycle policy) |
| OpenAI prompts | OpenAI API logs | Azure OpenAI may log prompts for abuse monitoring (Microsoft-managed) | Per Microsoft's data handling policy — typically 30 days |
| Logs | Log Analytics (`law-aiagent2-dev`) | Application diagnostics | 30 days (configured at workspace creation) |

---

## What We Do NOT Store

- No chat history is persisted (stateless `/chat` endpoint)
- No user authentication tokens (Teams SSO tokens are exchanged in-memory, never stored)
- No email content (O365 Mail MCP accesses Graph API on-the-fly)
- No OneDrive file content (streamed on-the-fly via Graph API or demo data)
- No browser cookies or analytics tracking

---

## Data Encryption

| Layer | Encryption |
|-------|-----------|
| **In transit** | All services use HTTPS (TLS 1.2+). Container Apps ingress enforces HTTPS. |
| **At rest — SQL** | Azure SQL Database encrypts data at rest via TDE (Transparent Data Encryption). |
| **At rest — Blob** | Storage account uses Microsoft-managed keys for encryption at rest. |
| **At rest — Key Vault** | All secrets (API keys, connection strings) encrypted at rest. |
| **At rest — Redis** | Basic tier — data-in-memory only (not persisted). Encryption in transit via TLS 1.2. |

---

## Data Deletion

- **Generated reports:** Automatically deleted after 30 days via Azure Blob lifecycle policy
- **Logs:** Automatically purged after 30 days per Log Analytics retention
- **Demo data:** Can be cleared by re-running the seed container or dropping tables
- **Full reset:** `terraform destroy` removes all resources and data (requires state unlock for Key Vault soft-delete)

---

## Compliance Notes

- **GDPR:** No persistent storage of personal user data. Memory MCP data is ephemeral. Use the Memory MCP's `/admin/data` endpoints to inspect or clear profile data.
- **CCPA:** No user data sold or shared with third parties. All processing happens within the Azure tenant.
- **Organizational data policies:** The SQL database contains synthetic/demo data only. If real CRM data is loaded, ensure the storage account and database comply with organizational retention schedules.

---

## Access Control

| Resource | Access via |
|----------|-----------|
| Key Vault secrets | RBAC — only Container App managed identities with `Key Vault Secrets User` role |
| SQL Database | SQL authentication (password in Key Vault). No public endpoint — Azure services only. |
| Blob Storage | Access key (in Key Vault). Container access type: private. |
| Container Apps | Azure RBAC for deployment. App-level auth via Teams SSO (optional, feature-flagged). |

---

## Questions or Data Requests

For data access, correction, or deletion requests related to this application, contact the application administrator through your organization's IT support channel.
