#!/usr/bin/env pwsh
# Simple script to create Azure DevOps sprints and work items
# Usage: .\import-sprints-simple.ps1 -Execute $true

param([bool]$Execute = $false)

$DryRun = -not $Execute

function LogInfo {
    param([string]$msg)
    Write-Host $msg -ForegroundColor Cyan
}

function LogOK {
    param([string]$msg)
    Write-Host "  [OK] $msg" -ForegroundColor Green
}

function LogError {
    param([string]$msg)
    Write-Host "  [ERROR] $msg" -ForegroundColor Red
}

function RunCmd {
    param([string]$title, [string]$cmd)
    
    LogInfo $title
    
    if ($DryRun) {
        Write-Host "  COMMAND: $cmd" -ForegroundColor Yellow
        return
    }
    
    try {
        Invoke-Expression $cmd
        LogOK "Done"
    }
    catch {
        LogError $_
    }
}

LogInfo "======== Azure DevOps Sprint Import ========"
LogInfo ""

if ($DryRun) {
    LogInfo "DRY RUN MODE - no changes will be made"
    LogInfo "Run with -Execute `$true to create items"
    LogInfo ""
}

# ============================================================================
# Create Sprints (Iterations)
# ============================================================================

LogInfo "[1] Creating Sprints"
LogInfo ""

$sprintDates = @(
    @{name = "Sprint 1: Health Checks"; start = "2026-05-30"; end = "2026-06-12"}
    @{name = "Sprint 2: Error Handling"; start = "2026-06-13"; end = "2026-06-26"}
    @{name = "Sprint 3: Caching"; start = "2026-06-27"; end = "2026-07-10"}
    @{name = "Sprint 4: Connection Pooling"; start = "2026-07-11"; end = "2026-07-24"}
    @{name = "Sprint 5: Documentation"; start = "2026-07-25"; end = "2026-08-07"}
)

