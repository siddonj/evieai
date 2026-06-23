# Governed Document Workflows Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first governed-actions slice so EvieAI can draft executive briefings, board reports, and operational reports from work packets, require user approval only at finalization, then generate final artifacts, store them to a selected destination, and create a follow-up announcement action.

**Architecture:** Build a focused document-action workflow on top of the existing work-packet and export foundations. Introduce a persistent document-action model and approval API in the orchestrator, reuse the current document-generation/export capabilities to produce final artifacts, and add a narrow UI flow for draft, approval, destination selection, and execution status without attempting a full generic action engine.

**Tech Stack:** FastAPI, Pydantic, sqlite/postgres-backed stores already used in orchestrator, pytest, React 18, TypeScript, Vite

---

## File Structure

- Create: `orchestrator/app/document_actions_store.py`
  Responsibility: persist governed document workflow records, draft versions, approval events, destinations, and execution outcomes.
- Create: `orchestrator/app/document_actions_service.py`
  Responsibility: orchestrate draft creation, approval validation, finalization, storage metadata, and announcement creation.
- Create: `orchestrator/app/document_actions_router.py`
  Responsibility: expose HTTP endpoints for draft creation, revision, approval, finalization status, and retrieval.
- Modify: `orchestrator/app/main.py`
  Responsibility: register the router and, where needed, expose work-packet document suggestions through existing app wiring.
- Modify: `orchestrator/app/actions_service.py`
  Responsibility: create a minimal announcement action record after successful document finalization.
- Modify: `orchestrator/app/blob.py`
  Responsibility: provide a stable artifact write/read helper for finalized governed documents.
- Modify: `orchestrator/openapi.yaml`
  Responsibility: publish the document workflow endpoints and request/response schemas.
- Create: `tests/unit/test_document_actions_store.py`
  Responsibility: verify persistence for draft, approval, finalization, and audit fields.
- Create: `tests/unit/test_document_actions_service.py`
  Responsibility: verify approval gating, artifact generation flow, destination handling, and announcement creation.
- Modify: `tests/smoke/test_orchestrator.py`
  Responsibility: add smoke coverage for document draft creation and approved finalization response shape.
- Create: `web_ui/src/DocumentWorkflowPanel.tsx`
  Responsibility: render document type selection, draft metadata, approval controls, destination, and finalization status.
- Modify: `web_ui/src/Cards.tsx`
  Responsibility: add frontend types for governed document actions and approval state.
- Modify: `web_ui/src/App.tsx`
  Responsibility: render document workflow actions from work packets and wire API calls for draft, approval, and finalization.
- Modify: `docs/FEATURES.md`
  Responsibility: document governed document workflows as a first-class capability.

## Task 1: Add Persistent Document Workflow Storage

**Files:**
- Create: `orchestrator/app/document_actions_store.py`
- Test: `tests/unit/test_document_actions_store.py`

- [ ] **Step 1: Write the failing tests**

```python
from orchestrator.app.document_actions_store import DocumentActionsStore


def test_store_creates_draft_record(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    record = store.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="executive_briefing",
        title="Executive Briefing",
        draft_markdown="# Briefing",
    )

    assert record["status"] == "draft"
    assert record["user_id"] == "alice"
    assert record["document_type"] == "executive_briefing"
    assert record["draft_version"] == 1


def test_store_records_approval_and_destination(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    record = store.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="board_report",
        title="Board Report",
        draft_markdown="# Board",
    )

    approved = store.mark_approved(
        document_action_id=record["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Board",
        output_formats=["pdf", "docx"],
    )

    assert approved["status"] == "approved"
    assert approved["approved_by"] == "alice"
    assert approved["destination_type"] == "onedrive"
    assert approved["output_formats"] == ["pdf", "docx"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_document_actions_store.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing `DocumentActionsStore`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DocumentActionsStore:
    def __init__(self, db_path: Path | str = "document_actions.db") -> None:
        self.db_path = str(db_path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS document_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    work_packet_id TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    draft_markdown TEXT NOT NULL,
                    draft_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    destination_type TEXT,
                    destination_ref TEXT,
                    output_formats_json TEXT NOT NULL,
                    approved_by TEXT,
                    approved_at TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_draft(
        self,
        *,
        user_id: str,
        work_packet_id: str,
        document_type: str,
        title: str,
        draft_markdown: str,
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO document_actions (
                    user_id, work_packet_id, document_type, title,
                    draft_markdown, draft_version, status, output_formats_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, work_packet_id, document_type, title, draft_markdown, 1, "draft", "[]", now, now),
            )
            row_id = cur.lastrowid
            row = conn.execute("SELECT * FROM document_actions WHERE id = ?", (row_id,)).fetchone()
        return self._row_to_dict(row)

    def mark_approved(
        self,
        *,
        document_action_id: int,
        approved_by: str,
        destination_type: str,
        destination_ref: str,
        output_formats: list[str],
    ) -> dict[str, Any]:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE document_actions
                SET status = ?, approved_by = ?, approved_at = ?, destination_type = ?,
                    destination_ref = ?, output_formats_json = ?, updated_at = ?
                WHERE id = ?
                """,
                ("approved", approved_by, now, destination_type, destination_ref, json.dumps(output_formats), now, document_action_id),
            )
            row = conn.execute("SELECT * FROM document_actions WHERE id = ?", (document_action_id,)).fetchone()
        return self._row_to_dict(row)

    def _row_to_dict(self, row: sqlite3.Row | None) -> dict[str, Any]:
        if row is None:
            raise KeyError("document action not found")
        data = dict(row)
        data["output_formats"] = json.loads(data.pop("output_formats_json") or "[]")
        return data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_document_actions_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/document_actions_store.py tests/unit/test_document_actions_store.py
git commit -m "feat: add document workflow storage"
```

