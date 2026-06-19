# EvieAI Work Orchestrator Design

Date: 2026-06-19
Status: Draft approved in conversation
Topic: Reposition EvieAI from a multi-source Q&A app into an evidence-first work orchestrator

## 1. Problem Statement

EvieAI already has the right structural foundation for multi-source enterprise intelligence: a central orchestrator, multiple MCP-backed data/tool services, report generation, export support, and a chat UI with cards. The current product story, however, still reads primarily as "chat with tools" rather than "governed orchestration across a user's environment."

That gap matters because the intended user value is broader than answering questions. The product should help a user ask one question, reconcile evidence across multiple systems, generate polished outputs, and complete approved follow-up work.

The design goal is to make EvieAI's primary promise:

`One question across many enterprise systems, one grounded answer, and a governed path from answer to deliverable to action.`

## 2. Product Positioning

EvieAI should be positioned as a `work orchestrator`, not just an answer engine or analyst copilot.

Primary proof point:
- `Cross-source intelligence` is the lead message.

Supporting proof points:
- Evidence-first deliverables such as cards, briefings, and formal exports.
- Semi-autonomous, policy-governed execution when the user wants the system to move from analysis into action.

This means the product must optimize first for trustable synthesis across multiple systems, then use exports and actions to reinforce that intelligence rather than distract from it.

## 3. Experience Model

The default user journey should be:

1. User asks a question in chat.
2. The orchestrator queries relevant sources in parallel.
3. The system reconciles evidence across those sources.
4. The UI returns a `work packet` rather than only markdown prose.
5. If ambiguity or write-back action matters, the packet escalates into a persistent `workspace session`.

### 3.1 Default Experience: Work Packet

The default result for meaningful queries should be a structured `work packet` containing:
- concise executive answer
- evidence cards grouped by source
- source agreement and conflict summary
- confidence or certainty indicators
- dynamic KPI or summary cards where appropriate
- recommended exports
- recommended next actions

This preserves fast time-to-value while making orchestration visible and tangible.

### 3.2 Escalation Experience: Workspace Session

When the system encounters material source conflict, incomplete evidence, or a need for multi-step execution, the user should be able to escalate into a persistent `workspace session`.

The workspace session should expose:
- active objective
- source retrieval status
- reconciliation status
- draft outputs
- action queue
- approval checkpoints
- execution log and audit trail

The workspace is not the default for every question. It is the governed escalation path when a simple answer is not enough.

## 4. Core Product Components

EvieAI needs five first-class product layers.

### 4.1 Source Orchestration Layer

This layer plans and executes retrieval across mail, files, SQL, knowledge base, analytics, memory, and future systems.

Responsibilities:
- classify the request
- pick relevant systems
- define a per-source retrieval plan
- run calls in parallel where possible
- normalize source metadata for downstream reasoning

This extends the current orchestrator from "tool calling" into explicit source planning.

### 4.2 Reconciliation Layer

This is the key missing differentiator.

Responsibilities:
- compare findings across systems
- identify agreement, partial overlap, and contradictions
- distinguish direct evidence from inference
- determine whether the result can be answered confidently or should escalate

Every important conclusion should be labeled as one of:
- `confirmed`
- `partial`
- `conflicting`
- `inferred`

### 4.3 Work Packet Renderer

The UI should treat a response as a structured object, not just markdown text.

Responsibilities:
- render answer summary
- render evidence cards by source
- render conflict and confidence indicators
- render dynamic cards for metrics, highlights, and report fragments
- expose export actions
- expose next-step actions

### 4.4 Governed Action Layer

Because the target state is semi-autonomous workflows, actions need a lifecycle separate from answer generation.

Action lifecycle:
1. propose
2. policy-check
3. route to required approval model
4. execute
5. log and audit
6. support rollback where possible

This layer is what makes bi-directional orchestration real rather than aspirational.

### 4.5 Artifact Generation Layer

Exports and formal outputs should be generated from the same structured work packet that powers the UI.

Outputs should include:
- polished dynamic cards for on-screen presentation
- formal reports
- PDF exports
- Word exports
- Excel exports

This ensures consistency between what the user sees in chat, what they present, and what they share externally.

## 5. Request Lifecycle

Every request should move through a consistent internal lifecycle.

