#!/bin/bash

# EvieAI Environment Manager - Start/Stop to reduce costs
# Usage: ./manage-environment.sh start|stop|status

set -e

# Configuration
RESOURCE_GROUP="${RESOURCE_GROUP:-rg-aiagent2-dev}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
ACTION="${1:-status}"

# List of all services
SERVICES=(
  "aiagent2-orchestrator-dev"
  "aiagent2-mcp-sql-dev"
  "aiagent2-mcp-mail-dev"
  "aiagent2-mcp-files-dev"
  "aiagent2-mcp-onedrive-dev"
  "aiagent2-mcp-kb-dev"
  "aiagent2-mcp-memory-dev"
  "aiagent2-mcp-doc-dev"
  "aiagent2-mcp-analytics-dev"
  "aiagent2-mcp-dashboard-dev"
  "aiagent2-dab-dev"
  "aiagent2-mcp-postgresql-dev"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

function print_info() {
  echo -e "${CYAN}$1${NC}"
}

function print_success() {
  echo -e "${GREEN}✓ $1${NC}"
}

function print_warning() {
  echo -e "${YELLOW}⚠ $1${NC}"
}

function print_error() {
  echo -e "${RED}✗ $1${NC}"
}

function start_environment() {
  print_info "=== Starting EvieAI Environment ==="
  print_info "Scaling all services to 1 replica..."
  
  local successful=0
  local failed=0
  
  for service in "${SERVICES[@]}"; do
    echo "Starting $service..."
    if az containerapp update \
      --name "$service" \
      --resource-group "$RESOURCE_GROUP" \
      --min-replicas 1 \
      --max-replicas 3 \
      --output none 2>/dev/null; then
      print_success "$service started"
      ((successful++))
    else
      print_error "Failed to start $service"
      ((failed++))
    fi
  done
  
  echo ""
  print_info "=== Startup Complete ==="
  print_success "Started: $successful services"
  if [ $failed -gt 0 ]; then
    print_error "Failed: $failed services"
  fi
  print_warning "Services are now running. Costs are accruing."
}

function stop_environment() {
  print_info "=== Stopping EvieAI Environment ==="
  print_warning "Scaling all services to 0 replicas..."
  print_warning "NOTE: Stopping services will terminate current operations"
  
  read -p "Continue with shutdown? (yes/no) " -r response
  if [ "$response" != "yes" ]; then
    print_info "Shutdown cancelled."
    return
  fi
  
  local successful=0
  local failed=0
  
  for service in "${SERVICES[@]}"; do
    echo "Stopping $service..."
    if az containerapp update \
      --name "$service" \
      --resource-group "$RESOURCE_GROUP" \
      --min-replicas 0 \
      --max-replicas 0 \
      --output none 2>/dev/null; then
      print_success "$service stopped"
      ((successful++))
    else
      print_error "Failed to stop $service"
      ((failed++))
    fi
  done
  
  echo ""
  print_info "=== Shutdown Complete ==="
  print_success "Stopped: $successful services"
  if [ $failed -gt 0 ]; then
    print_error "Failed: $failed services"
  fi
  print_success "Services are now stopped. Only storage/database costs remain."
}

function get_environment_status() {
  print_info "=== EvieAI Environment Status ==="
  echo ""
  
  local running=0
  local stopped=0
  
  for service in "${SERVICES[@]}"; do
    replicas=$(az containerapp show \
      --name "$service" \
      --resource-group "$RESOURCE_GROUP" \
      --query "properties.template.scale.minReplicas" \
      -o tsv 2>/dev/null || echo "error")
    
    if [ "$replicas" = "0" ]; then
      print_warning "⏹️  $service (STOPPED)"
      ((stopped++))
    elif [ "$replicas" != "error" ]; then
      print_success "▶️  $service (RUNNING - $replicas replicas)"
      ((running++))
    else
      echo "❓ $service (status unknown)"
    fi
  done
  
  echo ""
  print_info "Summary: $running running, $stopped stopped"
}

# Main execution
echo ""
case "$ACTION" in
  start)
    start_environment
    ;;
  stop)
    stop_environment
    ;;
  status)
    get_environment_status
    ;;
  *)
    echo "Usage: $0 {start|stop|status}"
    exit 1
    ;;
esac
echo ""
