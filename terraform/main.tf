# ─── Resource Group ─────────────────────────────────────────────────
resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location
  tags     = var.tags
}

# ─── Monitoring ───────────────────────────────────────────────────────
resource "azurerm_log_analytics_workspace" "main" {
  name                = "law-${var.project_name}-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

# ─── Container Registry ───────────────────────────────────────────────
resource "azurerm_container_registry" "main" {
  name                = "${var.project_name}acr${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = var.environment == "prod" ? "Standard" : "Basic"
  admin_enabled       = false
  tags                = var.tags
}

# ─── Key Vault ────────────────────────────────────────────────────────
resource "azurerm_key_vault" "main" {
  name                       = "${var.project_name}-kv2-${var.environment}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  soft_delete_retention_days = 7
  purge_protection_enabled   = true
  tags                       = var.tags
}

resource "azurerm_role_assignment" "kv_admin" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ─── Azure OpenAI ─────────────────────────────────────────────────────
resource "azurerm_cognitive_account" "openai" {
  name                = "${var.project_name}-openai-${var.environment}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  kind                = "OpenAI"
  sku_name            = "S0"
  tags                = var.tags
}

resource "azurerm_cognitive_deployment" "gpt4o" {
  name                 = "gpt-4o"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "gpt-4o"
    version = "2024-11-20"
  }
  scale {
    type     = "Standard"
    capacity = var.openai_tpm_capacity
  }
}

# ─── Azure SQL ────────────────────────────────────────────────────────
resource "azurerm_mssql_server" "main" {
  name                         = "${var.project_name}-sqlsrv-${var.environment}"
  resource_group_name          = azurerm_resource_group.main.name
  location                     = var.sql_location
  version                      = "12.0"
  administrator_login          = "sqladmin"
  administrator_login_password = var.sql_admin_password
  minimum_tls_version          = "1.2"
  tags                         = var.tags
}

resource "azurerm_mssql_database" "main" {
  name                        = "${var.project_name}-db-${var.environment}"
  server_id                   = azurerm_mssql_server.main.id
  sku_name                    = "GP_S_Gen5_2"
  max_size_gb                 = 32
  min_capacity                = 0.5
  auto_pause_delay_in_minutes = 60
  tags                        = var.tags
}

resource "azurerm_mssql_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_mssql_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ─── Azure PostgreSQL Flexible Server ───────────────────────────────
resource "azurerm_postgresql_flexible_server" "main" {
  name                          = "${var.project_name}-pg-${var.environment}"
  resource_group_name           = azurerm_resource_group.main.name
  location                      = azurerm_resource_group.main.location
  version                       = "16"
  administrator_login           = "pgadmin"
  administrator_password        = var.postgres_admin_password
  zone                          = "1"
  sku_name                      = var.environment == "prod" ? "GP_Standard_D2ds_v4" : "B_Standard_B1ms"
  storage_mb                    = 32768
  backup_retention_days         = 7
  public_network_access_enabled = true

  tags = var.tags
}