### 5.1 Intent Classification

Classify whether the request is:
- information only
- deliverable generation
- action request
- mixed request

### 5.2 Source Plan

Define which systems will be queried, what each system is expected to contribute, and which retrieval steps can run in parallel.

### 5.3 Evidence Normalization

Convert results into a common evidence model with:
- source identity
- timestamps
- entity references
- confidence signals
- traceable supporting excerpts or payload references

### 5.4 Reconciliation

Compare normalized evidence and produce:
- aligned facts
- conflicting facts
- unresolved gaps
- inferred conclusions

Default behavior for ambiguity:
- show evidence-first reconciliation
- allow escalation into workspace session

### 5.5 Work Packet Generation

Generate a structured result with:
- answer summary
- evidence by source
- reconciliation status
- dynamic cards
- suggested exports
- suggested next actions

### 5.6 Governed Execution

When the user or policy allows action, transition from packet to execution surface.

Execution should support:
- approvals
- policy gates
- allowed action classes
- audit logging
- outcome summaries back to the user

## 6. Guardrails and Trust Model

Trust must be a visible product capability, not only an internal engineering concern.

The user should always be able to see:
- which systems were queried
- which claims came from which systems
- where the system is confident
- where the system is inferring
- where systems disagree
- what action will happen before it happens
- what action completed afterward

### 6.1 Action Control Classes

Define three control classes:
- `read`: may run automatically
- `draft`: may prepare outputs automatically, but requires review before send or update
- `execute`: may complete approved action classes under policy and audit controls

### 6.2 Approval Model

The approval model should be explicit and explainable.

Examples:
- sending external email likely requires approval
- updating a CRM record may require approval depending on field and system
- generating a draft report does not require approval

The exact policy matrix is an implementation detail, but the design requires a visible separation between read, draft, and execute classes.

## 7. Fit With Current Repository

The repository is directionally correct. It already contains many of the right building blocks.

### 7.1 Already on the Right Track

- FastAPI orchestrator as central control plane
- MCP server separation by data/tool domain
- chat UI with dynamic card concepts
- report generation and export endpoints
- approval and safety concepts already present in architecture/docs

### 7.2 Key Gaps to Close

- no explicit reconciliation model across sources
- no first-class structured `work packet` response contract
- no clear product distinction between answer flow and execution flow
- no visible action lifecycle model in the user experience
- exports appear as features rather than outputs of a shared artifact model

## 8. Product Requirements

The next iteration of EvieAI should satisfy the following requirements.

### 8.1 Intelligence Requirements

- A user can ask one question across multiple systems.
- The answer shows which systems contributed evidence.
- The system distinguishes confirmed facts, partial matches, conflicts, and inferences.
- Conflicting evidence is surfaced rather than hidden.

### 8.2 Deliverable Requirements

- A user can generate polished dynamic cards from the same structured answer.
- A user can export formal artifacts as PDF, Word, and Excel where appropriate.
- Reports and exports remain consistent with the on-screen work packet.

### 8.3 Orchestration Requirements

- The system can propose follow-up actions grounded in the packet.
- The system can execute allowed action classes under guardrails.
- The user can see pending approvals, completed actions, and audit history.
- Material ambiguity can escalate into a persistent workspace session.

## 9. Non-Goals

The following are intentionally out of scope for this design:
- replacing the chat entry point with a mandatory case-management interface
- making every query open a persistent workspace
- hiding ambiguity to preserve conversational smoothness
- treating export generation as an isolated feature detached from the main response model

## 10. Success Metrics

Success should be measured with orchestration-aware metrics rather than generic chat metrics alone.

Recommended metrics:
- percentage of answers using more than one relevant source
- percentage of packets with explicit evidence attribution
- percentage of packets that detect and surface source conflict
- time from question to usable deliverable
- time from question to completed approved action
- export usage by format
- rate of user correction after high-confidence answers

## 11. Recommendation

EvieAI is on the right track structurally, but the product should be reframed around three first-class concepts:
- `evidence reconciliation`
- `work packets`
- `governed actions`

If those become the center of the product, the current orchestrator architecture can support a compelling work orchestration story. Without them, the product risks reading as a capable but familiar multi-source enterprise chat assistant.
