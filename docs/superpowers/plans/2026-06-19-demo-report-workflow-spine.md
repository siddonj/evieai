# Demo Report Workflow Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a formal export-package step, a presentation-style report viewer, and seeded demo playbook cards to the governed document workflow so the demo shows a single end-to-end orchestrator story.

**Architecture:** Extend the existing `document_actions` record and action ledger instead of creating a parallel reporting system. Backend changes add export-package persistence and API routes; frontend changes add a report viewer route, export controls, and scenario playbook entry points that all continue to flow through the existing chat and document workflow surfaces.

**Tech Stack:** FastAPI, sqlite-backed stores, React + Vite + TypeScript, pytest smoke/unit tests, existing document artifact/blob helpers.

---

## File Structure

- Modify: `orchestrator/app/document_actions_store.py`
  Responsibility: persist export-package metadata on document workflow records and expose idempotent updates.
- Modify: `orchestrator/app/document_actions_service.py`
  Responsibility: create and execute export-package actions, derive export artifacts, and return viewer-ready workflow data.
- Modify: `orchestrator/app/document_actions_router.py`
  Responsibility: expose guarded export-package and viewer fetch endpoints using the existing auth model.
- Modify: `orchestrator/openapi.yaml`
  Responsibility: document the new workflow endpoints in the checked-in API spec.
- Modify: `tests/unit/test_document_actions_service.py`
  Responsibility: cover export-package state transitions, idempotency, and persisted artifacts.
- Modify: `tests/smoke/test_orchestrator.py`
  Responsibility: cover the draft → approve → finalize → export happy path and schema regression checks.
- Modify: `web_ui/src/Cards.tsx`
  Responsibility: extend shared document action types with export-package and viewer metadata.
- Modify: `web_ui/src/DocumentWorkflowPanel.tsx`
  Responsibility: add `Export package` and `View report` affordances plus export status rendering.
- Modify: `web_ui/src/App.tsx`
  Responsibility: add playbook cards, report-view route, and navigation wiring.
- Modify: `web_ui/src/styles.css`
  Responsibility: style playbook cards and the presentation-oriented report viewer shell using existing visual primitives.

### Task 1: Persist export-package metadata in document workflows

**Files:**
- Modify: `orchestrator/app/document_actions_store.py`
- Test: `tests/unit/test_document_actions_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_service_records_export_package_metadata(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    actions_store = ActionsStore(str(tmp_path / "actions.db"))
    service = DocumentActionsService(store=store, artifact_root=tmp_path / "document_artifacts", actions_store=actions_store)

    draft = service.create_draft(
        user_id="alice",
        work_packet_id="wp-export-1",
        document_type="portfolio_performance_review",
        title="Portfolio Performance Review",
        source_summary="Performance summary",
    )
    store.mark_approved(
        document_action_id=draft["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Portfolio",
        output_formats=["pdf", "docx"],
    )
    service.finalize(document_action_id=draft["id"])

    exported = service.export_package(document_action_id=draft["id"])

    assert exported["status"] == "completed"
    assert exported["document_action"]["export_package"]["status"] == "completed"
    assert len(exported["document_action"]["export_package"]["artifacts"]) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3.11 -m pytest tests/unit/test_document_actions_service.py::test_service_records_export_package_metadata -v`
Expected: FAIL because `export_package` data and `export_package()` do not exist yet.

- [ ] **Step 3: Write minimal persistence implementation**

```python
# document_actions table additions
export_package_json TEXT,
exported_at TEXT,

def mark_export_package(
    self,
    *,
    document_action_id: int,
    export_package: dict[str, Any],
) -> dict[str, Any]:
    now = _utc_now()
    with self._connect() as conn:
        conn.execute(
            """
            UPDATE document_actions
            SET export_package_json = ?,
                exported_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (_canonical_json(export_package), now, now, document_action_id),
        )
        row = conn.execute(
            "SELECT * FROM document_actions WHERE id = ?",
            (document_action_id,),
        ).fetchone()
    return self._row_to_dict(row)
```

- [ ] **Step 4: Normalize the new stored fields**

```python
def _row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any]:
    ...
    data["export_package"] = json.loads(data.pop("export_package_json") or "null")
    return data
```

- [ ] **Step 5: Run the targeted test to verify it passes**

Run: `python3.11 -m pytest tests/unit/test_document_actions_service.py::test_service_records_export_package_metadata -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add orchestrator/app/document_actions_store.py tests/unit/test_document_actions_service.py
git commit -m "feat: persist document export packages"
```

### Task 2: Add export-package service behavior and API endpoint

**Files:**
- Modify: `orchestrator/app/document_actions_service.py`
- Modify: `orchestrator/app/document_actions_router.py`
- Modify: `orchestrator/openapi.yaml`
- Test: `tests/unit/test_document_actions_service.py`
- Test: `tests/smoke/test_orchestrator.py`

