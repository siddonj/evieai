# EvieAI Governed Document Workflows Design

Date: 2026-06-19
Status: Draft approved in conversation
Topic: First governed-actions slice for document workflows

## 1. Problem Statement

The work-packet foundation now gives EvieAI a structured way to move from question to evidence-backed result. The next step is to add a governed action that turns those results into official artifacts without immediately taking on the full complexity of generic write-backs across all systems.

The first governed-actions slice should focus on `document workflows` because it aligns with the current strengths of the product:
- evidence-backed answers
- dynamic cards and summaries
- report generation
- exports
- low-risk write-back compared with direct system mutation

The goal is to let a user move from question to draft to approved final artifact, then store that artifact to a selected destination and create a follow-up announcement action.

## 2. Product Positioning

This slice is not a generic approval engine yet. It is a `governed document finalization` workflow built on top of work packets.

Primary promise:

`EvieAI can turn a grounded answer into an official document with one approval step before final export and distribution.`

This should prove that EvieAI can do more than answer questions:
- synthesize evidence
- generate formal outputs
- enforce governance at the right boundary
- complete a real write-back outcome

## 3. Scope

Version 1 should support one shared workflow with three document template variants:
- `executive briefing`
- `board report`
- `operational report`

These should not be built as separate workflow systems. They are template variants on the same governed pipeline.

## 4. Experience Model

The default experience should be:

1. User asks a question.
2. EvieAI returns a work packet.
3. The work packet proposes a document action.
4. The user selects a document type and iterates on the draft.
5. The user approves finalization.
6. EvieAI generates final artifacts, stores them to the chosen destination, and creates a follow-up announcement action.

### 4.1 Approval Boundary

Approval should apply only to `finalization`, not to drafting or revision.

This means:
- EvieAI may draft freely
- EvieAI may revise drafts freely
- approval is required only before the document becomes official/exportable

This matches the chosen governance boundary: fast iteration during drafting, explicit control when the document becomes final and externalized.

### 4.2 Destination Model

Approved documents should live in:
- EvieAI's internal artifact model
- plus a selected external file destination

Version 1 should support the concept of a destination such as:
- OneDrive
- SharePoint
- file storage

The destination must be explicit before approval.

### 4.3 Post-Approval Behavior

After approval, version 1 should:
- generate final artifacts
- store them to the selected destination
- create a follow-up announcement action

The announcement action can be lower risk in version 1, such as:
- a drafted message
- a drafted notification record
- a queued communication action

It does not have to start as a fully autonomous outbound communication if that adds operational risk.

## 5. Workflow Lifecycle

The governed document lifecycle should be:

### 5.1 Draft

EvieAI generates the document from the work packet and supporting evidence.

Characteristics:
- editable
- revisable
- not yet official
- no approval required

### 5.2 Ready for Approval

The user requests finalization or export.

At this point, EvieAI should capture:
- template type
- selected destination
- selected output formats
- draft version identifier
- source work packet reference

This produces a concrete finalization request.

### 5.3 Approved

The requesting user approves the finalization request.

Approval metadata must record:
- approving user
- approval timestamp
- approved draft version
- approved output formats
- approved destination

### 5.4 Executed

After approval, EvieAI:
- generates the final artifact set
- stores artifacts to the chosen destination
- creates the announcement action

### 5.5 Recorded

EvieAI records the full chain:
- originating work packet
- draft version
- approval event
- generated artifacts
- storage location
- follow-up announcement outcome

## 6. Approval Model

Version 1 approval should be intentionally simple.

Approver:
- `requesting user`

Approval trigger:
- finalization only

No approval required for:
- draft generation
- draft revision
- internal iteration before finalization

This is sufficient to prove governed behavior without introducing role-routing complexity too early.

## 7. Core Components

This slice needs five first-class components.

### 7.1 Document Action Model

Represents:
- document type
- draft state
- approval state
- destination
- requested output formats
- generated artifacts
- announcement action state

This becomes the domain object for governed document finalization.

### 7.2 Draft Generation Adapter

Uses existing report/document generation capability to produce:
- executive briefing
- board report
- operational report

This adapter should consume work-packet data rather than raw chat text whenever possible.

### 7.3 Approval Service

Creates and resolves finalization requests.

Responsibilities:
- create approval request
- validate requesting user authority
- record approval metadata
- block export/storage until approved

### 7.4 Artifact Execution Service

After approval:
- generate the final files
- store files to the chosen destination
- return storage metadata and artifact identifiers

### 7.5 Announcement Action

After successful storage:
- create a follow-up notification action
- associate it with the finalized document
- record status for auditability

This is the first controlled post-approval write-back action beyond artifact storage itself.

## 8. Product Requirements

### 8.1 Drafting Requirements

- A user can create one of three document variants from a work packet.
- The system can revise drafts without requiring approval.
- Drafts retain a link to the source work packet and evidence context.

### 8.2 Governance Requirements

- A document cannot be finalized/exported without explicit approval from the requesting user.
- The approval record captures user, version, destination, and output formats.
- The system distinguishes draft state from approved state.

### 8.3 Execution Requirements

- After approval, the system generates final artifacts.
- The system stores final artifacts to the selected destination.
- The system creates an announcement action after successful storage.
- The execution chain is auditable end to end.

## 9. Non-Goals

Version 1 does not need to include:
- role-based approver routing
- named multi-step approval chains
- arbitrary generic action governance for all connectors
- direct mutation of CRM/ERP/task systems as part of this slice
- mandatory external system-of-record enforcement for every artifact

Those belong in later governed-actions phases.

## 10. Fit With Current Repository

This design fits the current repo well.

Already aligned:
- work packets now exist as a structured response layer
- document generation already exists conceptually and in routing
- exports already exist
- chat UI can now surface structured packet content

Likely new areas for implementation:
- document action state model
- approval persistence and API
- destination selection flow
- artifact finalization service
- post-approval announcement action

## 11. Success Metrics

Recommended success metrics:
- time from work packet to first draft
- percentage of drafts finalized after approval
- time from approval to stored artifact
- successful storage rate by destination
- percentage of finalizations with complete audit metadata
- percentage of approvals followed by successful announcement action

## 12. Recommendation

The next governed-actions slice should be:

`one governed document finalization workflow with three template variants, approval only at final export, external storage to a selected destination, and a post-approval announcement action.`

This is the strongest next step because it:
- builds directly on the work-packet foundation
- proves real governance without overbuilding
- creates a visible write-back outcome
- keeps the approval model simple enough to ship quickly
