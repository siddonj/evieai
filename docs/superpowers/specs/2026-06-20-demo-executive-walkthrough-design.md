# Executive Demo Walkthrough Design

**Date:** 2026-06-20
**Primary account:** Madison Street Partners
**Primary persona:** Robert Henderson, Managing Partner
**Demo format:** 20-minute guided walkthrough with Q&A

## Goal

Create a polished demo path that sells EvieAI to investor and client leadership audiences by showing three things clearly:

1. The app answers real business questions fast.
2. The app can move across multiple data sources in one conversation.
3. The app can turn answers into exportable business artifacts.

The demo should feel like a real executive workflow, not a feature tour.

## Audience

The target audience is:

- investor and client leadership,
- prospective customers evaluating the product,
- stakeholders who want to see practical AI value quickly.

The demo should speak in business terms first and technical terms only when needed to prove credibility.

## Narrative

The demo follows a single storyline:

`Robert Henderson` -> `portfolio performance` -> `operational visibility` -> `live chat across data types` -> `export to PDF or Excel`

This keeps the presentation coherent and avoids a feature dump.

The story should communicate that EvieAI is the system Robert uses when he needs:

- a portfolio snapshot,
- the current operational picture,
- a quick answer from the right source,
- a polished output he can share.

## Scope

This demo pass focuses on presentation, not core platform re-architecture.

Included:

- a named executive demo persona,
- a named client/account anchor,
- a guided 20-minute demo script,
- curated prompts that show portfolio, operations, and export behavior,
- a clear live chat sequence that demonstrates source switching,
- a polished path to PDF or Excel export.

Not included:

- new data ingestion,
- new external integrations,
- new auth flows,
- new pricing or billing flows,
- a full redesign of every product surface.

## Demo Structure

### 1. Opening and context

Start with a concise business framing:

- Robert Henderson at Madison Street Partners needs one place to understand portfolio performance and operational status.
- The pain point is switching between systems and assembling answers manually.
- EvieAI is the single chat surface that pulls those answers together.

This opening should be short. The demo should move quickly into product proof.

### 2. Portfolio performance

The first live question should establish executive value.

Use a prompt such as:

- `Give me a portfolio performance summary for Madison Street Partners.`

The desired response is a clear summary that highlights:

- occupancy,
- NOI,
- portfolio value,
- active deals or pipeline,
- top properties by performance.

If the dashboard view adds clarity, open the performance dashboard next and anchor the chat result to the visual summary.

### 3. Operational visibility

After performance, switch to an operational question such as:

- `What are the biggest operational issues right now?`
- `Show open work orders by property.`

This part proves the assistant can move from strategy to operations without losing context.

The response should feel grounded in actual operational data, not generic prose.

### 4. Multi-source live chat

The demo should then show one conversation asking for several data types:

- portfolio summary,
- operational data,
- policy or document information,
- a generated report.

The goal is to make it obvious that the assistant can route to different sources as the question changes.

Keep the live sequence short. The audience should understand the pattern after two or three questions.

### 5. Export

The final proof point is that the answer can become something shareable.

Use a prompt such as:

- `Generate a PDF executive summary.`
- `Export this to Excel.`

The export step should feel like the end of a business workflow, not a separate tool.

## Product Requirements

### Demo persona and account anchoring

The app should present the demo around Robert Henderson and Madison Street Partners.

The persona should be visible enough to guide the story, but not so prominent that it distracts from the product itself.

### Curated demo prompts

The chat surface should include a small set of polished prompts that support the demo flow.

Recommended prompts:

- portfolio performance summary,
- open work orders,
- operational issues by property,
- executive summary export,
- Excel export.

These prompts should make the demo repeatable without requiring a live operator to improvise.

### Dashboard entry points

The demo should keep the current performance and network dashboard surfaces available as supporting evidence.

The demo flow should prefer chat first, then dashboards only when they clarify or reinforce the answer.

### Export behavior

The export path should be visible and easy to narrate.

At minimum, the demo must show that outputs can be prepared in business-friendly formats:

- PDF,
- Excel.

The export action should preserve the connection to the underlying answer so the audience sees that the output is derived from the same conversation.

## Talk Track

Recommended talk track:

1. Robert wants a fast read on his business.
2. EvieAI gives him the performance picture.
3. He follows up on operations without changing tools.
4. He asks for the right source and gets a grounded answer.
5. He exports the result into something shareable.

Keep the language executive-facing. Avoid long explanations of implementation unless asked.

## Success Criteria

The demo is successful if:

- the audience understands the product in under 5 minutes,
- the audience sees a live question answered from real app data,
- the audience sees a second question answered from a different source type,
- the audience sees an export path that produces a business artifact,
- the demo feels polished and intentional rather than generic.

## Risks

- If the demo asks too many questions, it will feel like a feature checklist.
- If the flow jumps between unrelated surfaces, the narrative will feel weak.
- If exports are buried behind too many clicks, the business value will be lost.
- If the persona/account anchor is not explicit, the story will feel abstract.

## Implementation Notes

The implementation should favor small, high-leverage changes:

- a guided demo entry point or demo framing on the chat surface,
- curated prompt cards for the walkthrough,
- consistent naming of the account and persona,
- prominent export affordances,
- reuse of the existing performance and operational dashboards.

The first version should optimize for presentation quality and reliability before expanding the feature set.
