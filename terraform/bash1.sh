```bash
# 1. Create a resource group for Terraform state
az group create --name rg-terraform-state --location eastus2

# 2. Create a storage account (name must be globally unique, 3-24 lowercase letters)
az storage account create \
  --name aiagent2tfstate \
  --resource-group rg-terraform-state \
  --location eastus2 \
  --sku Standard_LRS

# 3. Create a container inside the storage account
az storage container create \
  --name tfstate \
  --account-name aiagent2tfstate
```