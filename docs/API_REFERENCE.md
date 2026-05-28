# API Reference

Base URL:

- Local: `http://localhost:8000`
- Production: your deployed orchestrator URL

All endpoints return JSON unless noted.

---

## Core

### `GET /`
Service info.

### `GET /health`
Liveness + connector runtime snapshot + reliability metrics.

### `GET /ready`
Readiness check across all MCP dependencies.

---

## Chat

### `POST /chat` (SSE streaming)
Primary chat endpoint used by the Web UI.

- Content-Type: `application/json`
- Response: `text/event-stream`
- SSE events include `token`, `tool`, `done`, `error`

Request body:

```json
{
  "message": "Show me portfolio risk by property",
  "user_id": "josh",
  "history": [{"role": "user", "content": "previous message"}],
  "teams_token": "optional"
}
```

### `POST /chat/batch`
Non-streaming wrapper that returns final JSON in one response.

Response shape:

```json
{
  "reply": "...",
  "tool_calls": [{"name": "query_sql", "args": {"query": "..."}}],
  "mcp_results": [{"service": "sql"}]
}
```

---

## Download & auth

### `GET /download/{service}/{file_name:path}`
Proxy-download files from MCP backends.

### `POST /auth/teams-token`
Teams SSO OBO exchange (enabled when `ENABLE_TEAMS_SSO=true`).

---

## Connectors / ingestion

### `GET /connectors`
List registered connectors.

### `POST /connectors/{source_id}/enable`
Enable/disable a connector.

### `POST /connectors/{source_id}/fetch`
Fetch records from a connector source.

### `POST /connectors/{source_id}/sync`
Run sync for a source/entity pair.

### `POST /webhooks/ingress`
Ingest inbound webhook event.

### `GET /signals`
List emitted signals.

### `GET /events`
List ingested events.

---

## Bitemporal tools

### `POST /tools/get_connector_freshness`
### `POST /tools/get_entity_lineage`
### `POST /tools/get_confidence_breakdown`
### `POST /tools/query_as_of`
### `POST /tools/diff_between`

---

## Write-back actions / approvals

### `POST /actions/write`
Queue a write action request.

### `POST /actions/approve`
Approve action (moves from pending approval).

### `POST /actions/reject`
Reject action.

### `POST /actions/execute`
Execute an approved action.

### `GET /actions`
List actions.

### `GET /actions/approvals`
List pending approvals.

### `POST /actions/circuit`
Open/close write circuit breaker.

### `GET /actions/circuit`
Get circuit breaker state.

### `GET /actions/audit`
Action audit log.

### `GET /actions/reliability`
Action reliability thresholds + current values.

---

## Connector sync scheduler / reliability

### `POST /connectors/sync/schedule`
Create/update connector sync schedule.

### `GET /connectors/sync/schedules`
List schedules.

### `POST /connectors/sync/stop`
Disable a schedule.

### `DELETE /connectors/sync/schedule`
Delete a schedule.

### `POST /connectors/sync/schedule/enable`
Enable a disabled schedule.

### `GET /connectors/sync/worker`
Get scheduler worker status.

### `GET /connectors/sync/runs`
List runs (with status filters).

### `GET /connectors/sync/runs/recent`
List recent runs.

### `GET /connectors/sync/reliability`
Connector sync reliability thresholds + current values.

### `POST /connectors/sync/replay`
Replay a dead-lettered sync item.

---

## Admin MCP controls

### `GET /admin/mcp-config`
List MCP runtime enablement.

### `POST /admin/mcp-config`
Enable/disable an MCP route at runtime.

### `GET /admin/mcp-data/{service}`
Read MCP sample/admin data.

### `POST /admin/mcp-data/{service}`
Write/update MCP sample/admin data.

---

## Rate limiting

- Sliding-window limiter per `user_id` (fallback IP)
- Limit violations return HTTP 429

## Common HTTP errors

- `400` invalid payload
- `401` invalid webhook signature (when enabled)
- `404` unknown route/service
- `429` rate limited
- `500` internal/runtime dependency error
