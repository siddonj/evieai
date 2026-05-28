# EvieAI Support Runbook

## Start / stop

### Start full stack

```bash
docker compose up --build -d
```

### Stop

```bash
docker compose down
```

### Tail logs

```bash
docker compose logs -f orchestrator
# or all services
docker compose logs -f
```

---

## Health / readiness

```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/ready
curl -s http://localhost:8000/actions/reliability
curl -s http://localhost:8000/connectors/sync/reliability
```

If `ready` shows dependencies unreachable, inspect that service logs:

```bash
docker compose logs --tail=200 <service-name>
```

---

## Common issues

### 1) 401/403 from mail/onedrive MCP

Likely Graph credentials/admin consent issue.

Check env:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`
- `AZURE_USER_ID`

In Azure, verify admin consent was granted for Graph app registration.

### 2) Chat endpoint failing with OpenAI errors

Verify:

- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`

### 3) Write actions not executing

Check:

- `GET /actions/approvals` for pending approvals
- `GET /actions/circuit` to confirm circuit status
- `GET /actions/reliability` for failure-rate threshold trips

### 4) Connector sync backlog

Check:

- `GET /connectors/sync/runs/recent`
- `GET /connectors/sync/reliability`
- `GET /connectors/sync/runs?status=pending`

If dead letters accumulate, replay with `/connectors/sync/replay`.

---

## Smoke check after deploy

1. `GET /health` returns `status=healthy`
2. `GET /ready` reports all dependencies reachable
3. `POST /chat/batch` returns reply + tool call logs
4. `GET /actions/reliability` returns thresholds/current values
5. `GET /connectors/sync/reliability` returns thresholds/current values

---

## Data paths (local default)

Configured in `.env`:

- `BITEMPORAL_DB_PATH=./data/evieai_bitemporal.db`
- `CONNECTOR_SYNC_DB_PATH=./data/evieai_connector_sync.db`
- `EVENT_SIGNAL_DB_PATH=./data/evieai_event_signal.db`
- `ACTIONS_DB_PATH=./data/evieai_actions.db`

Back up `./data/` periodically in long-running environments.
