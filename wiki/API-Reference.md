# API Reference

> EvieAI REST API endpoints and WebSocket documentation

## Base URL

```
https://{your-orchestrator-url}
```

Example: `https://acme-corp-orchestrator-prod.yellowpond-123.eastus.azurecontainerapps.io`

---

## Authentication

### Bearer Token (Optional)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  https://your-orchestrator/chat
```

### No Authentication (Default)

If Teams SSO is disabled, no auth required. If enabled, provide valid Azure AD token.

---

## Chat Endpoints

### POST /api/chat

Send a chat message and get streaming response.

**Request:**
```json
{
  "message": "What's in my inbox?",
  "user_id": "user@example.com",
  "session_id": "session-123",
  "conversation_history": [
    {
      "role": "user",
      "content": "Hello"
    },
    {
      "role": "assistant",
      "content": "Hi there!"
    }
  ]
}
```

**Response (Streaming):**
```
data: {"type": "start", "timestamp": "2026-05-29T14:30:00Z"}
data: {"type": "tool_call", "tool": "query_mail", "status": "calling"}
data: {"type": "text", "content": "Checking your "}
data: {"type": "text", "content": "inbox..."}
data: {"type": "tool_result", "tool": "query_mail", "result_count": 12}
data: {"type": "text", "content": "\n\nYou have 12 unread emails"}
data: {"type": "complete", "total_tokens": 142}
```

**Status Codes:**
- `200` — Streaming started
- `400` — Missing required fields
- `401` — Unauthorized (if auth enabled)
- `500` — Server error

**Example (curl with streaming):**
```bash
curl -X POST "https://your-orchestrator/api/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show recent emails",
    "user_id": "user@example.com"
  }' \
  --stream
```

**Example (Python):**
```python
import httpx
import json

async with httpx.AsyncClient() as client:
    async with client.stream(
        "POST",
        "https://your-orchestrator/api/chat",
        json={
            "message": "What emails do I have?",
            "user_id": "user@example.com"
        }
    ) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                event = json.loads(line[6:])
                print(event)
```

**Stream Event Types:**

| Type | Fields | Meaning |
|------|--------|---------|
| `start` | timestamp | Chat started |
| `tool_call` | tool, status | Calling data source |
| `text` | content | Streaming text response |
| `tool_result` | tool, result_count | Data source returned results |
| `complete` | total_tokens | Chat finished |
| `error` | message, details | Error occurred |

---

### GET /api/chat/{session_id}

Retrieve conversation history.

**Response:**
```json
{
  "session_id": "session-123",
  "user_id": "user@example.com",
  "created_at": "2026-05-29T14:00:00Z",
  "messages": [
    {
      "role": "user",
      "content": "What's in my inbox?",
      "timestamp": "2026-05-29T14:00:00Z"
    },
    {
      "role": "assistant",
      "content": "You have 12 unread emails...",
      "timestamp": "2026-05-29T14:00:05Z",
      "tool_calls": [
        {
          "tool": "query_mail",
          "status": "success",
          "result_count": 12
        }
      ]
    }
  ]
}
```

---

## Admin & Operations Endpoints

### POST /restart

Restart a service (for admin dashboard and programmatic use).

**Request:**
```json
{
  "service": "sql"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "service": "sql",
  "timestamp": "2026-05-29T14:32:45.123456Z",
  "message": "Service restarted successfully"
}
```

**Response (Error):**
```json
{
  "status": "error",
  "service": "sql",
  "message": "Insufficient permissions",
  "details": "Managed identity requires Container App Contributor role"
}
```

**Status Codes:**
- `200` — Restart initiated
- `400` — Invalid service name
- `401` — Unauthorized
- `403` — Insufficient permissions
- `404` — Service not found
- `500` — Azure API error

**Valid Service Names:**
```
sql, file_share, o365_mail, onedrive, memory, knowledge_base,
document_generation, analytics, dashboard, orchestrator
```

**Example:**
```bash
curl -X POST "https://your-orchestrator/restart" \
  -H "Content-Type: application/json" \
  -d '{"service": "sql"}'
```

---

### GET /health

Check if orchestrator is healthy.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-05-29T14:32:45Z",
  "version": "1.5.0"
}
```

---

### GET /ready

Check if all dependencies are reachable.

**Response:**
```json
{
  "status": "ready",
  "dependencies": {
    "openai": true,
    "database": true,
    "storage": true,
    "vault": true,
    "sql_mcp": true,
    "mail_mcp": true,
    "onedrive_mcp": true,
    "file_share_mcp": true,
    "memory_mcp": true,
    "knowledge_base_mcp": true,
    "document_generation_mcp": true,
    "analytics_mcp": true,
    "dashboard_mcp": true
  }
}
```

**Status Codes:**
- `200` — All dependencies ready
- `503` — One or more dependencies unavailable

---

### GET /metrics

Prometheus format metrics.

**Response:**
```
# HELP chat_requests_total Total chat requests
# TYPE chat_requests_total counter
chat_requests_total{status="success"} 1234
chat_requests_total{status="error"} 12

# HELP chat_response_duration_seconds Response time
# TYPE chat_response_duration_seconds histogram
chat_response_duration_seconds_bucket{le="1"} 456
chat_response_duration_seconds_bucket{le="5"} 1200
chat_response_duration_seconds_bucket{le="10"} 1246

# HELP tool_calls_total Total tool calls by service
# TYPE tool_calls_total counter
tool_calls_total{tool="query_mail",status="success"} 890
tool_calls_total{tool="query_mail",status="timeout"} 5
tool_calls_total{tool="query_sql",status="success"} 234
```

