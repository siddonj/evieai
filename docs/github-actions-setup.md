# GitHub Actions Setup for EvieAI

This replaces the Azure DevOps pipeline with GitHub Actions.

## What the workflow does

On every push to `main` that changes `orchestrator/`, `mcp_servers/`, or `web_ui/`:

1. **Lint** — runs `ruff check` and `mypy`
2. **Build** — builds Docker images for orchestrator + all MCP servers, pushes to ACR, builds web UI
3. **Deploy** — updates Azure Container Apps with new images, sets auth env vars, deploys Static Web App

## Required GitHub Secrets

Add these at **Settings → Secrets and variables → Actions → New repository secret**.

---

### 1. `AZURE_CREDENTIALS` — Service Principal JSON

This lets GitHub Actions log into Azure and update Container Apps.

**Create the service principal:**

```bash
az ad sp create-for-rbac \
  --name "github-actions-evieai" \
  --role contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID \
  --sdk-auth
```

Replace `YOUR_SUBSCRIPTION_ID` with your Azure subscription ID.

**Copy the entire JSON output** and paste it into the `AZURE_CREDENTIALS` secret.

Example output:
```json
{
  "clientId": "xxx",
  "clientSecret": "xxx",
  "subscriptionId": "xxx",
  "tenantId": "xxx"
}
```

**Give it ACR pull + push access:**

```bash
az acr show --name aiagent2acrdev --query id -o tsv
# Copy the ACR resource ID

az role assignment create \
  --assignee <clientId from JSON> \
  --role "AcrPush" \
  --scope <acr_resource_id>
```

---

### 2. `SWA_TOKEN` — Static Web App deployment token

```bash
az staticwebapp secrets list \
  --name aiagent2-ui-dev \
  --resource-group rg-aiagent2-dev \
  --query "properties.apiKey" \
  -o tsv
```

Paste the value into the `SWA_TOKEN` secret.

---

### 3. Optional: GitHub token for GitHub Container Registry

If you want to switch from ACR to GitHub Container Registry (ghcr.io), you don't need `AZURE_CREDENTIALS` for push — the built-in `GITHUB_TOKEN` handles auth. You'd still need it for `az containerapp update`.

---

## Verify setup

1. Push a small change to `main` (or go to **Actions → Deploy EvieAI → Run workflow**)
2. Check that the lint, build, and deploy stages all pass green
3. Visit `https://demo.resiq.co` and log in with `admin@evieai.local` / `admin`

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `az containerapp update` fails with permission denied | Check that the service principal has `Contributor` on the subscription and `AcrPush` on the ACR |
| `az acr login` fails | The service principal needs `AcrPush` role on the registry |
| Static Web App deploy fails | Regenerate the SWA token with the command above |
| JWT_SECRET changes on every deploy | This is expected on first run. After that, the pipeline preserves the existing secret from the Container App |
