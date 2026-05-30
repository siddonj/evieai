#Requires -Version 7.0
<#
.SYNOPSIS
Manage EvieAI environment startup/shutdown to reduce Azure costs

.DESCRIPTION
Scales Container Apps up/down to control costs. When scaled to 0 replicas,
services consume no compute costs (except storage/database).

.PARAMETER Action
"start" or "stop" or "status"

.PARAMETER ResourceGroup
Azure resource group name (default: rg-aiagent2-dev)

.PARAMETER Environment
Environment name: dev, staging, prod (default: dev)

.EXAMPLE
.\manage-environment.ps1 -Action start
.\manage-environment.ps1 -Action stop
.\manage-environment.ps1 -Action status
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("start", "stop", "status")]
    [string]$Action,
    
    [string]$ResourceGroup = "rg-aiagent2-dev",
    [string]$Environment = "dev"
)

# List of all EvieAI services
$services = @(
    "aiagent2-orchestrator-dev",
    "aiagent2-mcp-sql-dev",
    "aiagent2-mcp-mail-dev",
    "aiagent2-mcp-files-dev",
    "aiagent2-mcp-onedrive-dev",
    "aiagent2-mcp-kb-dev",
    "aiagent2-mcp-memory-dev",
    "aiagent2-mcp-doc-dev",
    "aiagent2-mcp-analytics-dev",
    "aiagent2-mcp-dashboard-dev",
    "aiagent2-dab-dev",
    "aiagent2-mcp-postgresql-dev"
)

function Write-Status {
    param([string]$Message, [ValidateSet("Info", "Success", "Warning", "Error")]$Type = "Info")
    $colors = @{
        "Info" = "Cyan"
        "Success" = "Green"
        "Warning" = "Yellow"
        "Error" = "Red"
    }
    Write-Host $Message -ForegroundColor $colors[$Type]
}

function Start-Environment {
    Write-Status "=== Starting EvieAI Environment ===" "Info"
    Write-Status "Scaling all services to 1 replica..." "Info"
    
    $successful = 0
    $failed = 0
    
    foreach ($service in $services) {
        try {
            Write-Host "Starting $service..."
            az containerapp update `
                --name $service `
                --resource-group $ResourceGroup `
                --min-replicas 1 `
                --max-replicas 3 `
                --output none
            
            Write-Status "✓ $service started" "Success"
            $successful++
        }
        catch {
            Write-Status "✗ Failed to start $service: $_" "Error"
            $failed++
        }
    }
    
    Write-Status "`n=== Startup Complete ===" "Info"
    Write-Status "Started: $successful services" "Success"
    if ($failed -gt 0) {
        Write-Status "Failed: $failed services" "Error"
    }
    Write-Status "Services are now running. Costs are accruing." "Warning"
}

function Stop-Environment {
    Write-Status "=== Stopping EvieAI Environment ===" "Info"
    Write-Status "Scaling all services to 0 replicas..." "Info"
    Write-Status "NOTE: Stopping services will terminate current operations" "Warning"
    
    $response = Read-Host "Continue with shutdown? (yes/no)"
    if ($response -ne "yes") {
        Write-Status "Shutdown cancelled." "Info"
        return
    }
    
    $successful = 0
    $failed = 0
    
    foreach ($service in $services) {
        try {
            Write-Host "Stopping $service..."
            az containerapp update `
                --name $service `
                --resource-group $ResourceGroup `
                --min-replicas 0 `
                --max-replicas 0 `
                --output none
            
            Write-Status "✓ $service stopped" "Success"
            $successful++
        }
        catch {
            Write-Status "✗ Failed to stop $service: $_" "Error"
            $failed++
        }
    }
    
    Write-Status "`n=== Shutdown Complete ===" "Info"
    Write-Status "Stopped: $successful services" "Success"
    if ($failed -gt 0) {
        Write-Status "Failed: $failed services" "Error"
    }
    Write-Status "Services are now stopped. Only storage/database costs remain." "Success"
}

function Get-EnvironmentStatus {
    Write-Status "=== EvieAI Environment Status ===" "Info"
    Write-Host ""
    
    $running = 0
    $stopped = 0
    
    foreach ($service in $services) {
        try {
            $replicas = az containerapp show `
                --name $service `
                --resource-group $ResourceGroup `
                --query "properties.template.scale.minReplicas" `
                -o tsv
            
            if ($replicas -eq "0") {
                Write-Status "⏹️  $service (STOPPED)" "Warning"
                $stopped++
            }
            else {
                Write-Status "▶️  $service (RUNNING - $replicas replicas)" "Success"
                $running++
            }
        }
        catch {
            Write-Status "❓ $service (status unknown)" "Error"
        }
    }
    
    Write-Host ""
    Write-Status "Summary: $running running, $stopped stopped" "Info"
}

# Main execution
Write-Host ""
switch ($Action) {
    "start" { Start-Environment }
    "stop" { Stop-Environment }
    "status" { Get-EnvironmentStatus }
}
Write-Host ""
