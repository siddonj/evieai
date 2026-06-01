# Terraform Rollback Runbook

This runbook covers safe rollback options for a deployment made from this repository.

## Scope

Use this guide when you need to:
- Roll back application image changes
- Revert recent infrastructure changes
- Fully destroy an environment
- Recover from a failed apply

This assumes:
- Terraform state is stored in Azure Storage backend
- You deploy from the `terraform/` folder
- You can authenticate with Azure CLI in the target subscription

## Before You Roll Back

1. Confirm the target environment (`dev`, `staging`, `prod`).
2. Confirm the subscription and resource group.
3. Pull latest code and ensure local branch is correct.
4. Create a backup of current Terraform state.

### State backup

From `terraform/`:

```powershell
terraform state pull > tfstate-backup-$(Get-Date -Format yyyyMMdd-HHmmss).json
```

## Option A: Roll Back App Image Only (Fastest, Lowest Risk)

Use when infrastructure is healthy and only app behavior regressed.

1. Identify the previous known-good image digest for orchestrator.
2. Update `orchestrator_image_digest` in `terraform.tfvars`.
3. Preview and apply only orchestrator change.

```powershell
terraform plan -target=azurerm_container_app.orchestrator
terraform apply -target=azurerm_container_app.orchestrator
```

4. Validate health endpoint and logs.

## Option B: Roll Back Recent Terraform Change by Git Commit

Use when a recent Terraform commit caused regressions.

1. Find a known-good commit.

```powershell
git log --oneline -- terraform/
```

2. Move working tree to that commit state (without rewriting remote history).

```powershell
git checkout <GOOD_COMMIT_SHA> -- terraform/
```

3. Run preview and apply.

```powershell
cd terraform
terraform plan
terraform apply
```

4. If successful, commit this rollback change so history is explicit.

## Option C: Targeted Infra Rollback

Use when one component should be recreated or removed.

### Example: recreate one container app

```powershell
terraform taint azurerm_container_app.sql_mcp
terraform plan
terraform apply
```

### Example: remove one resource from code and apply

1. Remove resource block from Terraform code.
2. Run:

```powershell
terraform plan
terraform apply
```

## Option D: Full Environment Destroy

Use for full teardown of a non-production environment.

1. Verify workspace and variables are for the correct environment.
2. Run destroy plan first.

```powershell
cd terraform
terraform plan -destroy
```

3. Execute destroy.

```powershell
terraform destroy
```

4. Keep backend state resources (`rg-terraform-state`, storage account, tfstate container) unless you intentionally want to remove Terraform backend.

## Option E: Failed Apply Recovery

If `terraform apply` fails mid-run:

1. Do not manually delete random resources.
2. Re-run:

```powershell
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

3. If drift persists, refresh and review:

```powershell
terraform plan -refresh-only
terraform apply -refresh-only
```

4. If a resource exists in Azure but not state, import it:

```powershell
terraform import <RESOURCE_ADDRESS> <AZURE_RESOURCE_ID>
```

Then run `terraform plan` and `terraform apply` again.

## Post-Rollback Validation Checklist

- Container Apps are healthy
- Orchestrator endpoint responds
- Static Web App is reachable
- Key Vault secrets resolve correctly
- SQL and PostgreSQL connectivity works
- Mail and OneDrive permissions still valid
- No unexpected Terraform drift

Run:

```powershell
terraform plan
```

Expected: `No changes. Your infrastructure matches the configuration.`

## Production Safety Rules

- Prefer Option A (image rollback) before infra rollback.
- Never run `terraform destroy` in production without explicit approval.
- Keep a state backup before any rollback.
- Use small, targeted applies when possible.
- Commit rollback changes to source control for auditability.
