# Import Work Items to Azure DevOps from CSV

## 📋 File: `azure-devops-workitems.csv`

Contains 27 work items across 5 sprints:
- **Sprint 1** (Health Checks): 6 tasks
- **Sprint 2** (Error Handling): 6 tasks
- **Sprint 3** (Caching): 5 tasks
- **Sprint 4** (Connection Pooling): 5 tasks
- **Sprint 5** (Documentation): 5 tasks

---

## 🚀 How to Import

### Option 1: Azure DevOps Web UI (Recommended)

1. Go to: https://dev.azure.com/siddonj/evieai

2. Click **Backlog** in the left menu

3. Click the **⋯ (More options)** button at the top

4. Select **Import work items**

5. Click **Browse** and select `azure-devops-workitems.csv`

6. Select **Map Fields**:
   - Ensure CSV headers match work item fields
   - Priority should map correctly
   - Iteration Path should resolve to sprints

7. Click **Import**

8. Verify all 27 items appear in the backlog

---

### Option 2: Azure CLI (PowerShell)

```powershell
cd C:\work\evieai

# Parse CSV and create each item
$csv = Import-Csv azure-devops-workitems.csv

foreach ($item in $csv) {
    $fields = @(
        "Microsoft.VSTS.Common.Priority=$($item.Priority)"
        "System.IterationPath=$($item.'Iteration Path')"
        "System.State=$($item.State)"
    )
    
    if ($item.Effort) {
        $fields += "Microsoft.VSTS.Scheduling.Effort=$($item.Effort)"
    }
    
    if ($item.'Story Points') {
        $fields += "Microsoft.VSTS.Scheduling.StoryPoints=$($item.'Story Points')"
    }
    
    az boards work-item create `
        --type "$($item.'Work Item Type')" `
        --title "$($item.Title)" `
        --fields $fields
}
```

---

## ✅ Verification

After import, verify in Azure DevOps:

1. Go to **Backlog** → **Sprint 1** should show 6 tasks
2. Each sprint should have its tasks listed
3. Effort estimates should be visible in the cards
4. Priority levels should be set (1 = High, 2 = Medium)

---

## 📝 Column Definitions

| Column | Example | Notes |
|--------|---------|-------|
| Work Item Type | Task | Use "Task" for all items (Feature/Story not available in project) |
| Title | Health Check Framework - Core | Clear, action-oriented title |
| Description | Create reusable health... | Context and acceptance criteria |
| Area Path | evieai | Project name |
| Iteration Path | evieai\Iteration\Sprint 1 | Full path to sprint |
| State | New | Initial state (New/Active/Resolved/Closed) |
| Priority | 1 or 2 | 1 = High, 2 = Medium |
| Effort | 2, 3 | Hours (for tasks) |
| Story Points | (empty for tasks) | Only used if converting to Story type |

---

## 🔧 Customization

To modify the CSV before import:

1. Open `azure-devops-workitems.csv` in Excel or VS Code
2. Update titles, descriptions, efforts as needed
3. Save as CSV (ensure comma-delimited, UTF-8 encoding)
4. Re-import

---

## ⚠️ Troubleshooting

| Error | Solution |
|-------|----------|
| "Invalid iteration path" | Ensure sprint names match exactly: "Sprint 1", "Sprint 2 - Error Handling", etc. |
| "Work item type not found" | Confirm "Task" type exists (it should in your project) |
| "Field not recognized" | Check that Priority, Effort columns are correctly named |
| "Import hangs" | Large files (50+ items) may take 5-10 minutes; be patient |

---

## 📊 After Import

Once all items are imported:

1. **Start Sprint 1**: Click "Sprint 1" → **Start sprint**
2. **Assign team members**: Click each task → **Assigned To**
3. **Set status**: Move tasks to **Active** or **In Progress**
4. **Track progress**: Use sprint board to visualize work

---

## 🎯 Next Steps

1. ✅ Import this CSV to Azure DevOps
2. Start Sprint 1 (May 30 – Jun 12)
3. Implement health check framework across 11 MCP servers
4. Close Sprint 1 tasks as work completes
5. Move to Sprint 2 (Error Handling) on Jun 13