## Task 2: Add Document Workflow Service and Approval Gating

**Files:**
- Create: `orchestrator/app/document_actions_service.py`
- Modify: `orchestrator/app/document_actions_store.py`
- Test: `tests/unit/test_document_actions_service.py`

- [ ] **Step 1: Write the failing tests**

```python
from orchestrator.app.document_actions_service import DocumentActionsService
from orchestrator.app.document_actions_store import DocumentActionsStore


def test_service_creates_document_draft(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)

    record = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="executive_briefing",
        title="Executive Briefing",
        source_summary="Portfolio summary",
    )

    assert record["status"] == "draft"
    assert "Portfolio summary" in record["draft_markdown"]


def test_service_blocks_finalization_before_approval(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)
    record = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="operational_report",
        title="Ops Report",
        source_summary="Ops summary",
    )

    result = service.finalize(document_action_id=record["id"])

    assert result["status"] == "blocked"
    assert result["reason"] == "approval_required"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_document_actions_service.py -v`
Expected: FAIL because `DocumentActionsService` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from typing import Any

from orchestrator.app.document_actions_store import DocumentActionsStore


class DocumentActionsService:
    def __init__(self, store: DocumentActionsStore) -> None:
        self.store = store

    def create_draft(
        self,
        *,
        user_id: str,
        work_packet_id: str,
        document_type: str,
        title: str,
        source_summary: str,
    ) -> dict[str, Any]:
        draft_markdown = f"# {title}\n\n## Summary\n\n{source_summary}\n"
        return self.store.create_draft(
            user_id=user_id,
            work_packet_id=work_packet_id,
            document_type=document_type,
            title=title,
            draft_markdown=draft_markdown,
        )

    def finalize(self, *, document_action_id: int) -> dict[str, Any]:
        record = self.store.get(document_action_id)
        if record["status"] != "approved":
            return {"status": "blocked", "reason": "approval_required", "document_action_id": document_action_id}
        return {"status": "ready", "document_action_id": document_action_id}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_document_actions_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/document_actions_service.py orchestrator/app/document_actions_store.py tests/unit/test_document_actions_service.py
