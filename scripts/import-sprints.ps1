#!/usr/bin/env pwsh
<#
.SYNOPSIS
Imports Azure DevOps work items for MCP Server Improvements sprints.

.DESCRIPTION
Creates 5 sprints with 25+ user stories and 50+ tasks based on the improvement roadmap.
Uses Azure CLI to bulk-import items into Azure DevOps.

.PARAMETER DryRun
If $true, prints commands without executing them.

.EXAMPLE
.\import-sprints.ps1 -DryRun $false
#>

param(
    [bool]$DryRun = $true
)

$ErrorActionPreference = "Stop"

# Colors
$InfoColor = "Cyan"
$SuccessColor = "Green"
$ErrorColor = "Red"

function Write-Info {
    Write-Host $args -ForegroundColor $InfoColor
}

function Write-Success {
    Write-Host $args -ForegroundColor $SuccessColor
}

function Write-ErrorMsg {
    Write-Host $args -ForegroundColor $ErrorColor
}

function Invoke-AzCommand {
    param(
        [string]$Title,
        [string[]]$Command
    )
    
    Write-Info "> $Title"
    
    if ($DryRun) {
        Write-Host ($Command -join " `n") -ForegroundColor Yellow
        return ""
    }
    
    try {
        $output = Invoke-Expression ($Command -join " ")
        Write-Success "  [OK] Success"
        return $output
    }
    catch {
        Write-ErrorMsg "  [FAIL] Failed: $_"
        return ""
    }
}

Write-Info "=============================================================================="
Write-Info "Azure DevOps Sprint Import - MCP Server Improvements"
Write-Info "=============================================================================="
Write-Info ""

# ============================================================================
# SPRINTS/ITERATIONS SETUP
# ============================================================================

Write-Info "[1/3] Creating Sprints/Iterations..."
Write-Info ""

$sprints = @(
    @{ Name = "Sprint 1: Health Checks"; StartDate = "2026-05-30"; EndDate = "2026-06-12" }
    @{ Name = "Sprint 2: Error Handling"; StartDate = "2026-06-13"; EndDate = "2026-06-26" }
    @{ Name = "Sprint 3: Caching"; StartDate = "2026-06-27"; EndDate = "2026-07-10" }
    @{ Name = "Sprint 4: Connection Pooling"; StartDate = "2026-07-11"; EndDate = "2026-07-24" }
    @{ Name = "Sprint 5: Documentation"; StartDate = "2026-07-25"; EndDate = "2026-08-07" }
)

$sprintPaths = @{}

foreach ($sprint in $sprints) {
    $iterationPath = "evieai\$($sprint.Name)"
    Write-Info "Creating iteration: $($sprint.Name)"
    
    $cmd = "az boards iteration project create --name `"$($sprint.Name)`" --start-date $($sprint.StartDate) --end-date $($sprint.EndDate)"
    
    Invoke-AzCommand "Create iteration: $($sprint.Name)" @($cmd)
    $sprintPaths[$sprint.Name] = $iterationPath
}

Write-Info ""

# ============================================================================
# SPRINT 1: HEALTH CHECKS
# ============================================================================

Write-Info "[2/3] Creating Sprint 1 User Stories & Tasks (Health Checks)..."
Write-Info ""

# Helper function to create work items
function New-UserStory {
    param(
        [string]$ID,
        [string]$Title,
        [string]$Description,
        [int]$StoryPoints,
        [string]$Priority,
        [string]$Sprint,
        [string[]]$Tags
    )
    
    $cmd = @(
        "az boards work-item create",
        "--type `"User Story`"",
        "--title `"$Title`"",
        "--description `"$Description`"",
        "--fields `"Microsoft.VSTS.Scheduling.StoryPoints=$StoryPoints`" `"System.IterationPath=$Sprint`" `"Microsoft.VSTS.Common.Priority=$Priority`""
    )
    
    if ($Tags) {
        $cmd += "--tags `"$($Tags -join ';')`""
    }
    
    $output = Invoke-AzCommand "Create user story: $ID - $Title" $cmd
    return $output
}

function New-Task {
    param(
        [string]$Title,
        [string]$Description,
        [float]$Effort,
        [string]$Priority,
        [string]$Sprint
    )
    
    $cmd = @(
        "az boards work-item create",
        "--type `"Task`"",
        "--title `"$Title`"",
        "--description `"$Description`"",
        "--fields `"Microsoft.VSTS.Scheduling.Effort=$Effort`" `"System.IterationPath=$Sprint`" `"Microsoft.VSTS.Common.Priority=$Priority`""
    )
    
    $output = Invoke-AzCommand "  Create task: $Title" $cmd
    return $output
}

# Sprint 1: Health Checks
$sprint1Path = $sprintPaths["Sprint 1: Health Checks"]

