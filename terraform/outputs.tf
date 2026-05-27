output "resource_group_name" {
  description = "Name of the provisioned resource group."
  value       = azurerm_resource_group.main.name
}

output "acr_login_server" {
  description = "URL of the Azure Container Registry. Use this in Docker tags."
  value       = azurerm_container_registry.main.login_server
}

output "acr_admin_username" {
  description = "ACR admin username (for CI/CD)."
  value       = azurerm_container_registry.main.admin_username
}

output "acr_admin_password" {
  description = "ACR admin password (for CI/CD). Treat as a secret."
  value       = azurerm_container_registry.main.admin_password
  sensitive   = true
}

output "key_vault_name" {
  description = "Name of the Azure Key Vault."
  value       = azurerm_key_vault.main.name
}

output "key_vault_uri" {
  description = "URI of the Azure Key Vault."
  value       = azurerm_key_vault.main.vault_uri
}

output "openai_endpoint" {
  description = "Azure OpenAI endpoint URL."
  value       = azurerm_cognitive_account.openai.endpoint
}

output "sql_server_fqdn" {
  description = "Fully qualified domain name of the SQL server."
  value       = azurerm_mssql_server.main.fully_qualified_domain_name
}

output "sql_connection_string" {
  description = "ADO.NET connection string for the SQL database."
  value       = azurerm_key_vault_secret.sql_conn.value
  sensitive   = true
}

output "storage_account_name" {
  description = "Name of the Azure Storage account."
  value       = azurerm_storage_account.main.name
}

output "file_share_name" {
  description = "Name of the Azure Files share."
  value       = azurerm_storage_share.main.name
}

output "orchestrator_url" {
  description = "Public HTTPS URL of the orchestrator Container App."
  value       = "https://${azurerm_container_app.orchestrator.ingress[0].fqdn}"
}

output "sql_mcp_internal_url" {
  description = "Internal URL of the SQL MCP server."
  value       = "http://${azurerm_container_app.sql_mcp.ingress[0].fqdn}/mcp"
}

output "files_mcp_internal_url" {
  description = "Internal URL of the File Share MCP server."
  value       = "http://${azurerm_container_app.files_mcp.ingress[0].fqdn}/mcp"
}

output "mail_mcp_internal_url" {
  description = "Internal URL of the O365 Mail MCP server."
  value       = "http://${azurerm_container_app.mail_mcp.ingress[0].fqdn}/mcp"
}

output "onedrive_mcp_internal_url" {
  description = "Internal URL of the OneDrive MCP server."
  value       = "http://${azurerm_container_app.onedrive_mcp.ingress[0].fqdn}/mcp"
}

output "kb_mcp_internal_url" {
  description = "Internal URL of the Knowledge Base MCP server."
  value       = "http://${azurerm_container_app.kb_mcp.ingress[0].fqdn}/mcp"
}

output "memory_mcp_internal_url" {
  description = "Internal URL of the Memory / Personal Context MCP server."
  value       = "http://${azurerm_container_app.memory_mcp.ingress[0].fqdn}/mcp"
}

output "doc_mcp_internal_url" {
  description = "Internal URL of the Document Generation MCP server."
  value       = "http://${azurerm_container_app.doc_mcp.ingress[0].fqdn}/mcp"
}

output "analytics_mcp_internal_url" {
  description = "Internal URL of the Analytics MCP server."
  value       = "http://${azurerm_container_app.analytics_mcp.ingress[0].fqdn}/mcp"
}

output "ui_default_hostname" {
  description = "Default hostname of the Static Web App (chat UI)."
  value       = azurerm_static_web_app.ui.default_host_name
}

output "ui_custom_domain_url" {
  description = "Custom domain URL of the Static Web App (chat UI). Only populated when ui_custom_domain is set."
  value       = var.ui_custom_domain != null ? "https://${var.ui_custom_domain}" : null
}

output "ui_cname_target" {
  description = "DNS CNAME target for the custom domain. Create a CNAME record pointing your domain to this value."
  value       = azurerm_static_web_app.ui.default_host_name
}

output "api_custom_domain_url" {
  description = "Custom domain URL of the orchestrator API. Only populated when api_custom_domain is set."
  value       = var.api_custom_domain != null ? "https://${var.api_custom_domain}" : null
}

output "api_cname_target" {
  description = "DNS CNAME target for the API custom domain. Create a CNAME record pointing your domain to this value."
  value       = azurerm_container_app.orchestrator.ingress[0].fqdn
}

output "api_custom_domain_verification_id" {
  description = "TXT verification ID for the API custom domain. Create a TXT record: asuid.<api_custom_domain> -> <this value> BEFORE running terraform apply."
  value       = var.api_custom_domain != null ? azurerm_container_app.orchestrator.custom_domain_verification_id : null
  sensitive   = true
}

output "entra_app_client_id" {
  description = "Client ID of the Entra ID app registration (for Graph API)."
  value       = azuread_application.graph.client_id
}

output "entra_app_object_id" {
  description = "Object ID of the Entra ID app registration."
  value       = azuread_application.graph.object_id
}

output "entra_service_principal_object_id" {
  description = "Object ID of the Entra ID service principal (needed for admin consent)."
  value       = azuread_service_principal.graph.object_id
}
