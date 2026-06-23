# Work Packet Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the first production slice of EvieAI's work-orchestrator model by returning structured work packets with normalized evidence and reconciliation summaries from `/chat`, then rendering them in the web UI.

**Architecture:** Keep the existing `reply + tool_calls + mcp_results` contract intact while adding a parallel `work_packet` object. Implement normalization and reconciliation in a focused backend module, thread the new field through streaming and batch chat responses, then render the packet in a dedicated React component so the UI can evolve without bloating `Cards.tsx` or `App.tsx`.

**Tech Stack:** FastAPI, Pydantic, pytest, React 18, TypeScript, Vite

---

## File Structure

- Create: `orchestrator/app/work_packets.py`
  Responsibility: normalize raw MCP results into evidence items, build a reconciliation summary, and assemble the `work_packet` payload.
- Modify: `orchestrator/app/main.py`
  Responsibility: extend `ChatResponse`, attach `work_packet` to SSE `done` events and batch responses.
- Modify: `orchestrator/openapi.yaml`
  Responsibility: document the new response contract for `/chat` and `/chat/batch`.
- Create: `tests/unit/test_work_packets.py`
  Responsibility: unit-test normalization, status labeling, and packet assembly.
- Modify: `tests/smoke/test_orchestrator.py`
  Responsibility: assert the new `work_packet` field exists and has stable top-level shape.
- Create: `web_ui/src/WorkPacketPanel.tsx`
  Responsibility: render answer summary, evidence by source, and reconciliation status from the new packet.
- Modify: `web_ui/src/Cards.tsx`
  Responsibility: add TypeScript types for `work_packet`.
- Modify: `web_ui/src/App.tsx`
  Responsibility: render `WorkPacketPanel` when present while preserving existing tool/result rendering.

## Task 1: Define the Work Packet Domain Model

**Files:**
- Create: `orchestrator/app/work_packets.py`
- Test: `tests/unit/test_work_packets.py`

- [ ] **Step 1: Write the failing test**

```python
from app.work_packets import build_work_packet


def test_build_work_packet_groups_evidence_and_sets_conflict_status():
    packet = build_work_packet(
        reply="Pipeline is $8.7M, but two systems disagree on active deal count.",
        tool_calls=[{"name": "query_sql", "args": {"query": "pipeline"}}],
        mcp_results=[
            {
                "service": "sql",
                "summary": "SQL pipeline snapshot",
                "metrics": {"total_pipeline_value": 8700000, "active_deals_count": 9},
            },
            {
                "service": "analytics",
                "summary": "Analytics pipeline snapshot",
                "kpi_cards": [{"name": "Active Deals", "value": "42", "change": "+5", "period": "30d", "status": "up", "target": "40", "target_status": "met"}],
            },
        ],
    )

    assert packet["answer"]["summary"] == "Pipeline is $8.7M, but two systems disagree on active deal count."
    assert packet["reconciliation"]["status"] == "conflicting"
    assert packet["reconciliation"]["source_count"] == 2
    assert len(packet["evidence"]) == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/unit/test_work_packets.py::test_build_work_packet_groups_evidence_and_sets_conflict_status -v`
Expected: FAIL with `ModuleNotFoundError` or `cannot import name 'build_work_packet'`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from typing import Any


def _result_title(result: dict[str, Any]) -> str:
    service = str(result.get("service") or "source")
    return service.replace("_", " ").title()


def _extract_signals(result: dict[str, Any]) -> list[str]:
    signals: list[str] = []
    metrics = result.get("metrics") or {}
    if isinstance(metrics, dict) and "active_deals_count" in metrics:
        signals.append(f"active_deals_count:{metrics['active_deals_count']}")
    cards = result.get("kpi_cards") or []
    for card in cards if isinstance(cards, list) else []:
        if isinstance(card, dict) and card.get("name") == "Active Deals":
            signals.append(f"active_deals_count:{card.get('value')}")
    return signals