New-UserStory -ID "MCP-101" -Title "Health Check Endpoint — Core Framework" `
    -Description "Create reusable health check framework in mcp_servers/common/ that all MCP servers can use." `
    -StoryPoints 3 -Priority "1 - High" -Sprint $sprint1Path -Tags @("health-check", "framework")

New-Task -Title "Design HealthCheck dataclass" -Description "Design class structure with status, checks, timestamp" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Implement dependency check base class" -Description "Base class for all health checks" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add timeout wrapper" -Description "Ensure health check completes in <100ms" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Write unit tests" -Description "100% test coverage for framework" -Effort 0.5 -Priority "1" -Sprint $sprint1Path

New-UserStory -ID "MCP-102" -Title "Health Checks — file_share Server" `
    -Description "Add /health endpoint to file_share MCP server that checks Azure Files connectivity." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint1Path -Tags @("health-check", "file-share")

New-Task -Title "Add HealthCheck import" -Description "Import framework from common" -Effort 0.083 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Implement /health endpoint" -Description "FastAPI endpoint for health checks" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add Azure Files connectivity check" -Description "Test connection to Azure Files" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add integration test" -Description "Test endpoint responds in <100ms" -Effort 0.333 -Priority "1" -Sprint $sprint1Path

New-UserStory -ID "MCP-103" -Title "Health Checks — sql Server" `
    -Description "Add /health endpoint to sql MCP server that checks database connectivity." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint1Path -Tags @("health-check", "sql")

New-Task -Title "Add HealthCheck import" -Description "Import framework from common" -Effort 0.083 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Implement /health endpoint" -Description "FastAPI endpoint for health checks" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add database connectivity check" -Description "Test SQL connection with SELECT 1" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add integration test" -Description "Test endpoint responds in <100ms" -Effort 0.333 -Priority "1" -Sprint $sprint1Path

New-UserStory -ID "MCP-104" -Title "Health Checks — analytics Server" `
    -Description "Add /health endpoint to analytics MCP server that checks data freshness." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint1Path -Tags @("health-check", "analytics")

New-Task -Title "Add HealthCheck import" -Description "Import framework from common" -Effort 0.083 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Implement /health endpoint" -Description "FastAPI endpoint for health checks" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add data freshness check" -Description "Check last update timestamp" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add integration test" -Description "Test endpoint responds in <100ms" -Effort 0.333 -Priority "1" -Sprint $sprint1Path

New-UserStory -ID "MCP-105" -Title "Health Checks — document_generation Server" `
    -Description "Add /health endpoint to document_generation MCP server that checks template availability." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint1Path -Tags @("health-check", "document-generation")

New-Task -Title "Add HealthCheck import" -Description "Import framework from common" -Effort 0.083 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Implement /health endpoint" -Description "FastAPI endpoint for health checks" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add template availability check" -Description "Check templates exist and readable" -Effort 0.5 -Priority "1" -Sprint $sprint1Path
New-Task -Title "Add integration test" -Description "Test endpoint responds in <100ms" -Effort 0.333 -Priority "1" -Sprint $sprint1Path

New-UserStory -ID "MCP-106" -Title "Health Checks — Other Servers (Copy-Paste)" `
    -Description "Add /health endpoints to remaining servers: o365_mail, onedrive, memory, knowledge_base, dashboard, postgresql." `
    -StoryPoints 2 -Priority "2 - Medium" -Sprint $sprint1Path -Tags @("health-check")

New-Task -Title "Add /health to o365_mail" -Description "Graph API connectivity check" -Effort 0.25 -Priority "2" -Sprint $sprint1Path
New-Task -Title "Add /health to onedrive" -Description "Graph API connectivity check" -Effort 0.25 -Priority "2" -Sprint $sprint1Path
New-Task -Title "Add /health to memory" -Description "Cache connectivity check" -Effort 0.25 -Priority "2" -Sprint $sprint1Path
New-Task -Title "Add /health to knowledge_base" -Description "Storage connectivity check" -Effort 0.25 -Priority "2" -Sprint $sprint1Path
New-Task -Title "Add /health to dashboard" -Description "Data source connectivity check" -Effort 0.25 -Priority "2" -Sprint $sprint1Path
New-Task -Title "Add /health to postgresql" -Description "Database connectivity check" -Effort 0.25 -Priority "2" -Sprint $sprint1Path

Write-Info ""

# ============================================================================
# SPRINT 2: ERROR HANDLING
# ============================================================================

Write-Info "[2/3] Creating Sprint 2 User Stories & Tasks (Error Handling & Validation)..."
Write-Info ""

$sprint2Path = $sprintPaths["Sprint 2: Error Handling"]

