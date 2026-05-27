# Disaster Recovery Runbook

This runbook describes the manual steps to recover the `aiagent2` application
after a region-wide Azure outage in `westus3`. Recovery target: **RTO < 2 hours**.

---

## Pre-requisites

- Azure CLI authenticated with Owner/Contributor on the subscription
- Terraform state accessible (stored in `aiagent2tfstate` / `rg-terraform-state` in `eastus2`)
- Admin access to the custom domain DNS (`resiq.co`)

---

## Step 1: Assess the Outage

```bash
# Check if resources are reachable
az containerapp show --name aiagent2-orchestrator-dev -g rg-aiagent2-dev --query "properties.runningStatus"
az staticwebapp show --name aiagent2-ui-dev -g rg-aiagent2-dev --query "defaultHostname"
```

If both return healthy responses, the issue is not regional. Check OpenAI, SQL, or individual MCP servers.

---

## Step 2: Deploy to Secondary Region

Create a secondary variables file (`terraform/secondary.tfvars`):

```hcl
project_name           = "aiagent2"
environment            = "dr"
location               = "eastus2"
sql_admin_password     = "<same as primary - retrieve from Key Vault>"
target_user_upn        = "<same as primary>"
container_app_min_replicas = 0
container_app_max_replicas = 3
openai_tpm_capacity    = 10
```

Deploy:

```bash
cd terraform
terraform init
terraform apply -var-file=secondary.tfvars -auto-approve
```

Expected time: **15-20 minutes**.

---

## Step 3: Restore SQL Database

The primary database (`aiagent2-sqlsrv-dev`) has geo-redundant backups. Restore to the
DR server:

```bash
az sql db restore \
  --dest-name aiagent2-db-dr \
  --dest-resource-group rg-aiagent2-dr \
  --dest-server aiagent2-sqlsrv-dr \
  --name aiagent2-db-dev \
  --resource-group rg-aiagent2-dev \
  --server aiagent2-sqlsrv-dev \
  --time "<UTC timestamp just before the outage>"
```

If geo-restore is unavailable (paired region not enabled), restore from the latest
point-in-time backup within the same region.

After restore, update the connection string in Key Vault:

```bash
# Get the new connection string
DR_CONN=$(az sql db show-connection-string \
  --server aiagent2-sqlsrv-dr \
  --name aiagent2-db-dr \
  --client ado.net)

# Store in Key Vault (DR environment)
az keyvault secret set \
  --vault-name aiagent2-kv2-dr \
  --name sql-connection-string \
  --value "$DR_CONN"
```

Run migrations and seed data:

```bash
export DATABASE_CONNECTION_STRING="$DR_CONN"
python mcp_servers/sql/migrate.py
```

---

## Step 4: DNS Cutover

Update the custom domain CNAME records to point to the DR environment:

| Domain | Current (Primary) | New (DR) |
|--------|-------------------|----------|
| `demo.resiq.co` | `orange-bush-054b9530f.7.azurestaticapps.net` | DR SWA hostname (from `terraform output ui_cname_target`) |
| `api.resiq.co` | Orchestrator FQDN in westus3 | DR orchestrator FQDN (from `terraform output orchestrator_url`) |

DNS changes take **5-60 minutes** to propagate globally. Monitor with:

```bash
nslookup demo.resiq.co
nslookup api.resiq.co
```

---

## Step 5: Validate

```bash
# Health checks
curl -s https://api.resiq.co/health | jq
curl -s https://api.resiq.co/ready | jq

# Smoke test a chat request
curl -s -X POST https://api.resiq.co/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me the sales pipeline", "user_id": "smoke-test"}' | jq

# Verify SWA is serving the UI
curl -s -o /dev/null -w "%{http_code}" https://demo.resiq.co
```

Open `https://demo.resiq.co` in a browser and confirm the chat interface loads and responds.

---

## Step 6: Fail Back (when primary is restored)

1. Reverse the DNS CNAME records back to primary endpoints
2. Export any data created during DR (if needed) and restore to primary SQL
3. Optionally `terraform destroy` the DR environment to avoid costs

---

## Critical Contacts & Resources

| Resource | Location |
|----------|----------|
| Terraform state | `rg-terraform-state` / `aiagent2tfstate` / `tfstate` container |
| Key Vault (primary) | `aiagent2-kv2-dev` in `rg-aiagent2-dev` |
| DNS provider | Wherever `resiq.co` is managed |
| App registration | Entra ID → `aiagent2-graph-app-dev` |
| Azure Support | Microsoft Q&A / `az support ticket create` |