def build_work_packet(*, reply: str, tool_calls: list[dict[str, Any]], mcp_results: list[dict[str, Any]]) -> dict[str, Any]:
    evidence = [
        {
            "source": str(result.get("service") or "unknown"),
            "title": _result_title(result),
            "summary": str(result.get("summary") or "Data retrieved"),
            "signals": _extract_signals(result),
            "raw": result,
        }
        for result in mcp_results
    ]
    statuses = {tuple(item["signals"]) for item in evidence if item["signals"]}
    reconciliation_status = "conflicting" if len(statuses) > 1 else "confirmed"
    return {
        "answer": {"summary": reply},
        "reconciliation": {
            "status": reconciliation_status,
            "source_count": len(evidence),
            "notes": [],
        },
        "evidence": evidence,
        "suggested_actions": [],
        "suggested_exports": ["pdf", "docx", "xlsx"],
        "tool_calls": tool_calls,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/unit/test_work_packets.py::test_build_work_packet_groups_evidence_and_sets_conflict_status -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/work_packets.py tests/unit/test_work_packets.py
git commit -m "feat: add work packet builder foundation"
```

## Task 2: Expand Normalization and Reconciliation Rules

**Files:**
- Modify: `orchestrator/app/work_packets.py`
- Modify: `tests/unit/test_work_packets.py`

- [ ] **Step 1: Write the failing tests**

```python
from app.work_packets import build_work_packet


def test_build_work_packet_marks_partial_when_only_one_source_returns_evidence():
    packet = build_work_packet(
        reply="I found one supporting source.",
        tool_calls=[],
        mcp_results=[{"service": "mail", "summary": "Found 3 emails", "messages": [{"subject": "Board update", "from": "ceo@example.com"}]}],
    )

    assert packet["reconciliation"]["status"] == "partial"


def test_build_work_packet_collects_export_and_action_suggestions_from_documents():
    packet = build_work_packet(
        reply="Draft board briefing ready.",
        tool_calls=[{"name": "query_document_generation", "args": {"query": "board briefing"}}],
        mcp_results=[
            {
                "service": "document_generation",
                "summary": "Generated board briefing",
                "generated_documents": [{"title": "Board Briefing", "status": "draft"}],
            }
        ],
    )

    assert "pdf" in packet["suggested_exports"]
    assert packet["suggested_actions"][0]["type"] == "review_document"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/unit/test_work_packets.py -k "partial or collects_export" -v`
Expected: FAIL because `build_work_packet()` currently only returns `confirmed` or `conflicting` and no action suggestions.

- [ ] **Step 3: Write minimal implementation**

```python
def _normalize_evidence(result: dict[str, Any]) -> dict[str, Any]:
    messages = result.get("messages") if isinstance(result.get("messages"), list) else []
    files = result.get("files") if isinstance(result.get("files"), list) else []
    documents = result.get("generated_documents") if isinstance(result.get("generated_documents"), list) else []
    snippets: list[str] = []
    if messages:
        snippets.append(f"{len(messages)} email(s)")
    if files:
        snippets.append(f"{len(files)} file(s)")
    if documents:
        snippets.append(f"{len(documents)} generated document(s)")
    return {
        "source": str(result.get("service") or "unknown"),
        "title": _result_title(result),
        "summary": str(result.get("summary") or "Data retrieved"),
        "signals": _extract_signals(result),
        "snippets": snippets,
        "raw": result,
    }


def _reconciliation_status(evidence: list[dict[str, Any]]) -> str:
    populated = [item for item in evidence if item.get("signals") or item.get("snippets")]
    if len(populated) <= 1:
        return "partial"
    statuses = {tuple(item.get("signals", [])) for item in populated if item.get("signals")}
    return "conflicting" if len(statuses) > 1 else "confirmed"


def _suggested_actions(mcp_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    for result in mcp_results:
        docs = result.get("generated_documents")
        if isinstance(docs, list) and docs:
            title = str((docs[0] or {}).get("title") or "Generated document")
            return [{"type": "review_document", "label": f"Review {title}"}]
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_work_packets.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/work_packets.py tests/unit/test_work_packets.py
git commit -m "feat: add reconciliation states for work packets"
```

## Task 3: Thread `work_packet` Through Chat Responses

**Files:**
- Modify: `orchestrator/app/main.py`
- Modify: `tests/smoke/test_orchestrator.py`

- [ ] **Step 1: Write the failing smoke assertion**

```python
@pytest.mark.asyncio
async def test_chat_with_tool_calls_includes_work_packet():
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"{_base_url()}/chat",
            json={"message": "Show me the sales pipeline", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        data = _extract_sse_payload(resp)
        assert "work_packet" in data
        assert "answer" in data["work_packet"]
        assert "reconciliation" in data["work_packet"]
        assert "evidence" in data["work_packet"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/smoke/test_orchestrator.py::test_chat_with_tool_calls_includes_work_packet -v`
Expected: FAIL because the SSE `done` payload does not include `work_packet`.

- [ ] **Step 3: Write minimal implementation**

```python
from app.work_packets import build_work_packet


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    mcp_results: list[dict[str, Any]] = Field(default_factory=list)
    work_packet: dict[str, Any] | None = None


def _final_chat_payload(reply: str, tool_calls: list[dict[str, Any]], mcp_results: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "reply": reply,
        "tool_calls": tool_calls,
        "mcp_results": mcp_results,
        "work_packet": build_work_packet(reply=reply, tool_calls=tool_calls, mcp_results=mcp_results),
    }


# In both SSE completion paths:
yield _sse({"type": "done", **_final_chat_payload(full_reply, tool_calls_log, mcp_results_log)})


# In _collect_batch():
return ChatResponse(
    reply=reply or "No response",
    tool_calls=tool_calls,
    mcp_results=mcp_results,
    work_packet=build_work_packet(reply=reply or "No response", tool_calls=tool_calls, mcp_results=mcp_results),
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/unit/test_work_packets.py tests/smoke/test_orchestrator.py::test_chat_with_tool_calls_includes_work_packet -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/main.py tests/smoke/test_orchestrator.py
git commit -m "feat: return work packets from chat responses"
```

## Task 4: Document the New API Contract

**Files:**
- Modify: `orchestrator/openapi.yaml`

- [ ] **Step 1: Write the failing contract check**

```python
@pytest.mark.asyncio
async def test_openapi_schema_mentions_work_packet():
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{_base_url()}/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        chat_response = schema["components"]["schemas"]["ChatResponse"]
        assert "work_packet" in chat_response["properties"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/smoke/test_orchestrator.py::test_openapi_schema_mentions_work_packet -v`
Expected: FAIL because `ChatResponse` does not yet declare `work_packet`.

- [ ] **Step 3: Write minimal implementation**

```yaml
ChatResponse:
  type: object
  required: [reply]
  properties:
    reply:
      type: string
    tool_calls:
      type: array
      items:
        type: object
    mcp_results:
      type: array
      items:
        type: object
    work_packet:
      type: object
      properties:
        answer:
          type: object
          properties:
            summary:
              type: string
        reconciliation:
          type: object
          properties:
            status:
              type: string
              enum: [confirmed, partial, conflicting, inferred]
            source_count:
              type: integer
        evidence:
          type: array
          items:
            type: object
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/smoke/test_orchestrator.py::test_openapi_schema_mentions_work_packet -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add orchestrator/openapi.yaml tests/smoke/test_orchestrator.py
git commit -m "docs: publish work packet chat schema"
```

## Task 5: Add UI Types and a Focused Work Packet Renderer

**Files:**
- Create: `web_ui/src/WorkPacketPanel.tsx`
- Modify: `web_ui/src/Cards.tsx`

- [ ] **Step 1: Write the failing UI type and renderer task**

```tsx
export type WorkPacket = {
  answer?: { summary?: string }
  reconciliation?: { status?: 'confirmed' | 'partial' | 'conflicting' | 'inferred'; source_count?: number; notes?: string[] }
  evidence?: Array<{ source: string; title: string; summary: string; snippets?: string[] }>
  suggested_actions?: Array<{ type: string; label: string }>
  suggested_exports?: string[]
}

export function WorkPacketPanel({ packet }: { packet: WorkPacket }) {
  return <section className="work-packet-panel">{packet.answer?.summary}</section>
}
```

Run: `npm run build`
Expected: FAIL because `WorkPacketPanel.tsx` and the new `work_packet` type are not yet wired into the app.

- [ ] **Step 2: Add the types to `Cards.tsx`**

```tsx
export type WorkPacketEvidence = {
  source: string
  title: string
  summary: string
  snippets?: string[]
}

export type WorkPacket = {
  answer?: { summary?: string }
  reconciliation?: { status?: 'confirmed' | 'partial' | 'conflicting' | 'inferred'; source_count?: number; notes?: string[] }
  evidence?: WorkPacketEvidence[]
  suggested_actions?: Array<{ type: string; label: string }>
  suggested_exports?: string[]
}

export type ChatResponse = {
  reply: string
  tool_calls?: ToolCall[]
  mcp_results?: McpResult[]
  work_packet?: WorkPacket
}
```

- [ ] **Step 3: Create the minimal renderer**

```tsx
import type { WorkPacket } from './Cards'

const STATUS_LABELS = {
  confirmed: 'Confirmed across sources',
  partial: 'Partial evidence',
  conflicting: 'Conflicting evidence',
  inferred: 'Inference used',
} as const

export function WorkPacketPanel({ packet }: { packet: WorkPacket }) {
  return (
    <section className="result-card">
      <div className="result-card-header">
        <strong>Work Packet</strong>
        <span>{STATUS_LABELS[packet.reconciliation?.status ?? 'partial']}</span>
      </div>
      <p>{packet.answer?.summary}</p>
      <div className="result-grid">
        {(packet.evidence || []).map(item => (
          <article key={`${item.source}-${item.title}`} className="mini-card">
            <strong>{item.title}</strong>
            <p>{item.summary}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
```

- [ ] **Step 4: Run build to verify it passes**

Run: `npm run build`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web_ui/src/Cards.tsx web_ui/src/WorkPacketPanel.tsx
git commit -m "feat: add work packet UI types and panel"
```

## Task 6: Render Work Packets in Chat Without Removing Existing Result Decks

**Files:**
- Modify: `web_ui/src/App.tsx`

- [ ] **Step 1: Write the failing integration step**

```tsx
import { WorkPacketPanel } from './WorkPacketPanel'

// Inside the assistant message render:
{msg.data?.work_packet && <WorkPacketPanel packet={msg.data.work_packet} />}
```

Run: `npm run build`
Expected: FAIL until `App.tsx` imports and renders the new component in the assistant message path.

- [ ] **Step 2: Write minimal implementation**

```tsx
import { ResultDeck, ToolBadge, LiveToolBadge, type ChatResponse } from './Cards'
import { WorkPacketPanel } from './WorkPacketPanel'

// In the assistant message block, before tool badges/results:
{msg.data?.work_packet && (
  <div className="message-section">
    <WorkPacketPanel packet={msg.data.work_packet} />
  </div>
)}
```

- [ ] **Step 3: Preserve the current detailed decks**

```tsx
{msg.data?.tool_calls && msg.data.tool_calls.length > 0 && (
  <div className="tool-badges">
    {msg.data.tool_calls.map((tc, i) => (
      <ToolBadge key={`${tc.name}-${i}`} name={tc.name} />
    ))}
  </div>
)}

{msg.data?.mcp_results && msg.data.mcp_results.length > 0 && (
  <div className="result-decks">
    {msg.data.mcp_results.map((r, i) => <ResultDeck key={i} result={r} />)}
  </div>
)}
```

- [ ] **Step 4: Run build and smoke verification**

Run: `npm run build`
Expected: PASS

Run: `python3 -m pytest tests/unit/test_work_packets.py tests/smoke/test_orchestrator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add web_ui/src/App.tsx
git commit -m "feat: render work packets in chat"
```

## Task 7: Final Verification and Docs Note

**Files:**
- Modify: `docs/FEATURES.md`

- [ ] **Step 1: Add the product note**

```md
### Evidence-First Work Packets
- Chat responses now include a structured work packet with answer summary, reconciliation status, evidence by source, suggested exports, and suggested next actions.
- Work packets appear alongside existing detailed result decks so users can scan the summary first, then inspect raw source results.
```

- [ ] **Step 2: Run verification**

Run: `python3 -m pytest tests/unit/test_work_packets.py tests/smoke/test_orchestrator.py -v`
Expected: PASS

Run: `npm run build`
Expected: PASS

- [ ] **Step 3: Manually verify the UX**

Run: `docker compose up --build`
Expected: Orchestrator on `http://localhost:8000`, UI on `http://localhost:5173`

Manual check:
- Ask `Show me the sales pipeline`
- Confirm the assistant response shows:
  - work packet summary
  - reconciliation status
  - evidence cards
  - existing tool badges and result decks

- [ ] **Step 4: Commit**

```bash
git add docs/FEATURES.md
git commit -m "docs: describe work packet responses"
```

- [ ] **Step 5: Stop here and split the next work into separate plans**

Next plans:
- governed action lifecycle and approval routing
- persistent workspace session UX
- artifact generation from work packets instead of ad hoc export payloads

## Self-Review

- Spec coverage:
  - `evidence reconciliation`: covered by Tasks 1-4
  - `work packets`: covered by Tasks 1-6
  - `artifact/export consistency`: partially covered by packet export suggestions in Tasks 1-6; full artifact unification intentionally deferred
  - `governed actions`: intentionally deferred to a separate plan after this foundation ships
  - `workspace escalation`: intentionally deferred to a separate plan after this foundation ships
- Placeholder scan: no `TODO`, `TBD`, or "implement later" placeholders remain in the tasks above.
- Type consistency: the plan uses a single `work_packet` field name and a fixed reconciliation enum of `confirmed | partial | conflicting | inferred` across backend, schema, and UI.