- [ ] **Step 1: Write the failing backend tests**

```python
def test_service_blocks_export_before_finalization(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)
    draft = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="portfolio_performance_review",
        title="Portfolio Performance Review",
        source_summary="Summary",
    )

    result = service.export_package(document_action_id=draft["id"])

    assert result["status"] == "blocked"
    assert result["reason"] == "finalization_required"
```

```python
@pytest.mark.asyncio
async def test_document_workflow_export_package_endpoint():
    async with httpx.AsyncClient(timeout=20) as client:
        ...
        exported = await client.post(f"{_base_url()}/document-actions/{draft_body['id']}/export-package")
        assert exported.status_code == 200
        body = exported.json()
        assert body["status"] == "completed"
        assert len(body["artifacts"]) == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3.11 -m pytest tests/unit/test_document_actions_service.py::test_service_blocks_export_before_finalization -v`
Expected: FAIL because `export_package()` is missing.

Run: `python3.11 -m pytest tests/smoke/test_orchestrator.py::test_document_workflow_export_package_endpoint -v`
Expected: FAIL because the route does not exist.

- [ ] **Step 3: Add the service method and export action creation**

```python
def export_package(self, *, document_action_id: int) -> dict[str, Any]:
    record = self.store.get(document_action_id)
    if record["status"] != "executed":
        return {
            "status": "blocked",
            "reason": "finalization_required",
            "document_action_id": document_action_id,
        }
    if record.get("export_package", {}).get("status") == "completed":
        return {
            "status": "completed",
            "document_action": record,
            "artifacts": record["export_package"]["artifacts"],
        }

    export_artifacts = [
        self._write_artifact(record=record, output_format=output_format)
        for output_format in ["pdf", "docx", "xlsx"]
    ]
    export_action = self._create_export_action(record=record, artifacts=export_artifacts)
    persisted = self.store.mark_export_package(
        document_action_id=document_action_id,
        export_package=export_action | {"artifacts": export_artifacts},
    )
    return {
        "status": persisted["export_package"]["status"],
        "document_action": persisted,
        "artifacts": persisted["export_package"]["artifacts"],
    }
```

- [ ] **Step 4: Expose the router endpoint**

```python
@router.post("/{document_action_id}/export-package")
def export_package(
    document_action_id: int,
    actor: Annotated[dict[str, Any] | None, Depends(require_auth_optional)] = None,
) -> dict[str, Any]:
    record = get_document_actions_store().get(document_action_id)
    _authorize_document_access(actor, record)
    return DOCUMENT_ACTIONS_SERVICE.export_package(document_action_id=document_action_id)
```

- [ ] **Step 5: Update the checked-in schema**

Run: update `orchestrator/openapi.yaml` to include `/document-actions/{document_action_id}/export-package` and its response shape.

- [ ] **Step 6: Run targeted tests to verify green**

Run: `python3.11 -m pytest tests/unit/test_document_actions_service.py -v`
Expected: PASS with export-package coverage included.

Run: `python3.11 -m pytest tests/smoke/test_orchestrator.py::test_document_workflow_export_package_endpoint -v`
Expected: PASS when the local orchestrator test environment is available.

- [ ] **Step 7: Commit**

```bash
git add orchestrator/app/document_actions_service.py orchestrator/app/document_actions_router.py orchestrator/openapi.yaml tests/unit/test_document_actions_service.py tests/smoke/test_orchestrator.py
git commit -m "feat: add document workflow export packages"
```

### Task 3: Add report-view navigation and workflow actions in the UI

**Files:**
- Modify: `web_ui/src/Cards.tsx`
- Modify: `web_ui/src/DocumentWorkflowPanel.tsx`
- Modify: `web_ui/src/App.tsx`
- Modify: `web_ui/src/styles.css`

- [ ] **Step 1: Write the failing UI state contract**

```ts
export type DocumentAction = {
  ...
  export_package?: {
    status?: 'queued' | 'running' | 'completed' | 'failed'
    action_id?: string
    created_at?: string
    updated_at?: string
    artifacts?: Array<{
      format?: string
      file_name?: string
      storage_ref?: string
      blob_url?: string
      size_bytes?: number
    }>
    error?: string
  }
}
```

The initial build should fail because components still assume only finalization artifacts exist.

- [ ] **Step 2: Run build to verify the current UI does not support the new state**

Run: `cd web_ui && npm run build`
Expected: FAIL after introducing the new type contract and references to missing UI branches.

- [ ] **Step 3: Add workflow actions and report route**

```tsx
const canExportPackage = action.id > 0 && action.status === 'executed'

<button
  className="status-btn"
  onClick={(event) => {
    event.stopPropagation()
    void handleExportPackage()
  }}
  disabled={!canExportPackage || busy !== null}
>
  {busy === 'export' ? 'Exporting…' : 'Export package'}
</button>

<button className="status-btn" onClick={() => onViewReport(action.id)}>
  View report
</button>
```

