# Manual Azure DevOps Sprint Import Guide

> Since the automated CLI import encountered project configuration issues, here's the manual approach to create sprints and work items.

---

## ✅ What Was Successfully Created

**5 Sprints (Iterations)** — All created successfully:
- ✅ Sprint 1: Health Checks (May 30 – Jun 12)
- ✅ Sprint 2: Error Handling (Jun 13 – Jun 26)  
- ✅ Sprint 3: Caching (Jun 27 – Jul 10)
- ✅ Sprint 4: Connection Pooling (Jul 11 – Jul 24)
- ✅ Sprint 5: Documentation (Jul 25 – Aug 7)

View at: https://dev.azure.com/siddonj/evieai/_backlogs/backlog

---

## ⚠️ Work Items Issue

The work item creation failed because:
1. **"User Story" type not found** → Your project may use "Feature" or "Epic" instead
2. **Invalid iteration path** → Permissions or path format issue

---

## 🔧 Manual Sprint 1 Import (5 minutes)

Go to: https://dev.azure.com/siddonj/evieai/_backlogs/backlog

### Create Story: MCP-101 (Health Check Framework)

1. Click **"+ New Work Item"** in backlog
2. **Type**: Feature (or Story)
3. **Title**: Health Check Endpoint - Core Framework
4. **Description**: Create reusable health check framework in `mcp_servers/common/` that all MCP servers can use.
5. **Sprint**: Sprint 1: Health Checks
6. **Story Points**: 3
7. **Priority**: 1 - High
8. Click **Save**

#### Add Tasks to MCP-101:
9. In work item details, click **Add link** → **Child** → **Task**
   - **Task 1**: Design HealthCheck dataclass (Effort: 0.5h)
   - **Task 2**: Implement dependency check base class (Effort: 0.5h)
   - **Task 3**: Add timeout wrapper (Effort: 0.5h)
   - **Task 4**: Write unit tests (Effort: 0.5h)

### Create Story: MCP-102 (Health Checks - file_share)

1. Click **"+ New Work Item"**
2. **Type**: Feature
3. **Title**: Health Checks - file_share Server
4. **Description**: Add `/health` endpoint to file_share MCP server that checks Azure Files connectivity.
5. **Sprint**: Sprint 1: Health Checks
6. **Story Points**: 2
7. **Priority**: 1 - High

#### Add Tasks:
- **Task**: Implement health endpoint for file_share (Effort: 1h)
- **Task**: Write integration test for file_share health (Effort: 1h)

### Create Story: MCP-103 (Health Checks - sql)

Same structure as MCP-102:
- **Title**: Health Checks - sql Server
- **Story Points**: 2
- **Tasks**: 
  - Implement health endpoint for sql (1h)
  - Write integration test for sql health (1h)

### Create Story: MCP-104 (Health Checks - analytics)

Same structure:
- **Title**: Health Checks - analytics Server
- **Story Points**: 2
- **Tasks**:
  - Implement health endpoint for analytics (1h)
  - Write integration test for analytics health (1h)

### Create Story: MCP-105 (Health Checks - document_generation)

Same structure:
- **Title**: Health Checks - document_generation Server
- **Story Points**: 2
- **Tasks**:
  - Implement health endpoint for document_generation (1h)
  - Write integration test for document_generation health (1h)

### Create Story: MCP-106 (Health Checks - Other Servers)

- **Title**: Health Checks - Other Servers
- **Description**: Add `/health` endpoints to remaining servers
- **Story Points**: 2
- **Priority**: 2 - Medium
- **Tasks**:
  - Add health to o365_mail, onedrive, memory (1.5h)
  - Add health to knowledge_base, dashboard, postgresql (1.5h)

---

## Sprint 1 Summary

**Total for Sprint 1**:
- 6 User Stories
- 13 Story Points
- 12 Tasks
- Effort: ~8 hours

---

## 📋 Repeat for Sprint 2

Use the same process for Sprint 2 (Error Handling):

### Sprint 2 Stories:
- **MCP-201**: Error Framework (3 points, 4 tasks)
- **MCP-202**: Input Validation Framework (2 points, 2 tasks)
- **MCP-203**: Error Handling - file_share (2 points, 1 task)
- **MCP-204**: Error Handling - sql (2 points, 1 task)
- **MCP-205**: Error Handling - analytics & document_generation (2 points, 1 task)
- **MCP-206**: Error Documentation (2 points, 1 task)

---

## 💡 Quick Tips

- **Bulk edit**: Select multiple items and update properties at once
- **Copy**: Right-click a story → **Copy work item** → paste and modify
- **Velocity**: Track story points completed per sprint to forecast future capacity
- **Sprint dates**: Already set in the 5 sprints (May 30 – Aug 7)

---

## 🎯 Once Import is Complete

1. **Assign team members** to stories (click story → **Assigned To**)
2. **Start Sprint 1** (click sprint header → **Start sprint**)
3. **Kanban board**: View board at https://dev.azure.com/siddonj/evieai/_boards/board
4. **Track progress**: Move cards across columns as work progresses

---

## Alternative: CSV Import

If you prefer bulk import via CSV:

1. Export template: **Backlog** → **... menu** → **Export to CSV**
2. Fill in CSV with stories and tasks
3. **Import to CSV** → **Select file** → **Map fields** → **Import**

---

## Need Help?

- **Azure DevOps docs**: https://docs.microsoft.com/azure/devops/boards/
- **User Story format**: https://docs.microsoft.com/azure/devops/boards/work-items/user-stories
- **Effort estimation**: Use Fibonacci scale (1, 2, 3, 5, 8, 13)