resource "azurerm_postgresql_flexible_server_database" "main" {
  name      = "${var.project_name}_db_${var.environment}"
  server_id = azurerm_postgresql_flexible_server.main.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.main.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# ─── Storage Account + File Share ───────────────────────────────────
resource "azurerm_storage_account" "main" {
  name                     = "${var.project_name}st${var.environment}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  account_kind             = "StorageV2"
  tags                     = var.tags
}

resource "azurerm_storage_share" "main" {
  name                 = "fileshare"
  storage_account_name = azurerm_storage_account.main.name
  quota                = 100
}

# ─── Entra ID App Registration ────────────────────────────────────────
resource "azuread_application" "graph" {
  display_name = "${var.project_name}-graph-app-${var.environment}"
  owners       = [data.azurerm_client_config.current.object_id]

  required_resource_access {
    resource_app_id = data.azuread_application_published_app_ids.well_known.result["MicrosoftGraph"]

    resource_access {
      id   = data.azuread_service_principal.msgraph.oauth2_permission_scope_ids["User.Read"]
      type = "Scope"
    }
    resource_access {
      id   = data.azuread_service_principal.msgraph.app_role_ids["Mail.Read"]
      type = "Role"
    }
    resource_access {
      id   = data.azuread_service_principal.msgraph.app_role_ids["Files.Read.All"]
      type = "Role"
    }
    resource_access {
      id   = data.azuread_service_principal.msgraph.app_role_ids["User.Read.All"]
      type = "Role"
    }
  }
}

resource "azuread_application_password" "graph" {
  application_id = azuread_application.graph.id
  display_name   = "terraform-generated"
  end_date       = "2099-01-01T00:00:00Z"
}

resource "azuread_service_principal" "graph" {
  client_id = azuread_application.graph.client_id
  owners    = [data.azurerm_client_config.current.object_id]
}

# ─── Data Sources ─────────────────────────────────────────────────────
data "azurerm_client_config" "current" {}

data "azuread_application_published_app_ids" "well_known" {}

data "azuread_service_principal" "msgraph" {
  client_id = data.azuread_application_published_app_ids.well_known.result["MicrosoftGraph"]
}

# ─── Secrets in Key Vault ─────────────────────────────────────────────
resource "azurerm_key_vault_secret" "openai_endpoint" {
  name         = "openai-endpoint"
  value        = azurerm_cognitive_account.openai.endpoint
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "openai_key" {
  name         = "openai-api-key"
  value        = azurerm_cognitive_account.openai.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "sql_conn" {
  name         = "sql-connection-string"
  value        = "Server=tcp:${azurerm_mssql_server.main.fully_qualified_domain_name},1433;Initial Catalog=${azurerm_mssql_database.main.name};Persist Security Info=False;User ID=${azurerm_mssql_server.main.administrator_login};Password=${var.sql_admin_password};MultipleActiveResultSets=False;Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;"
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "postgres_dsn" {
  name         = "postgres-dsn"
  value        = "postgresql://${azurerm_postgresql_flexible_server.main.administrator_login}:${var.postgres_admin_password}@${azurerm_postgresql_flexible_server.main.fqdn}:5432/${azurerm_postgresql_flexible_server_database.main.name}?sslmode=require"
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "storage_key" {
  name         = "storage-key"
  value        = azurerm_storage_account.main.primary_access_key
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "tenant_id" {
  name         = "azure-tenant-id"
  value        = data.azurerm_client_config.current.tenant_id
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "client_id" {
  name         = "azure-client-id"
  value        = azuread_application.graph.client_id
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "client_secret" {
  name         = "azure-client-secret"
  value        = azuread_application_password.graph.value
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "user_id" {
  name         = "azure-user-id"
  value        = var.target_user_upn
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

resource "azurerm_key_vault_secret" "redis_conn" {
  name         = "redis-connection-string"
  value        = var.redis_connection_string
  key_vault_id = azurerm_key_vault.main.id
  depends_on   = [azurerm_role_assignment.kv_admin]
}

# ─── Blob Storage for Reports ────────────────────────────────────────

resource "azurerm_storage_container" "reports" {
  name                  = "reports"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

resource "azurerm_storage_management_policy" "reports" {
  storage_account_id = azurerm_storage_account.main.id

  rule {
    name    = "delete-old-reports"
    enabled = true
    filters {
      blob_types   = ["blockBlob"]
      prefix_match = ["reports/"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }
    }
  }
}

# ─── Container Apps Environment ───────────────────────────────────────
resource "azurerm_container_app_environment" "main" {
  name                       = "${var.project_name}-env-${var.environment}"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.main.id
  tags                       = var.tags
}

# ─── SQL MCP Server ───────────────────────────────────────────────────
resource "azurerm_container_app" "sql_mcp" {
  name                         = "${var.project_name}-mcp-sql-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = all
  }

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8004
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  secret {
    name  = "sql-connection-string"
    value = azurerm_key_vault_secret.sql_conn.value
  }

  template {
    container {
      name   = "sql-mcp"
      image  = "${azurerm_container_registry.main.login_server}/mcp-sql:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name  = "DAB_BASE_URL"
        value = "http://localhost:5000"
      }
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }
}

# ─── File Share MCP Server ────────────────────────────────────────────
resource "azurerm_container_app" "files_mcp" {
  name                         = "${var.project_name}-mcp-files-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = all
  }

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8001
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  secret {
    name  = "storage-key"
    value = azurerm_key_vault_secret.storage_key.value
  }

  template {
    container {
      name   = "files"
      image  = "${azurerm_container_registry.main.login_server}/mcp-files:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name  = "STORAGE_ACCOUNT_NAME"
        value = azurerm_storage_account.main.name
      }
      env {
        name        = "STORAGE_ACCOUNT_KEY"
        secret_name = "storage-key"
      }
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }
}

# ─── O365 Mail MCP Server ─────────────────────────────────────────────
resource "azurerm_container_app" "mail_mcp" {
  name                         = "${var.project_name}-mcp-mail-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = all
  }

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8002
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  secret {
    name  = "azure-tenant-id"
    value = azurerm_key_vault_secret.tenant_id.value
  }
  secret {
    name  = "azure-client-id"
    value = azurerm_key_vault_secret.client_id.value
  }
  secret {
    name  = "azure-client-secret"
    value = azurerm_key_vault_secret.client_secret.value
  }
  secret {
    name  = "azure-user-id"
    value = azurerm_key_vault_secret.user_id.value
  }

  template {
    container {
      name   = "mail"
      image  = "${azurerm_container_registry.main.login_server}/mcp-mail:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name        = "AZURE_TENANT_ID"
        secret_name = "azure-tenant-id"
      }
      env {
        name        = "AZURE_CLIENT_ID"
        secret_name = "azure-client-id"
      }
      env {
        name        = "AZURE_CLIENT_SECRET"
        secret_name = "azure-client-secret"
      }
      env {
        name        = "AZURE_USER_ID"
        secret_name = "azure-user-id"
      }
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }
}

# ─── OneDrive MCP Server ──────────────────────────────────────────────
resource "azurerm_container_app" "onedrive_mcp" {
  name                         = "${var.project_name}-mcp-onedrive-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = all
  }

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8003
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  secret {
    name  = "azure-tenant-id"
    value = azurerm_key_vault_secret.tenant_id.value
  }
  secret {
    name  = "azure-client-id"
    value = azurerm_key_vault_secret.client_id.value
  }
  secret {
    name  = "azure-client-secret"
    value = azurerm_key_vault_secret.client_secret.value
  }
  secret {
    name  = "azure-user-id"
    value = azurerm_key_vault_secret.user_id.value
  }

  template {
    container {
      name   = "onedrive"
      image  = "${azurerm_container_registry.main.login_server}/mcp-onedrive:latest"
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name        = "AZURE_TENANT_ID"
        secret_name = "azure-tenant-id"
      }
      env {
        name        = "AZURE_CLIENT_ID"
        secret_name = "azure-client-id"
      }
      env {
        name        = "AZURE_CLIENT_SECRET"
        secret_name = "azure-client-secret"
      }
      env {
        name        = "AZURE_USER_ID"
        secret_name = "azure-user-id"
      }
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }
}

# ─── Knowledge Base MCP Server ────────────────────────────────────────
resource "azurerm_container_app" "kb_mcp" {
  name                         = "${var.project_name}-mcp-kb-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8005
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  template {
    container {
      name   = "kb"
      image  = "${azurerm_container_registry.main.login_server}/mcp-knowledge-base:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }

  lifecycle {
    ignore_changes = all
  }
}

# ─── Memory / Personal Context MCP Server ─────────────────────────────
resource "azurerm_container_app" "memory_mcp" {
  name                         = "${var.project_name}-mcp-memory-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8004
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  template {
    container {
      name   = "memory"
      image  = "${azurerm_container_registry.main.login_server}/mcp-memory:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }

  lifecycle {
    ignore_changes = all
  }
}

# ─── Document Generation MCP Server ─────────────────────────────────────
resource "azurerm_container_app" "doc_mcp" {
  name                         = "${var.project_name}-mcp-doc-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8006
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  template {
    container {
      name   = "doc"
      image  = "${azurerm_container_registry.main.login_server}/mcp-document-generation:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }

  lifecycle {
    ignore_changes = all
  }
}

# ─── Analytics MCP Server ───────────────────────────────────────────────
resource "azurerm_container_app" "analytics_mcp" {
  name                         = "${var.project_name}-mcp-analytics-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8007
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  template {
    container {
      name   = "analytics"
      image  = "${azurerm_container_registry.main.login_server}/mcp-analytics:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }

  lifecycle {
    ignore_changes = all
  }
}

# ─── Dashboard MCP Server ───────────────────────────────────────────────
resource "azurerm_container_app" "dashboard_mcp" {
  name                         = "${var.project_name}-mcp-dashboard-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = 8009
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  template {
    container {
      name   = "dashboard"
      image  = "${azurerm_container_registry.main.login_server}/mcp-dashboard:latest"
      cpu    = 0.25
      memory = "0.5Gi"
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }

  lifecycle {
    ignore_changes = all
  }
}

# ─── Context Forge Gateway (Internal) ─────────────────────────────────
resource "azurerm_container_app" "context_forge" {
  count                        = var.context_forge_enabled ? 1 : 0
  name                         = "${var.project_name}-context-forge-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = false
    target_port      = var.context_forge_container_port
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }

  template {
    container {
      name   = "context-forge"
      image  = var.context_forge_image
      cpu    = 0.5
      memory = "1.0Gi"
      env {
        name  = "PORT"
        value = tostring(var.context_forge_container_port)
      }
    }
    min_replicas = var.container_app_min_replicas
    max_replicas = var.container_app_max_replicas
  }

  depends_on = [
    azurerm_container_app.sql_mcp,
    azurerm_container_app.files_mcp,
    azurerm_container_app.mail_mcp,
    azurerm_container_app.onedrive_mcp,
    azurerm_container_app.memory_mcp,
    azurerm_container_app.kb_mcp,
    azurerm_container_app.doc_mcp,
    azurerm_container_app.analytics_mcp,
    azurerm_container_app.dashboard_mcp,
  ]
}

# ─── Orchestrator (Public-Facing) ─────────────────────────────────────
resource "azurerm_container_app" "orchestrator" {
  name                         = "${var.project_name}-orchestrator-${var.environment}"
  container_app_environment_id = azurerm_container_app_environment.main.id
  resource_group_name          = azurerm_resource_group.main.name
  revision_mode                = "Single"

  lifecycle {
    ignore_changes = all
  }

  identity {
    type = "SystemAssigned"
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "http"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }

  }

  registry {
    server   = azurerm_container_registry.main.login_server
    identity = "system"
  }
  secret {
    name  = "openai-endpoint"
    value = azurerm_key_vault_secret.openai_endpoint.value
  }
  secret {
    name  = "openai-api-key"
    value = azurerm_key_vault_secret.openai_key.value
  }
  dynamic "secret" {
    for_each = var.obot_api_key != "" ? [1] : []
    content {
      name  = "obot-api-key"
      value = var.obot_api_key
    }
  }
  dynamic "secret" {
    for_each = var.context_forge_api_key != "" ? [1] : []
    content {
      name  = "context-forge-api-key"
      value = var.context_forge_api_key
    }
  }

  template {
    container {
      name   = "orchestrator"
      image  = "${azurerm_container_registry.main.login_server}/orchestrator:latest"
      cpu    = 1.0
      memory = "2.0Gi"
      env {
        name        = "AZURE_OPENAI_ENDPOINT"
        secret_name = "openai-endpoint"
      }
      env {
        name        = "AZURE_OPENAI_API_KEY"
        secret_name = "openai-api-key"
      }
      env {
        name  = "AZURE_OPENAI_DEPLOYMENT"
        value = "gpt-4o"
      }
      env {
        name  = "LLM_PROVIDER"
        value = var.llm_provider
      }
      env {
        name  = "OBOT_BASE_URL"
        value = var.obot_base_url
      }
      env {
        name  = "OBOT_MODEL"
        value = var.obot_model
      }
      env {
        name  = "OBOT_API_REQUIRED"
        value = var.obot_api_required ? "true" : "false"
      }
      dynamic "env" {
        for_each = var.obot_api_key != "" ? [1] : []
        content {
          name        = "OBOT_API_KEY"
          secret_name = "obot-api-key"
        }
      }
      env {
        name  = "MCP_SQL_URL"
        value = "http://${azurerm_container_app.sql_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_FILES_URL"
        value = "http://${azurerm_container_app.files_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_MAIL_URL"
        value = "http://${azurerm_container_app.mail_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_ONEDRIVE_URL"
        value = "http://${azurerm_container_app.onedrive_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_KB_URL"
        value = "http://${azurerm_container_app.kb_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_MEMORY_URL"
        value = "http://${azurerm_container_app.memory_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_DOC_URL"
        value = "http://${azurerm_container_app.doc_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_ANALYTICS_URL"
        value = "http://${azurerm_container_app.analytics_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "MCP_DASHBOARD_URL"
        value = "http://${azurerm_container_app.dashboard_mcp.ingress[0].fqdn}/mcp"
      }
      env {
        name  = "CONTEXT_FORGE_ENABLED"
        value = var.context_forge_enabled ? "true" : "false"
      }
      env {
        name  = "CONTEXT_FORGE_BASE_URL"
        value = var.context_forge_base_url_override != "" ? var.context_forge_base_url_override : (var.context_forge_enabled ? "http://${azurerm_container_app.context_forge[0].ingress[0].fqdn}" : "")
      }
      env {
        name  = "CONTEXT_FORGE_TIMEOUT_SECONDS"
        value = tostring(var.context_forge_timeout_seconds)
      }
      env {
        name  = "CONTEXT_FORGE_FALLBACK_MODE"
        value = var.context_forge_fallback_mode
      }
      env {
        name  = "CONTEXT_FORGE_CACHE_ENABLED"
        value = var.context_forge_cache_enabled ? "true" : "false"
      }
      dynamic "env" {
        for_each = var.context_forge_api_key != "" ? [1] : []
        content {
          name        = "CONTEXT_FORGE_API_KEY"
          secret_name = "context-forge-api-key"
        }
      }
      env {
        name  = "REPORT_OUTPUT_DIR"
        value = "/tmp/reports"
      }
      env {
        name  = "CORS_ORIGINS"
        value = var.ui_custom_domain != null ? "https://${azurerm_static_web_app.ui.default_host_name},https://${var.ui_custom_domain}" : "https://${azurerm_static_web_app.ui.default_host_name}"
      }
      env {
        name  = "REDIS_URL"
        value = var.redis_connection_string
      }
      env {
        name  = "AZURE_STORAGE_ACCOUNT"
        value = azurerm_storage_account.main.name
      }
      env {
        name  = "AZURE_STORAGE_KEY"
        value = azurerm_storage_account.main.primary_access_key
      }
      env {
        name  = "JWT_SECRET"
        value = var.jwt_secret
      }
      env {
        name  = "AUTH_DB_PATH"
        value = "/tmp/evieai_auth.db"
      }
      env {
        name  = "DEFAULT_ADMIN_EMAIL"
        value = var.default_admin_email
      }
      env {
        name  = "DEFAULT_ADMIN_PASSWORD"
        value = var.default_admin_password
      }
      env {
        name  = "PROJECT_NAME"
        value = var.project_name
      }
      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }
      env {
        name  = "RESOURCE_GROUP"
        value = azurerm_resource_group.main.name
      }
      env {
        name  = "AZURE_SUBSCRIPTION_ID"
        value = data.azurerm_client_config.current.subscription_id
      }
    }
    min_replicas = 1
    max_replicas = var.container_app_max_replicas
  }
}

# NOTE: Custom domain was created manually in Azure Portal and removed from terraform state
# to avoid certificate_id parsing issues with the azurerm provider.
# Domain api.resiq.co remains bound to the orchestrator Container App.

# ─── Managed Identity → Key Vault Role Assignments ────────────────────
resource "azurerm_role_assignment" "orchestrator_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.orchestrator.identity[0].principal_id
}

resource "azurerm_role_assignment" "sql_mcp_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.sql_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "files_mcp_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.files_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "mail_mcp_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.mail_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "onedrive_mcp_kv" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_container_app.onedrive_mcp.identity[0].principal_id
}

# ─── Managed Identity → ACR Role Assignments ───────────────────────
resource "azurerm_role_assignment" "orchestrator_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.orchestrator.identity[0].principal_id
}

resource "azurerm_role_assignment" "sql_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.sql_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "files_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.files_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "mail_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.mail_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "onedrive_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.onedrive_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "kb_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.kb_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "memory_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.memory_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "doc_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.doc_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "analytics_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.analytics_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "dashboard_mcp_acr_pull" {
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.dashboard_mcp.identity[0].principal_id
}

resource "azurerm_role_assignment" "context_forge_acr_pull" {
  count                = var.context_forge_enabled ? 1 : 0
  scope                = azurerm_container_registry.main.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_container_app.context_forge[0].identity[0].principal_id
}

# ─── Static Web App ───────────────────────────────────────────────────
resource "azurerm_static_web_app" "ui" {
  name                = "${var.project_name}-ui-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  location            = "eastus2" # SWA free tier is region-agnostic; pick any valid
  sku_tier            = "Free"
  sku_size            = "Free"
  tags                = var.tags
}

resource "azurerm_static_web_app_custom_domain" "ui" {
  count             = var.ui_custom_domain != null ? 1 : 0
  static_web_app_id = azurerm_static_web_app.ui.id
  domain_name       = var.ui_custom_domain
  validation_type   = "cname-delegation"
}

# ─── Monitoring & Alerts ──────────────────────────────────────────────

resource "azurerm_monitor_action_group" "main" {
  count               = var.alert_email != null ? 1 : 0
  name                = "ag-${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  short_name          = "aiagent2"

  email_receiver {
    name                    = "admin"
    email_address           = var.alert_email
    use_common_alert_schema = true
  }
}

resource "azurerm_monitor_metric_alert" "container_restarts" {
  count               = var.alert_email != null ? 1 : 0
  name                = "Container App Restarts - ${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.orchestrator.id]
  description         = "Alert when the orchestrator container restarts more than 3 times in 10 minutes"
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "RestartCount"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 3
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }
}

resource "azurerm_monitor_metric_alert" "http_5xx" {
  count               = var.alert_email != null ? 1 : 0
  name                = "HTTP 5xx Errors - ${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_container_app.orchestrator.id]
  description         = "Alert when HTTP 5xx errors exceed 1% of total requests"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT15M"

  criteria {
    metric_namespace = "Microsoft.App/containerApps"
    metric_name      = "Http5xx"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 5
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }
}

resource "azurerm_monitor_metric_alert" "openai_throttling" {
  count               = var.alert_email != null ? 1 : 0
  name                = "OpenAI Rate Limit - ${var.project_name}-${var.environment}"
  resource_group_name = azurerm_resource_group.main.name
  scopes              = [azurerm_cognitive_account.openai.id]
  description         = "Alert when Azure OpenAI is throttling requests (BlockedCalls > 0)"
  severity            = 1
  frequency           = "PT5M"
  window_size         = "PT5M"

  criteria {
    metric_namespace = "Microsoft.CognitiveServices/accounts"
    metric_name      = "BlockedCalls"
    aggregation      = "Total"
    operator         = "GreaterThan"
    threshold        = 0
  }

  action {
    action_group_id = azurerm_monitor_action_group.main[0].id
  }
}