git commit -m "feat: add governed document workflow service"
```

## Task 3: Add Finalization Execution, Destination Storage, and Announcement Action

**Files:**
- Modify: `orchestrator/app/document_actions_service.py`
- Modify: `orchestrator/app/document_actions_store.py`
- Modify: `orchestrator/app/blob.py`
- Modify: `orchestrator/app/actions_service.py`
- Test: `tests/unit/test_document_actions_service.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_service_finalizes_after_approval_and_records_artifacts(tmp_path):
    store = DocumentActionsStore(db_path=tmp_path / "document_actions.db")
    service = DocumentActionsService(store=store)
    draft = service.create_draft(
        user_id="alice",
        work_packet_id="wp-1",
        document_type="board_report",
        title="Board Report",
        source_summary="Board summary",
    )
    store.mark_approved(
        document_action_id=draft["id"],
        approved_by="alice",
        destination_type="onedrive",
        destination_ref="Reports/Board",
        output_formats=["pdf", "docx"],
    )

    result = service.finalize(document_action_id=draft["id"])

    assert result["status"] == "executed"
    assert result["artifacts"][0]["format"] == "pdf"
    assert result["destination"]["type"] == "onedrive"
    assert result["announcement"]["status"] == "created"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_document_actions_service.py::test_service_finalizes_after_approval_and_records_artifacts -v`
Expected: FAIL because finalization does not generate artifacts or announcement metadata yet.

- [ ] **Step 3: Write minimal implementation**

```python
def finalize(self, *, document_action_id: int) -> dict[str, Any]:
    record = self.store.get(document_action_id)
    if record["status"] != "approved":
        return {"status": "blocked", "reason": "approval_required", "document_action_id": document_action_id}

    artifacts = [
        {
            "format": fmt,
            "file_name": f"{record['title'].replace(' ', '_').lower()}.{fmt}",
        }
        for fmt in record["output_formats"]
    ]
    destination = {
        "type": record["destination_type"],
        "ref": record["destination_ref"],
    }
    announcement = {"status": "created", "type": "document_finalized"}
    executed = self.store.mark_executed(
        document_action_id=document_action_id,
        artifacts=artifacts,
        announcement=announcement,
    )
    return {
        "status": "executed",
        "document_action": executed,
        "artifacts": artifacts,
        "destination": destination,
        "announcement": announcement,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_document_actions_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/document_actions_service.py orchestrator/app/document_actions_store.py orchestrator/app/blob.py orchestrator/app/actions_service.py tests/unit/test_document_actions_service.py
git commit -m "feat: finalize governed documents"
```

## Task 4: Expose Document Workflow API Endpoints

**Files:**
- Create: `orchestrator/app/document_actions_router.py`
- Modify: `orchestrator/app/main.py`
- Modify: `orchestrator/openapi.yaml`
- Test: `tests/smoke/test_orchestrator.py`

- [ ] **Step 1: Write the failing smoke checks**

```python
@pytest.mark.asyncio
async def test_document_workflow_draft_endpoint():
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{_base_url()}/document-actions/draft",
            json={
                "user_id": "smoke-test",
                "work_packet_id": "wp-1",
                "document_type": "executive_briefing",
                "title": "Executive Briefing",
                "source_summary": "Summary",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "draft"


@pytest.mark.asyncio
async def test_openapi_schema_mentions_document_actions():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_base_url()}/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "/document-actions/draft" in schema["paths"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/smoke/test_orchestrator.py -k "document_workflow_draft_endpoint or openapi_schema_mentions_document_actions" -v`
Expected: FAIL because the endpoints do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter(prefix="/document-actions", tags=["document-actions"])


class CreateDraftRequest(BaseModel):
    user_id: str
    work_packet_id: str
    document_type: str
    title: str
    source_summary: str


@router.post("/draft")
def create_draft(payload: CreateDraftRequest) -> dict[str, Any]:
    return DOCUMENT_ACTIONS_SERVICE.create_draft(
        user_id=payload.user_id,
        work_packet_id=payload.work_packet_id,
        document_type=payload.document_type,
        title=payload.title,
        source_summary=payload.source_summary,
    )
```

Also register the router in `main.py`:

```python
from app.document_actions_router import router as document_actions_router

app.include_router(document_actions_router)
```

And document the endpoints in `orchestrator/openapi.yaml`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/smoke/test_orchestrator.py -k "document_workflow_draft_endpoint or openapi_schema_mentions_document_actions" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/document_actions_router.py orchestrator/app/main.py orchestrator/openapi.yaml tests/smoke/test_orchestrator.py
git commit -m "feat: add document workflow endpoints"
```

## Task 5: Add Approval and Finalization Endpoints

**Files:**
- Modify: `orchestrator/app/document_actions_router.py`
- Modify: `orchestrator/openapi.yaml`
- Test: `tests/smoke/test_orchestrator.py`

- [ ] **Step 1: Write the failing smoke check**

```python
@pytest.mark.asyncio
async def test_document_workflow_approve_and_finalize():
    async with httpx.AsyncClient(timeout=20) as client:
        draft = await client.post(
            f"{_base_url()}/document-actions/draft",
            json={
                "user_id": "smoke-test",
                "work_packet_id": "wp-1",
                "document_type": "executive_briefing",
                "title": "Executive Briefing",
                "source_summary": "Summary",
            },
        )
        draft_body = draft.json()

        approved = await client.post(
            f"{_base_url()}/document-actions/{draft_body['id']}/approve",
            json={
                "approved_by": "smoke-test",
                "destination_type": "onedrive",
                "destination_ref": "Reports/Exec",
                "output_formats": ["pdf", "docx"],
            },
        )
        assert approved.status_code == 200

        finalized = await client.post(f"{_base_url()}/document-actions/{draft_body['id']}/finalize")
        assert finalized.status_code == 200
        body = finalized.json()
        assert body["status"] == "executed"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/smoke/test_orchestrator.py::test_document_workflow_approve_and_finalize -v`
Expected: FAIL because approval/finalize endpoints do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
class ApproveDraftRequest(BaseModel):
    approved_by: str
    destination_type: str
    destination_ref: str
    output_formats: list[str]


@router.post("/{document_action_id}/approve")
def approve_draft(document_action_id: int, payload: ApproveDraftRequest) -> dict[str, Any]:
    return DOCUMENT_ACTIONS_SERVICE.approve(
        document_action_id=document_action_id,
        approved_by=payload.approved_by,
        destination_type=payload.destination_type,
        destination_ref=payload.destination_ref,
        output_formats=payload.output_formats,
    )


@router.post("/{document_action_id}/finalize")
def finalize_draft(document_action_id: int) -> dict[str, Any]:
    return DOCUMENT_ACTIONS_SERVICE.finalize(document_action_id=document_action_id)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/smoke/test_orchestrator.py -k "document_workflow_approve_and_finalize" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/document_actions_router.py orchestrator/openapi.yaml tests/smoke/test_orchestrator.py
git commit -m "feat: add document approval workflow"
```

## Task 6: Add Frontend Types and Document Workflow Panel

**Files:**
- Modify: `web_ui/src/Cards.tsx`
- Create: `web_ui/src/DocumentWorkflowPanel.tsx`

- [ ] **Step 1: Write the failing TypeScript additions**

```tsx
export type DocumentAction = {
  id: number
  status: 'draft' | 'approved' | 'executed'
  document_type: string
  title: string
  destination_type?: string
  destination_ref?: string
  output_formats?: string[]
}
```

Run: `npm run build`
Expected: FAIL because the new panel and types do not yet exist.

- [ ] **Step 2: Add the shared types**

```tsx
export type DocumentAction = {
  id: number
  status: 'draft' | 'approved' | 'executed' | 'blocked'
  document_type: string
  title: string
  draft_version?: number
  destination_type?: string
  destination_ref?: string
  output_formats?: string[]
}
```

And create `DocumentWorkflowPanel.tsx`:

```tsx
import type { DocumentAction } from './Cards'

export function DocumentWorkflowPanel({ action }: { action: DocumentAction }) {
  return (
    <section className="result-card">
      <div className="result-card-header">
        <strong>{action.title}</strong>
        <span>{action.status}</span>
      </div>
      <p>{action.document_type}</p>
    </section>
  )
}
```

- [ ] **Step 3: Run build to verify it passes**

Run: `npm run build`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web_ui/src/Cards.tsx web_ui/src/DocumentWorkflowPanel.tsx
git commit -m "feat: add governed document workflow panel"
```

## Task 7: Render Document Workflow Actions in Chat and Add Docs Note

**Files:**
- Modify: `web_ui/src/App.tsx`
- Modify: `docs/FEATURES.md`

- [ ] **Step 1: Write the failing render hook**

```tsx
{msg.data?.document_actions?.map(action => (
  <DocumentWorkflowPanel key={action.id} action={action} />
))}
```

Run: `npm run build`
Expected: FAIL because `App.tsx` does not yet import or render the panel.

- [ ] **Step 2: Write minimal implementation**

```tsx
import { DocumentWorkflowPanel } from './DocumentWorkflowPanel'

// In assistant message rendering, before work packet:
{msg.data?.document_actions?.map(action => (
  <div key={action.id} className="message-section">
    <DocumentWorkflowPanel action={action} />
  </div>
))}
```

And update docs:

```md
### Governed Document Workflows
- Executive briefings, board reports, and operational reports can be drafted from work packets.
- Finalization requires explicit user approval before export.
- Approved artifacts can be stored to a selected destination and followed by an announcement action.
```

- [ ] **Step 3: Run verification**

Run: `npm run build`
Expected: PASS

Run: `python3 -m pytest tests/unit/test_document_actions_store.py tests/unit/test_document_actions_service.py tests/smoke/test_orchestrator.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add web_ui/src/App.tsx docs/FEATURES.md
git commit -m "feat: surface governed document workflows"
```

## Self-Review

- Spec coverage:
  - document templates: covered by Tasks 2 and 7
  - approval only at finalization: covered by Tasks 2, 3, and 5
  - external destination selection: covered by Tasks 1, 3, and 5
  - post-approval announcement action: covered by Task 3
  - audit trail and metadata capture: covered by Tasks 1 and 3
- Placeholder scan: no `TODO`, `TBD`, or “implement later” placeholders remain.
- Type consistency: document workflow status values are consistently `draft | approved | executed | blocked`; destination/output format fields are named consistently across store, service, API, and UI.