```tsx
if (view === 'report' && selectedDocumentId) {
  return <ReportViewer documentActionId={selectedDocumentId} authHeader={authHeader} onBack={() => setView('documents')} />
}
```

- [ ] **Step 4: Add the presentation-style report viewer shell**

```tsx
function ReportViewer({ documentActionId, authHeader, onBack }: ReportViewerProps) {
  const [document, setDocument] = useState<DocumentAction | null>(null)
  ...
  return (
    <div className="page report-viewer-page">
      <header className="hero">
        <p className="eyebrow">Presentation View</p>
        <h1>{document?.title}</h1>
        <p className="subtitle">{document?.document_type?.split('_').join(' ')}</p>
      </header>
      <div className="dashboard-shell">
        <div className="kpi-grid">{/* status, exports, handoff */}</div>
        <section className="dashboard-panel">{/* narrative body */}</section>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Style the new surfaces**

Run: extend `web_ui/src/styles.css` with focused styles for `.playbook-grid`, `.playbook-card`, `.report-viewer-page`, `.report-stat`, and any new timeline/status elements while preserving the existing shell.

- [ ] **Step 6: Run the frontend build to verify it passes**

Run: `cd web_ui && npm run build`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web_ui/src/Cards.tsx web_ui/src/DocumentWorkflowPanel.tsx web_ui/src/App.tsx web_ui/src/styles.css
git commit -m "feat: add report viewer and export actions"
```

### Task 4: Add playbook cards for the two seeded demo scenarios

**Files:**
- Modify: `web_ui/src/App.tsx`
- Modify: `web_ui/src/styles.css`

- [ ] **Step 1: Write the failing playbook config**

```ts
const PLAYBOOKS = [
  {
    id: 'portfolio-performance-review',
    title: 'Portfolio performance review',
    question: 'Generate a portfolio performance review with NOI, occupancy, rent trends, and export-ready summary.',
    outputs: ['Governed draft', 'Presentation view', 'PDF/DOCX/XLSX package'],
  },
  {
    id: 'board-packet',
    title: 'Board packet',
    question: 'Prepare a board packet summarizing portfolio health, key risks, and next actions.',
    outputs: ['Board-ready narrative', 'Governed approval flow', 'Formal export package'],
  },
]
```

The build should initially fail until the rendering and click handling are wired.

- [ ] **Step 2: Run build to verify the new playbook references are unresolved**

Run: `cd web_ui && npm run build`
Expected: FAIL if the config is added before the render path and click handler.

- [ ] **Step 3: Render the playbook cards and connect them to chat**

```tsx
<div className="playbook-grid">
  {PLAYBOOKS.map((playbook) => (
    <button
      key={playbook.id}
      className="playbook-card"
      onClick={() => sendMessage(playbook.question)}
      disabled={loading}
    >
      <span className="eyebrow">{playbook.id.replaceAll('-', ' ')}</span>
      <strong>{playbook.title}</strong>
      <p>{playbook.question}</p>
    </button>
  ))}
</div>
```

- [ ] **Step 4: Verify the frontend build passes**

Run: `cd web_ui && npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web_ui/src/App.tsx web_ui/src/styles.css
git commit -m "feat: add demo workflow playbooks"
```

### Task 5: Run end-to-end verification and polish integration gaps

**Files:**
- Modify: any of the above only if verification exposes concrete defects
- Test: `tests/unit/test_document_actions_service.py`
- Test: `tests/smoke/test_orchestrator.py`

- [ ] **Step 1: Run backend unit verification**

Run: `python3.11 -m pytest tests/unit/test_document_actions_service.py -v`
Expected: PASS

- [ ] **Step 2: Run backend smoke verification for the workflow story**

Run: `python3.11 -m pytest tests/smoke/test_orchestrator.py -v`
Expected: PASS when the orchestrator dependencies are available locally. If the environment is missing `fastapi` or related packages, record that constraint explicitly.

- [ ] **Step 3: Run frontend verification**

Run: `cd web_ui && npm run build`
Expected: PASS

- [ ] **Step 4: Inspect the final diff for scope drift**

Run: `git diff --stat HEAD~3..HEAD`
Expected: changes confined to document workflow backend, smoke/unit tests, and the report/playbook UI surfaces.

- [ ] **Step 5: Commit any final verification fixes**

```bash
git add orchestrator/app/document_actions_store.py orchestrator/app/document_actions_service.py orchestrator/app/document_actions_router.py orchestrator/openapi.yaml tests/unit/test_document_actions_service.py tests/smoke/test_orchestrator.py web_ui/src/Cards.tsx web_ui/src/DocumentWorkflowPanel.tsx web_ui/src/App.tsx web_ui/src/styles.css
git commit -m "test: verify demo report workflow spine"
```
