# API Reference

Base URL: `https://api.resiq.co` (prod) or `http://localhost:8000` (local)

All endpoints return JSON. Streaming endpoints return SSE (Server-Sent Events).

---

## Orchestrator Endpoints

### `GET /`
Service info. Returns: `{"service": "orchestrator", "status": "ok", "mode": "openai-tool-calling"}`

### `GET /health`
Liveness probe. Returns: `{"status": "healthy"}`

### `GET /ready`
Readiness probe. Checks all 8 MCP servers. Returns dependency reachability map.

### `POST /chat`
Standard (batch) chat. Returns full response after LLM completes.

**Request:**
```json
{
  "message": "Show me the sales pipeline",
  "user_id": "alice.chen",
  "history": [
    {"role": "user", "content": "What data do you have?"},
    {"role": "assistant", "content": "I have access to..."}
  ],
  "teams_token": "(optional SSO token)"
}
```

**Response:**
```json
{
  "reply": "### Sales Pipeline Overview\n...",
  "tool_calls": [{"name": "query_sql", "args": {"query": "..."}}],
  "mcp_results": [
    {
      "service": "sql",
      "contacts": [...],
      "companies": [...],
      "metrics": {...}
    }
  ]
}
```

### `POST /chat/stream`
Streaming variant. Returns SSE events.

**Request:** Same as `/chat`.

**SSE Events:**

| Event | Description | Example |
|-------|-------------|---------|
| `token` | Word-by-word text | `{"type":"token","content":"### Sales"}` |
| `tool_start` | Tool call initiated | `{"type":"tool_start","name":"query_sql","args":"..."}` |
| `tool_result` | Tool completed | `{"type":"tool_result","name":"query_sql","summary":"Found 12 contacts"}` |
| `done` | Response complete | `{"type":"done","reply":"...","tool_calls":[...],"mcp_results":[...]}` |

### `GET /download/{service}/{file_name}`
Proxy file download from an MCP server.

**Parameters:**
- `service`: `files`, `mail`, `onedrive`, `sql`, `knowledge_base`, `memory`, `document_generation`, `analytics`
- `file_name`: URL-encoded filename

Returns file content with `Content-Disposition: attachment` header.

### `POST /auth/teams-token`
Exchange a Teams SSO token for a Graph API token (OBO flow).

**Request:** `{"token": "eyJ..."}`  
**Response:** `{"exchanged": true, "token_type": "Bearer", "scope": "..."}`  

Requires: `ENABLE_TEAMS_SSO=true` env var. Uses `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`.

---

## Admin Endpoints

### `GET /admin/mcp-config`
List all MCP servers and their enabled/disabled status.

### `POST /admin/mcp-config`
Enable or disable an MCP server at runtime.

**Request:** `{"key": "sql", "enabled": false}`

### `GET /admin/mcp-data/{service}`
Fetch sample data from an MCP server's `/admin/data` endpoint.

### `POST /admin/mcp-data/{service}`
Add data to an MCP server.

---

## MCP Endpoint Contract

Every MCP server implements:

### `GET /health` → `{"status": "healthy"}`
### `GET /mcp` → `{"transport": "streamable-http", "service": "service_name"}`
### `POST /mcp/query` → `{"service": "...", "query": "...", ...}`

**MCP-specific response fields:**

| MCP Server | Response Fields |
|------------|----------------|
| `sql` | `contacts`, `companies`, `metrics`, `contacts_summary`, `companies_summary`, `metrics_summary` |
| `files` | `items` (list of files/dicts) |
| `mail` | `messages` (list of emails) |
| `onedrive` | `files` (list of OneDrive files) |
| `knowledge_base` | `documents` (SOPs, policies) |
| `memory` | `profile`, `preferences`, `recent_topics`, `bookmarks`, `relevant_snippets` |
| `document_generation` | `documents` (templates with sections, metrics, action items) |
| `analytics` | `kpi_cards`, `trends`, `insights` |

### `GET /mcp/files/{file_name}/download` — File download (files, onedrive)

Returns file content with appropriate `Content-Type` and `Content-Disposition: attachment`.

---

## Rate Limiting

- **20 requests/minute per user** (keyed by `user_id` or IP)
- Returns HTTP 429 with `{"detail": "Rate limit reached. X requests remaining."}`
- In-memory sliding window — resets on container restart

## Error Responses

| Status | Meaning |
|--------|---------|
| 400 | Invalid input (empty message, >4000 chars) |
| 429 | Rate limit exceeded |
| 404 | Unknown service (download proxy) or endpoint not found |
| 500 | Internal error (check application logs) |
