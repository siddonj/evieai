# Create remaining 4 sprints (Sprint 1 already exists)
$sprints = @(
    @{ name = "Sprint 2 - Error Handling"; start = "2026-06-13"; end = "2026-06-26" }
    @{ name = "Sprint 3 - Caching"; start = "2026-06-27"; end = "2026-07-10" }
    @{ name = "Sprint 4 - Connection Pooling"; start = "2026-07-11"; end = "2026-07-24" }
    @{ name = "Sprint 5 - Documentation"; start = "2026-07-25"; end = "2026-08-07" }
)

foreach ($sprint in $sprints) {
    Write-Host "Creating $($sprint.name)..." -ForegroundColor Cyan
    $result = az boards iteration project create --name $sprint.name --start-date $sprint.start --finish-date $sprint.end 2>&1
    if ($result -match "error" -or $result -match "Error") {
        Write-Host "ERROR: $result" -ForegroundColor Red
    } else {
        Write-Host "✅ Created" -ForegroundColor Green
    }
}

Write-Host "`n✅ All sprints created. View at: https://dev.azure.com/siddonj/evieai/_backlogs/backlog" -ForegroundColor Green
