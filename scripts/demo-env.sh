#!/usr/bin/env bash
# One command to run the whole EvieAI demo environment on Azure.
#
#   scripts/demo-env.sh down     # stop all container apps (save $$)
#   scripts/demo-env.sh up       # start all apps, wait until healthy, re-seed demo data
#   scripts/demo-env.sh status   # show running status of every app
#
# Why this exists:
#   * `az containerapp stop/start` is missing from this CLI build, so we call
#     the ARM REST API directly.
#   * The orchestrator's workflow DB lives on ephemeral storage, so `up`
#     re-seeds the demo workflows every time.
set -euo pipefail

RG="rg-evie62a1-dev"
API="2024-03-01"
BASE="https://evie62a1-orchestrator-dev.whitebush-68f2367a.eastus2.azurecontainerapps.io"
HERE="$(cd "$(dirname "$0")" && pwd)"
ACTION="${1:-status}"

require_login() {
  if ! az account show >/dev/null 2>&1; then
    echo "Not logged into Azure. Run:"
    echo "  az login --tenant 153ae1c6-1735-43ac-a2f3-ccf3dfb2da69"
    exit 1
  fi
}

show_status() {
  az containerapp list -g "$RG" \
    --query "[].{name:name, status:properties.runningStatus}" -o table
}

power() { # $1 = stop|start
  local action="$1"
  local sub
  sub=$(az account show --query id -o tsv)
  echo "Sending $action to all container apps in $RG ..."
  for app in $(az containerapp list -g "$RG" --query "[].name" -o tsv); do
    az rest --method post \
      --url "https://management.azure.com/subscriptions/$sub/resourceGroups/$RG/providers/Microsoft.App/containerApps/$app/$action?api-version=$API" \
      --only-show-errors && echo "  $action: $app" &
  done
  wait
}

wait_healthy() {
  echo -n "Waiting for orchestrator to become healthy"
  for _ in $(seq 1 60); do
    if curl -sf --max-time 8 "$BASE/health" >/dev/null 2>&1; then
      echo " ... healthy."
      return 0
    fi
    echo -n "."
    sleep 5
  done
  echo " timed out. Check 'scripts/demo-env.sh status'."
  return 1
}

case "$ACTION" in
  down)
    require_login
    power stop
    echo
    show_status
    echo "All apps stopping. Azure compute billing pauses once they report Stopped."
    ;;
  up)
    require_login
    power start
    echo
    wait_healthy
    echo "Seeding demo workflows ..."
    "$HERE/seed_demo_workflows.sh"
    echo
    show_status
    echo "EvieAI is up. Demo login: admin@evieai.local / admin (auto-login on demo.resiq.co)."
    ;;
  status)
    require_login
    show_status
    ;;
  *)
    echo "usage: $0 up|down|status"
    exit 1
    ;;
esac
