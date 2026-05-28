# ─── General ─────────────────────────────────────────────────────────
variable "project_name" {
  description = "Short project prefix used in all resource names. Must be alphanumeric, lowercase, 3-12 chars."
  type        = string
  validation {
    condition     = can(regex("^[a-z0-9]{3,12}$", var.project_name))
    error_message = "project_name must be lowercase alphanumeric, 3-12 characters."
  }
}

variable "environment" {
  description = "Environment name: dev, staging, or prod."
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging, or prod."
  }
}

variable "location" {
  description = "Azure region. Must support Azure OpenAI (eastus2, swedencentral, westus3)."
  type        = string
  default     = "eastus2"
  validation {
    condition     = contains(["eastus2", "swedencentral", "westus3"], var.location)
    error_message = "location must be eastus2, swedencentral, or westus3 for GPT-4o availability."
  }
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default = {
    project    = "ai-qa-app"
    managed_by = "terraform"
  }
}

# ─── Security ────────────────────────────────────────────────────────
variable "sql_admin_password" {
  description = "Strong password for Azure SQL admin. Min 8 chars, must include upper, lower, number, symbol."
  type        = string
  sensitive   = true
  validation {
    condition     = length(var.sql_admin_password) >= 8
    error_message = "sql_admin_password must be at least 8 characters."
  }
}

variable "target_user_upn" {
  description = "UPN (email) of the Microsoft 365 user whose mail/files the app will access."
  type        = string
}

# ─── Scale / Cost ────────────────────────────────────────────────────
variable "openai_tpm_capacity" {
  description = "OpenAI tokens-per-minute capacity in thousands. 10 = 10,000 TPM."
  type        = number
  default     = 10
}

variable "container_app_min_replicas" {
  description = "Minimum replicas for non-orchestrator Container Apps. Set to 0 to scale-to-zero and save cost."
  type        = number
  default     = 0
}

variable "container_app_max_replicas" {
  description = "Maximum replicas for Container Apps."
  type        = number
  default     = 3
}

variable "ui_custom_domain" {
  description = "Custom domain for the React chat UI (Static Web App), e.g. demo.resiq.co. Leave null to use the Azure default hostname only."
  type        = string
  default     = null
}

variable "api_custom_domain" {
  description = "Custom domain for the orchestrator API (Container App), e.g. api.resiq.co. Leave null to use the Azure FQDN only."
  type        = string
  default     = null
}

variable "alert_email" {
  description = "Email address to receive Azure Monitor alerts. Set to a real address to enable alerting."
  type        = string
  default     = null
  sensitive   = true
}

# ─── Web UI Auth ─────────────────────────────────────────
variable "jwt_secret" {
  description = "HS256 secret for signing web UI JWT tokens. Generate with: openssl rand -hex 32"
  type        = string
  sensitive   = true
}

variable "default_admin_email" {
  description = "Email for the default admin account seeded on first startup."
  type        = string
  default     = "admin@evieai.local"
}

variable "default_admin_password" {
  description = "Password for the default admin account. Change after first login."
  type        = string
  default     = "admin"
  sensitive   = true
}
