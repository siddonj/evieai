terraform {
  required_version = ">= 1.7.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.48"
    }
  }

  # Uncomment and update after completing the one-time backend bootstrap.
  # See terraform/README.md for instructions.
  #
  backend "azurerm" {
    resource_group_name  = "rg-terraform-state"
    storage_account_name = "aiagent2tfstate"
    container_name       = "tfstate"
    key                  = "aiagent2.tfstate"
  }
}

provider "azurerm" {
  skip_provider_registration = true

  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }

    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = false
    }
  }
}

provider "azuread" {}