---

## Report Generation Endpoints

### POST /api/generate-report

Generate a report from chat context.

**Request:**
```json
{
  "title": "Q2 Revenue Analysis",
  "session_id": "session-123",
  "template": "executive_briefing",
  "format": "html"
}
```

**Response:**
```json
{
  "status": "success",
  "report_id": "report-456",
  "download_url": "https://storage.blob.core.windows.net/reports/report-456.html",
  "created_at": "2026-05-29T14:35:00Z"
}
```

**Template Options:**
- `executive_briefing` — Multi-section professional report
- `daily_digest` — Morning news/updates style
- `compliance_report` — Policy-focused with signatures
- `customer_brief` — Client-facing summary

**Format Options:**
- `html` — Web browser (default)
- `pdf` — Print-ready (requires print-to-PDF capability)
- `markdown` — Raw markdown

---

## Tool Discovery Endpoints

### GET /tools

List all available tools (data sources).

**Response:**
```json
{
  "tools": [
    {
      "name": "query_mail",
      "display_name": "Email Search",
      "description": "Search Outlook email",
      "parameters": {
        "query": {"type": "string", "required": true},
        "mailbox": {"type": "string", "required": false},
        "limit": {"type": "integer", "default": 10}
      }
    },
    {
      "name": "query_sql",
      "display_name": "Database Query",
      "description": "Execute SQL queries",
      "parameters": {
        "query": {"type": "string", "required": true},
        "database": {"type": "string", "required": false}
      }
    },
    ...
  ]
}
```

---

## Error Handling

All error responses follow this format:

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: message",
    "details": {
      "field": "message",
      "expected": "string"
    },
    "timestamp": "2026-05-29T14:32:45Z"
  }
}
```

### Common Error Codes

| Code | Meaning | Fix |
|------|---------|-----|
| `INVALID_REQUEST` | Missing/bad request body | Check JSON format |
| `INVALID_SERVICE` | Unknown service name | See valid service list |
| `AUTHENTICATION_FAILED` | Invalid/missing token | Provide valid bearer token |
| `PERMISSION_DENIED` | Insufficient role/permissions | Check RBAC roles |
| `SERVICE_UNAVAILABLE` | MCP server unreachable | Check /ready endpoint |
| `TIMEOUT` | Request took >30s | Retry or increase timeout |
| `INTERNAL_ERROR` | Server error | Check logs, retry |

---

## Rate Limiting

Default limits (per user, per minute):
- Chat API: 10 requests/minute
- Restart API: 5 requests/minute
- Report generation: 2 requests/minute

**If rate limited:**
- Status code: `429 Too Many Requests`
- Response includes: `Retry-After` header (seconds to wait)

```bash
# Retry after waiting
curl -H "Authorization: Bearer $TOKEN" \
  https://your-orchestrator/api/chat

# Returns: 429
# Retry-After: 60 (wait 60 seconds, then retry)
```

---

## OpenAPI Specification

Download the full OpenAPI schema:

```bash
curl https://your-orchestrator/openapi.json
```

Use in tools like Postman, Swagger UI, or code generators:

```bash
# Generate Python client
openapi-generator-cli generate \
  -i https://your-orchestrator/openapi.json \
  -g python
```

---

## Webhooks (Optional)

If enabled, EvieAI sends webhooks for events:

```json
{
  "event": "chat.completed",
  "timestamp": "2026-05-29T14:32:45Z",
  "data": {
    "session_id": "session-123",
    "user_id": "user@example.com",
    "message_count": 5,
    "tools_used": ["query_mail", "query_sql"],
    "duration_seconds": 15
  }
}
```

**Event Types:**
- `chat.started` — User initiated chat
- `chat.completed` — Chat finished
- `chat.failed` — Chat errored
- `report.generated` — Report created
- `service.restarted` — Service was restarted

---

## Examples

### Python Chat Client

```python
import httpx
import json

class EvieAIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def chat(self, message: str, user_id: str):
        response_text = ""
        
        async with self.client.stream(
            "POST",
            f"{self.base_url}/api/chat",
            json={"message": message, "user_id": user_id}
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if event["type"] == "text":
                        response_text += event["content"]
                        print(event["content"], end="", flush=True)
        
        return response_text
    
    async def restart_service(self, service: str):
        resp = await self.client.post(
            f"{self.base_url}/restart",
            json={"service": service}
        )
        return resp.json()

# Usage
client = EvieAIClient("https://your-orchestrator")
response = await client.chat("What emails do I have?", "user@example.com")
status = await client.restart_service("sql")
```

### JavaScript Chat Client

```javascript
class EvieAIClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
  }

  async chat(message, userId) {
    const response = await fetch(`${this.baseUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, user_id: userId })
    });

    let fullResponse = "";
    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const text = decoder.decode(value);
      for (const line of text.split("\n")) {
        if (line.startsWith("data: ")) {
          const event = JSON.parse(line.slice(6));
          if (event.type === "text") {
            fullResponse += event.content;
            process.stdout.write(event.content);
          }
        }
      }
    }

    return fullResponse;
  }

  async restartService(service) {
    const response = await fetch(`${this.baseUrl}/restart`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service })
    });
    return response.json();
  }
}

// Usage
const client = new EvieAIClient("https://your-orchestrator");
const response = await client.chat("What emails do I have?", "user@example.com");
```

---

## Next Steps

- **Deploy EvieAI:** [[Deployment-Checklist]]
- **Understand architecture:** [[Architecture]]
- **Troubleshoot API issues:** [[Troubleshooting]]