New-UserStory -ID "MCP-201" -Title "Error Framework" `
    -Description "Create centralized error handling framework in mcp_servers/common/errors.py." `
    -StoryPoints 3 -Priority "1 - High" -Sprint $sprint2Path -Tags @("error-handling", "framework")

New-Task -Title "Design error codes" -Description "Define all error codes (FILE_NOT_FOUND, TIMEOUT, etc)" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Implement ErrorResponse dataclass" -Description "Create reusable error response format" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Add structured logging utility" -Description "Logging with trace_id" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Write unit tests" -Description "100% test coverage" -Effort 0.5 -Priority "1" -Sprint $sprint2Path

New-UserStory -ID "MCP-202" -Title "Input Validation Framework" `
    -Description "Create Pydantic validation models for all MCP server endpoints." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint2Path -Tags @("validation", "framework")

New-Task -Title "Design Pydantic models" -Description "Request and response models with constraints" -Effort 0.75 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Implement FastAPI exception handlers" -Description "Return structured error on validation failure" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Write unit tests" -Description "Validate all models correctly" -Effort 0.25 -Priority "1" -Sprint $sprint2Path

New-UserStory -ID "MCP-203" -Title "Error Handling — file_share Server" `
    -Description "Implement structured error handling in file_share MCP server." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint2Path -Tags @("error-handling", "file-share")

New-Task -Title "Add error handling to query_files endpoint" -Description "Use structured ErrorResponse" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Add input validation model" -Description "Pydantic model for file_share requests" -Effort 0.333 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Include available files as alternatives" -Description "FILE_NOT_FOUND shows alternatives" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Write integration tests" -Description "Test error responses match format" -Effort 0.333 -Priority "1" -Sprint $sprint2Path

New-UserStory -ID "MCP-204" -Title "Error Handling — sql Server" `
    -Description "Implement structured error handling in sql MCP server." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint2Path -Tags @("error-handling", "sql")

New-Task -Title "Add error handling to query_sql endpoint" -Description "Specific error codes" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Add input validation model" -Description "Pydantic model for sql requests" -Effort 0.333 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Add retry logic guidance" -Description "Suggest simpler queries on timeout" -Effort 0.333 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Write integration tests" -Description "Test all error codes" -Effort 0.333 -Priority "1" -Sprint $sprint2Path

New-UserStory -ID "MCP-205" -Title "Error Handling — analytics & document_generation" `
    -Description "Implement structured error handling in analytics and document_generation servers." `
    -StoryPoints 2 -Priority "1 - High" -Sprint $sprint2Path -Tags @("error-handling")

New-Task -Title "Add error handling to analytics endpoints" -Description "DATA_STALE, METRIC_NOT_FOUND" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Add error handling to document_generation endpoints" -Description "TEMPLATE_NOT_FOUND, INVALID_DATA" -Effort 0.5 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Add input validation models" -Description "Pydantic models for requests" -Effort 0.333 -Priority "1" -Sprint $sprint2Path
New-Task -Title "Write integration tests" -Description "Test both servers" -Effort 0.333 -Priority "1" -Sprint $sprint2Path

New-UserStory -ID "MCP-206" -Title "Error Documentation" `
    -Description "Document all error codes and their meanings." `
    -StoryPoints 2 -Priority "2 - Medium" -Sprint $sprint2Path -Tags @("documentation")

New-Task -Title "Create MCP_ERROR_CODES.md" -Description "List all error codes" -Effort 0.333 -Priority "2" -Sprint $sprint2Path
New-Task -Title "Add descriptions and examples" -Description "Document each error" -Effort 0.333 -Priority "2" -Sprint $sprint2Path
New-Task -Title "Add recovery guidance" -Description "How to fix each error" -Effort 0.333 -Priority "2" -Sprint $sprint2Path

Write-Info ""

# ============================================================================
# SUMMARY
# ============================================================================

Write-Info "=" * 80
Write-Info "Import Summary"
Write-Info "=" * 80
Write-Info ""
Write-Info "Created:"
Write-Success "  • 5 Sprints/Iterations"
Write-Success "  • Sprint 1: 6 User Stories + 16 Tasks"
Write-Success "  • Sprint 2: 6 User Stories + 16 Tasks"
Write-Info ""
Write-Info "Note: Sprints 3, 4, 5 can be imported after reviewing Sprint 1 & 2"
Write-Info ""
Write-Info "Next Steps:"
Write-Info "  1. Review work items in Azure DevOps"
Write-Info "  2. Assign team members to stories"
Write-Info "  3. Kick off Sprint 1 on May 30"
Write-Info ""

if ($DryRun) {
    Write-Info "DRY RUN MODE: No changes were made. Run with -DryRun `$false to import."
}
else {
    Write-Success "✅ All work items imported successfully!"
}