foreach ($sprint in $sprintDates) {
    $cmd = "az boards iteration project create --name `"$($sprint.name)`" --start-date $($sprint.start) --end-date $($sprint.end)"
    RunCmd "Create sprint: $($sprint.name)" $cmd
}

LogInfo ""

# ============================================================================
# Create User Stories and Tasks - Sprint 1
# ============================================================================

LogInfo "[2] Creating Sprint 1 Work Items"
LogInfo ""

$sprint1 = "Sprint 1: Health Checks"

# Story MCP-101
RunCmd "Story MCP-101: Health Check Framework" `
  "az boards work-item create --type 'User Story' --title 'Health Check Endpoint - Core Framework' --description 'Create reusable health check framework' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=3' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

# Tasks for MCP-101
RunCmd "Task: Design HealthCheck dataclass" `
  "az boards work-item create --type Task --title 'Design HealthCheck dataclass' --fields 'Microsoft.VSTS.Scheduling.Effort=0.5' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Implement dependency check base class" `
  "az boards work-item create --type Task --title 'Implement dependency check base class' --fields 'Microsoft.VSTS.Scheduling.Effort=0.5' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add timeout wrapper" `
  "az boards work-item create --type Task --title 'Add timeout wrapper' --fields 'Microsoft.VSTS.Scheduling.Effort=0.5' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Write unit tests" `
  "az boards work-item create --type Task --title 'Write unit tests for framework' --fields 'Microsoft.VSTS.Scheduling.Effort=0.5' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-102
RunCmd "Story MCP-102: Health Checks - file_share" `
  "az boards work-item create --type 'User Story' --title 'Health Checks - file_share Server' --description 'Add health endpoint to file_share' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add health endpoint to file_share" `
  "az boards work-item create --type Task --title 'Implement health endpoint for file_share' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Test file_share health check" `
  "az boards work-item create --type Task --title 'Write integration test for file_share health' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-103
RunCmd "Story MCP-103: Health Checks - sql" `
  "az boards work-item create --type 'User Story' --title 'Health Checks - sql Server' --description 'Add health endpoint to sql' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add health endpoint to sql" `
  "az boards work-item create --type Task --title 'Implement health endpoint for sql' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Test sql health check" `
  "az boards work-item create --type Task --title 'Write integration test for sql health' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-104
RunCmd "Story MCP-104: Health Checks - analytics" `
  "az boards work-item create --type 'User Story' --title 'Health Checks - analytics Server' --description 'Add health endpoint to analytics' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add health endpoint to analytics" `
  "az boards work-item create --type Task --title 'Implement health endpoint for analytics' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Test analytics health check" `
  "az boards work-item create --type Task --title 'Write integration test for analytics health' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-105
RunCmd "Story MCP-105: Health Checks - document_generation" `
  "az boards work-item create --type 'User Story' --title 'Health Checks - document_generation Server' --description 'Add health endpoint to document_generation' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add health endpoint to document_generation" `
  "az boards work-item create --type Task --title 'Implement health endpoint for document_generation' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Test document_generation health check" `
  "az boards work-item create --type Task --title 'Write integration test for document_generation health' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-106
RunCmd "Story MCP-106: Health Checks - Other Servers" `
  "az boards work-item create --type 'User Story' --title 'Health Checks - Other Servers' --description 'Add health endpoints to remaining servers' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=2'"

RunCmd "Task: Add health to o365_mail, onedrive, memory" `
  "az boards work-item create --type Task --title 'Add health endpoints to o365_mail, onedrive, memory' --fields 'Microsoft.VSTS.Scheduling.Effort=1.5' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=2'"

RunCmd "Task: Add health to knowledge_base, dashboard, postgresql" `
  "az boards work-item create --type Task --title 'Add health endpoints to knowledge_base, dashboard, postgresql' --fields 'Microsoft.VSTS.Scheduling.Effort=1.5' 'System.IterationPath=evieai\$sprint1' 'Microsoft.VSTS.Common.Priority=2'"

LogInfo ""

# ============================================================================
# Create Sprint 2 Work Items
# ============================================================================

LogInfo "[3] Creating Sprint 2 Work Items"
LogInfo ""

$sprint2 = "Sprint 2: Error Handling"

# Story MCP-201
RunCmd "Story MCP-201: Error Framework" `
  "az boards work-item create --type 'User Story' --title 'Error Framework' --description 'Create centralized error handling' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=3' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Design error codes" `
  "az boards work-item create --type Task --title 'Design error codes and structure' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Implement ErrorResponse dataclass" `
  "az boards work-item create --type Task --title 'Implement ErrorResponse dataclass' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add structured logging" `
  "az boards work-item create --type Task --title 'Add structured logging with trace_id' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-202
RunCmd "Story MCP-202: Input Validation Framework" `
  "az boards work-item create --type 'User Story' --title 'Input Validation Framework' --description 'Create Pydantic validation models' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Design Pydantic models" `
  "az boards work-item create --type Task --title 'Design Pydantic models for validation' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Implement exception handlers" `
  "az boards work-item create --type Task --title 'Implement FastAPI exception handlers' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-203
RunCmd "Story MCP-203: Error Handling - file_share" `
  "az boards work-item create --type 'User Story' --title 'Error Handling - file_share Server' --description 'Implement error handling for file_share' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add structured errors to file_share" `
  "az boards work-item create --type Task --title 'Add structured error handling to file_share' --fields 'Microsoft.VSTS.Scheduling.Effort=1.5' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-204
RunCmd "Story MCP-204: Error Handling - sql" `
  "az boards work-item create --type 'User Story' --title 'Error Handling - sql Server' --description 'Implement error handling for sql' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add structured errors to sql" `
  "az boards work-item create --type Task --title 'Add structured error handling to sql' --fields 'Microsoft.VSTS.Scheduling.Effort=1.5' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-205
RunCmd "Story MCP-205: Error Handling - analytics and document_generation" `
  "az boards work-item create --type 'User Story' --title 'Error Handling - analytics and document_generation' --description 'Implement error handling' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

RunCmd "Task: Add errors to analytics and document_generation" `
  "az boards work-item create --type Task --title 'Add structured error handling to analytics and document_generation' --fields 'Microsoft.VSTS.Scheduling.Effort=1.5' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=1'"

# Story MCP-206
RunCmd "Story MCP-206: Error Documentation" `
  "az boards work-item create --type 'User Story' --title 'Error Documentation' --description 'Document all error codes' --fields 'Microsoft.VSTS.Scheduling.StoryPoints=2' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=2'"

RunCmd "Task: Create MCP_ERROR_CODES.md" `
  "az boards work-item create --type Task --title 'Create MCP_ERROR_CODES.md documentation' --fields 'Microsoft.VSTS.Scheduling.Effort=1' 'System.IterationPath=evieai\$sprint2' 'Microsoft.VSTS.Common.Priority=2'"

LogInfo ""
LogInfo "======== Summary ========"
LogInfo ""
LogInfo "Created:"
LogInfo "  - 5 Sprints (iterations)"
LogInfo "  - Sprint 1: 6 User Stories + 12 Tasks"
LogInfo "  - Sprint 2: 6 User Stories + 8 Tasks"
LogInfo ""
LogInfo "View in Azure DevOps at:"
LogInfo "  https://dev.azure.com/siddonj/evieai/_backlogs/backlog"
LogInfo ""

if ($DryRun) {
    LogInfo "DRY RUN: Run with -Execute `$true to create items"
}
else {
    LogInfo "All items created successfully!"
}
