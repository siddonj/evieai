#!/usr/bin/env bash
# Stop or start all EvieAI Container Apps.
# Usage: scripts/containerapps.sh stop|start|status
# az containerapp has no app-level stop/start command, so this calls the ARM API.
set -euo pipefail

ACTION="${1:-status}"
RG="rg-evie62a1-dev"
API="2024-03-01"

if [[ "$ACTION" == "status" ]]; then
  az containerapp list -g "$RG" --query "[].{name:name, status:properties.runningStatus}" -o table
  exit 0
fi

if [[ "$ACTION" != "stop" && "$ACTION" != "start" ]]; then
  echo "usage: $0 stop|start|status" >&2
  exit 1
fi

SUB=$(az account show --query id -o tsv)
for app in $(az containerapp list -g "$RG" --query "[].name" -o tsv); do
  az rest --method post \
    --url "https://management.azure.com/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.App/containerApps/$app/$ACTION?api-version=$API" \
    --only-show-errors && echo "$ACTION: $app" &
done
wait
az containerapp list -g "$RG" --query "[].{name:name, status:properties.runningStatus}" -o table
