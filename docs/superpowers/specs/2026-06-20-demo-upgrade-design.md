# Demo Upgrade Design

**Date:** 2026-06-20  
**Primary demo spine:** Multi-source chat with export  
**Goal:** Make the app feel credible, useful, and polished in a live demo

## Goal

The current product already proves the basics:

- chat exists,
- multiple data surfaces exist,
- work packets and document workflows exist,
- exports are tracked.

What is still missing is the layer that makes the product feel like a strong live demo. This upgrade focuses on three problems the audience will notice immediately:

1. Answers can feel vague unless the assistant shows where it got the result.
2. The demo can feel static unless the presenter has a guided path.
3. Export can feel like an afterthought unless the artifact state is visible and polished.

This design turns the current chat experience into a more convincing demo surface without re-architecting the product.

## Scope

### Included

- a guided demo path for presenters,
- visible source grounding on answers,
- demo-safe fallback behavior when a connector is slow or unavailable,
- export preview and artifact states,
- stronger chat follow-up and handoff cues,
- a lightweight demo launcher that is easy to reset during a live session.

### Not included

- new external integrations,
- new authentication flows,
- new data ingestion pipelines,
- a full redesign of the application shell,
- changing the core backend architecture.

## User Experience

The upgraded demo should support one primary flow:

`launch demo` -> `ask a live question` -> `see source selection` -> `see grounded answer` -> `follow up` -> `export PDF / Excel` -> `review artifact`

The presenter should be able to:

- start from a single obvious entry point,
- step through a curated sequence of questions,
- answer live follow-ups without breaking the story,
- end with a deliverable the audience can share.

The audience should leave with three impressions:

- the product knows how to route questions,
- the product knows how to explain the answer,
- the product knows how to package the result.

## Architecture

### 1. Demo mode controller

Add a small demo-mode state layer in the frontend that controls the presenter experience.

Responsibilities:

- show a demo entry state,
- expose a small set of curated prompts,
- advance the presentation path in a predictable order,
- allow reset without page refresh,
- optionally auto-sequence the first few prompts for booths or sales calls.

This controller should sit above the existing chat experience. It should not replace normal chat.

### 2. Answer grounding layer

The chat response surface should display enough context for the audience to trust the answer.

The answer card should include:

- a concise answer summary,
- the source class used to answer it,
- a visible evidence count or source count,
- a short “why this source” cue when the routing is interesting,
- a confidence or certainty indicator when the response is partial or inferred.

The goal is not academic provenance. The goal is demo-grade transparency.

### 3. Export artifact layer

Export should feel like the end of a workflow, not a file download button.

The export experience should show:

- what will be exported,
- which formats are available,
- whether the artifact is queued, running, completed, or failed,
- a way to view the generated artifact or summary,
- a clear link between the answer and the exported deliverable.

### 4. Fallback and demo safety layer

The demo should not fall apart if a connector is slow or if a source returns partial data.

When a source is unavailable, the app should:

- show the failure as a surfaced state,
- fall back to a demo-safe sample response when appropriate,
- preserve the flow so the presenter can continue.

This layer should be visible enough that the demo still feels real, but not so noisy that it distracts the audience.

## Components

### Frontend

The frontend needs three focused additions:

1. A demo launcher or scenario card set.
2. A richer answer panel with source and evidence cues.
3. An export state view with artifact preview and status.

These should be built as additive changes to the current shell, not a separate demo app.

### Orchestrator

The orchestrator should keep doing the routing and tool calling.

For the demo upgrade, it also needs to return enough structured metadata for the UI to explain:

- which source answered the question,
- whether the answer is complete or partial,
- which exports are available,
- which follow-up actions are recommended.

### Existing workflow surfaces

The work packet and document workflow surfaces already carry some of the right ideas.

This upgrade should reuse those patterns instead of inventing new ones:

- evidence cards,
- reconciliation state,
- export package tracking,
- artifact lists.

## Data Flow

1. The presenter starts a curated scenario or types a live question.
2. The orchestrator routes the request to the appropriate source.
3. The response returns with answer text plus structured metadata.
4. The UI renders the answer, source, and evidence in one place.
5. If the user asks for a report or export, the same result is promoted into an artifact state.
6. The export artifact becomes visible in the UI and can be opened or downloaded.

The important constraint is that the answer and the export must be clearly linked.

## Error Handling

The demo should degrade gracefully.

### Slow or missing source

- Show a visible partial or fallback state.
- Keep the presenter in the same flow.
- Offer a safe follow-up prompt instead of stopping the demo.

### Export failure

- Mark the export artifact as failed.
- Show a compact error message.
- Leave the originating answer visible so the presenter can explain the outcome.

### Empty or vague answer

- Surface the answer as partial or low-confidence.
- Show the source class that was used.
- Suggest a follow-up prompt that can sharpen the result.

### Reset

- Reset demo state without clearing the user’s broader session unless explicitly requested.
- Preserve chat history if the presenter wants to reuse it.

## Testing

The upgrade should be verified at three levels.

### Unit tests

- demo state transitions,
- source metadata rendering,
- export state rendering,
- fallback state selection.

### Integration tests

- prompt -> orchestrator -> answer metadata,
- export request -> artifact state,
- partial result -> surfaced fallback path.

### Manual demo checks

- launch the guided path,
- ask a follow-up question,
- trigger an export,
- simulate a slow source,
- confirm the presenter can still finish the flow.

## Success Criteria

The upgrade is successful if:

- the presenter can run the demo without improvising the story,
- the audience can see which source produced an answer,
- the answer feels grounded rather than generic,
- export feels like a real product outcome,
- the demo still works when one source is partial or slow.

## Recommended Path

Build the demo upgrade in this order:

1. Guided demo mode and curated prompts.
2. Answer grounding and source transparency.
3. Export artifact preview and states.
4. Fallback behavior for demo safety.

This order delivers the biggest improvement in credibility fastest.

