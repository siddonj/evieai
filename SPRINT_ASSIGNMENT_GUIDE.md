# Azure DevOps Sprint Assignment Guide

**Status**: ✅ All 27 work items successfully created (IDs 1-27)

## Quick Assignment (Manual - Recommended)

Visit: https://dev.azure.com/siddonj/evieai/_backlogs/backlog

### Bulk Move by Drag-Drop:

**Sprint 1 (IDs 1-6):**
```
Health Check Framework - Core
Health Checks - file_share
Health Checks - sql
Health Checks - analytics
Health Checks - document_generation
Health Checks - Other Servers
```

1. Click "Backlog" tab
2. Select all 6 items (Ctrl+Click)
3. Drag to "Sprint 1" in left sidebar
4. Confirm

**Sprint 2 (IDs 7-12):**
```
Error Framework
Input Validation Framework
Error Handling - file_share
Error Handling - sql
Error Handling - analytics and document_generation
Error Documentation
```

**Sprint 3 (IDs 13-17):**
```
Query Caching Framework
Caching - file_share
Caching - analytics
Caching - knowledge_base
Caching - Metrics and Monitoring
```

**Sprint 4 (IDs 18-22):**
```
SQL Connection Pooling
Graph API Pooling
Structured Logging
Application Insights Integration
Performance Testing
```

**Sprint 5 (IDs 23-27):**
```
API Documentation
Docstrings and Code Comments
Best Practices Guide
Troubleshooting Guide
Examples and Tutorials
```

## Command-Line Assignment

Once Azure DevOps CLI fixes its iteration path handling, use:

```powershell
$sprintPaths = @{
  "1-6" = "\evieai\Iteration\Sprint 1"
  "7-12" = "\evieai\Iteration\Sprint 2 - Error Handling"
  "13-17" = "\evieai\Iteration\Sprint 3 - Caching"
  "18-22" = "\evieai\Iteration\Sprint 4 - Connection Pooling"
  "23-27" = "\evieai\Iteration\Sprint 5 - Documentation"
}
```

## View Work Items

List all items:
```bash
az boards query --wiql "SELECT [System.Id], [System.Title], [System.IterationPath] FROM workitems WHERE [System.TeamProject] = 'evieai' ORDER BY [System.Id]"
```

## Next Steps

1. ✅ Create 27 work items
2. 🔄 **Assign to sprints** (manual UI method recommended)
3. 📋 Start Sprint 1 in Azure DevOps UI
4. 👥 Assign team members to tasks
5. 🚀 Begin Sprint 1 implementation (May 30, 2026)

## Sprint Dates

- **Sprint 1**: May 30 - Jun 12 (Health Checks)
- **Sprint 2**: Jun 13 - Jun 26 (Error Handling)
- **Sprint 3**: Jun 27 - Jul 10 (Caching)
- **Sprint 4**: Jul 11 - Jul 24 (Connection Pooling)
- **Sprint 5**: Jul 25 - Aug 7 (Documentation)

---

**Created**: 2026-05-30
**Status**: Ready for sprint assignment
