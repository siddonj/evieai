# Demo Report Workflow Spine Design

**Date:** 2026-06-19
**Primary demo path:** Portfolio performance review
**Secondary demo path:** Board packet

## Goal

Turn the current governed document workflow into a coherent demo spine that proves the orchestrator can:

- gather and synthesize answers from multiple sources,
- promote the result into a governed workflow,
- produce polished presentation surfaces,
- generate formal export packages, and
- show downstream handoff state in a visible operational feed.

The experience should read as one connected product flow rather than a set of unrelated features.

## Scope

This slice adds three connected capabilities:

1. A formal export-package step for finalized document workflows.
2. A presentation-style report viewer for finalized workflows.
3. Seeded playbook cards for repeatable demo scenarios.

These three additions all attach to the existing document workflow entity and reuse the orchestrator actions system where possible.

## Product Narrative

The demo flow should be:

`Playbook card` -> `chat kickoff` -> `draft workflow` -> `approve` -> `finalize` -> `export package` -> `report viewer` -> `outbox handoff`

This is the product claim in executable form:

- the user starts from an intelligible business objective,
- the orchestrator gathers and structures information,
- the user governs the result through approval and finalization,
- the system emits formal artifacts for consumption elsewhere,
- the user presents the result in a polished viewer, and
- the downstream handoff is visible in the outbox.

## Architecture

### Anchor entity

The document workflow record remains the source-of-truth anchor after chat. It owns:

- draft metadata,
- approval/finalization state,
- finalized artifacts,
- export-package metadata,
- viewer-facing report content, and
- downstream announcement linkage.

### Action model

The existing actions system should be reused for export tracking.

The current model already creates internal announcement actions from finalized document workflows. The export-package step should follow the same pattern:

- `source_id`: `document_workflow`
- `entity_type`: `export_package`
- idempotent creation per document workflow
- status progression visible through the actions feed

This keeps the outbox and operational ledger conceptually consistent. Announcements and export packages are both governed downstream actions emitted by the same source entity.

### Backend execution model

For the demo, export-package execution may remain synchronous in-process if that is the fastest stable path. The user-facing behavior should still read as a tracked workflow with explicit status and persisted results.

That means the backend may:

1. create the export action,
2. render or derive the target artifacts,
3. persist export results on the document workflow,
4. mark the export action completed or failed.

If true async execution is added later, the API and persistence model should not need to change substantially.

## Feature Design

### 1. Formal export package

#### User behavior

Once a document workflow is finalized, the user can trigger `Export package`.

This action should:

- create a tracked export-package action,
- generate `pdf`, `docx`, and `xlsx` artifacts for the finalized workflow,
- persist the artifact list and action metadata on the document workflow,
- surface completion state in the workflow UI and report viewer.

#### Data model additions

Each document workflow should gain export-package metadata such as:

- `export_package`
  - `action_id`
  - `status`
  - `created_at`
  - `updated_at`
  - `artifacts`
  - optional `error`

Artifact items should align with the current artifact model where practical:

- format
- file name
- local storage reference
- optional blob URL
- size in bytes

#### API shape

Add a dedicated route on the document workflow surface, for example:

- `POST /document-actions/{document_action_id}/export-package`

This route should:

- enforce the same ownership/auth rules as other document workflow endpoints,
- require finalized state before export,
- be idempotent for the same finalized workflow unless a reset/regenerate path is explicitly added later.

### 2. Presentation-style report viewer

#### Purpose

The viewer must feel presentation-ready. It is not just an operational detail pane.

It should help the user present a finalized workflow as a business artifact with clear status, summary, and deliverables.

#### Layout

The viewer page should include:

- title and report type
- summary band with key workflow status
- artifact and export chips
- governed status timeline
- downstream handoff state
- readable narrative/report body
- actions area for export package and artifact access

The initial viewer shell should favor the `Portfolio performance review` scenario:

- portfolio summary framing,
- concise executive overview,
- visible artifact readiness,
- clear finalization/export state.

`Board packet` should reuse the same viewer shell but swap labels/copy where needed instead of introducing a second page type.

#### Navigation

Users should be able to open the viewer from at least:

- the documents list,
- the in-chat document workflow card after finalization,
- the outbox when a completed announcement references the workflow.

### 3. Seeded playbook cards

#### Purpose

Playbook cards make the demo repeatable and legible for a single-user environment. They should reduce improvisation without bypassing the real orchestration flow.

#### Initial scenarios

At minimum:

1. `Portfolio performance review` as the hero scenario.
2. `Board packet` as the secondary scenario.

Each card should include:

- scenario name,
- what business question it answers,
- the expected signals or source types,
- the outputs the user should expect,
- a primary CTA such as `Run scenario`.

#### Behavior

Selecting a playbook card should seed the existing chat/workflow path, not create a detached shortcut path.

The card may:

- inject a polished starter prompt into chat, or
- directly trigger the same orchestrated request path used by manual chat,

but the resulting outputs must still land in the same governed document workflow flow so that draft, approve, finalize, export, viewer, and outbox all remain connected.

## State Model

Primary visible states for the demo:

1. Drafted
2. Approved
3. Finalized
4. Export package queued
5. Export package running
6. Export package completed
7. Export package failed
8. Announcement delivered

The UI should emphasize clear progression rather than exposing internal implementation details.

For a synchronous backend implementation, the user may move quickly from queued/running to completed, but the state model should still exist explicitly in the persisted data and UI.

## UI Surface Changes

### Chat surface

- Add playbook cards alongside or near the existing suggested prompts.
- Keep the surface lightweight; the cards are entry points, not a dashboard rewrite.
- Preserve the current product shell and status-bar navigation.

### Document workflow panel

- Add an `Export package` action after finalization.
- Show export status and exported artifact counts.
- Provide a `View report` entry point once the workflow is meaningful to present.

### Documents view

- Allow opening a workflow into the dedicated report viewer.
- Surface export-package status in the list context where useful.

### Report viewer

- New dedicated page/view in the frontend app.
- Optimized for polished presentation and artifact access.

### Outbox

- Continue showing announcement actions.
- Do not add export-package actions to the outbox in this slice.
- The main requirement is that downstream orchestration remains visible and attributable to the workflow.

## Error Handling

### Export package

- If export is requested before finalization, return a clear 4xx response.
- If export generation fails, persist a failed export-package state and expose a concise error summary.
- If an export already exists for the current finalized workflow, return the existing package instead of duplicating records.

### Viewer

- If a workflow is missing or unauthorized, show the same access/error semantics used by the current document workflow routes.
- If export artifacts are absent, the viewer should still render the finalized report content and clearly indicate exports are not ready.

### Playbooks

- If a playbook-triggered run fails, the user should land back in the existing chat error path rather than a separate scenario-specific failure mode.

## Testing Strategy

### Backend

Add unit coverage for:

- export-package action creation,
- finalized-only export enforcement,
- persisted export metadata on the document workflow,
- idempotent repeat export behavior,
- artifact generation metadata and blob promotion where available.

Add smoke coverage for the full happy path:

1. create draft
2. approve
3. finalize
4. export package
5. fetch updated workflow
6. verify export metadata and artifacts

### Frontend

- keep `npm run build` as a required verification step,
- add lightweight logic coverage only where the repo already supports it cleanly,
- otherwise rely on typed integration and build validation for this slice.

The frontend should at minimum compile cleanly with the new viewer, playbook, and export states wired through the shared types.

## Non-Goals

This slice does not include:

- multi-user workflow assignment,
- background worker infrastructure,
- editable report-template design tools,
- generalized presentation framework beyond this report viewer,
- a fully generic scenario-builder system.

## Implementation Notes

- Prefer extending existing document workflow storage and actions patterns instead of creating parallel systems.
- Preserve the current local-demo friendliness of the product.
- Optimize for the single-user demo case without hard-coding the entire flow into a fake experience.

## Success Criteria

The slice is successful when a demo user can:

1. launch `Portfolio performance review` from a playbook card,
2. produce a governed document workflow through the existing flow,
3. approve and finalize it,
4. trigger a formal export package,
5. open a polished report viewer,
6. access formal artifacts in `pdf`, `docx`, and `xlsx`,
7. show visible downstream orchestration in the outbox.
