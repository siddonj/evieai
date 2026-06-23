# Demo Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current chat product into a stronger live demo by adding guided demo mode, clearer source grounding, and a polished export path.

**Architecture:** Keep the existing orchestrator and chat shell. Add a small frontend demo-state layer for presenter flow, extend chat responses with structured grounding metadata, and reuse the existing document workflow/export state to show the final artifact more clearly. The changes should be additive and reversible, not a rewrite.

**Tech Stack:** React + TypeScript + Vite, FastAPI + Pydantic, SSE chat stream, pytest, HTTPX. Add Vitest only for pure frontend helper logic.

---

## File Map

- `web_ui/src/App.tsx` owns the chat shell, presenter flow, and answer rendering.
- `web_ui/src/Cards.tsx` owns typed chat payload rendering and follow-up/export cards.
- `web_ui/src/DocumentWorkflowPanel.tsx` owns governed export actions and artifact state.
- `web_ui/src/styles.css` owns the demo presentation polish.
- `web_ui/src/demoMode.ts` will hold demo scenarios and prompt sequencing helpers.
- `web_ui/src/demoMode.test.ts` will cover the pure demo-mode helper logic.
- `web_ui/package.json` will add a `test` script and Vitest dev dependency.
- `orchestrator/app/main.py` owns chat response assembly and SSE payload shape.
- `orchestrator/app/demo_metadata.py` will derive demo-friendly metadata from the chat result.
- `orchestrator/app/work_packets.py` may need a small extension if the demo metadata should be derived from the work packet rather than duplicated.
- `tests/smoke/test_orchestrator.py` will verify the chat payload and export path end to end.

## Task 1: Add Guided Demo Mode

**Files:**
- Create: `web_ui/src/demoMode.ts`
- Create: `web_ui/src/demoMode.test.ts`
- Modify: `web_ui/package.json`
- Modify: `web_ui/src/App.tsx`
- Modify: `web_ui/src/styles.css`

- [ ] **Step 1: Write the failing test**

```ts
import { describe, expect, it } from 'vitest'
import { DEMO_SCENARIOS, getNextDemoStep } from './demoMode'

describe('demoMode', () => {
  it('defines a product-demo scenario for multi-source chat with export', () => {
    expect(DEMO_SCENARIOS[0].id).toBe('multi-source-chat-export')
    expect(DEMO_SCENARIOS[0].title).toBe('Multi-source chat with export')
    expect(DEMO_SCENARIOS[0].prompts).toEqual([
      'Show me portfolio performance for this account.',
      'What open work orders need attention right now?',
      'Export this answer to PDF and Excel.',
    ])
  })

  it('advances through the guided sequence one step at a time', () => {
    expect(getNextDemoStep(0)).toBe(1)
    expect(getNextDemoStep(1)).toBe(2)
    expect(getNextDemoStep(2)).toBe(2)
  })
})
```

- [ ] **Step 2: Run the test and confirm it fails**

Run:
```bash
cd web_ui
npm test -- --run src/demoMode.test.ts
```

Expected: fail because `demoMode.ts` and the `test` script do not exist yet.

- [ ] **Step 3: Implement the minimal demo-mode layer**

```ts
export type DemoScenario = {
  id: string
  title: string
  description: string
  prompts: string[]
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: 'multi-source-chat-export',
    title: 'Multi-source chat with export',
    description: 'A guided product demo that shows routing, grounded answers, and export.',
    prompts: [
      'Show me portfolio performance for this account.',
      'What open work orders need attention right now?',
      'Export this answer to PDF and Excel.',
    ],
  },
]

export function getNextDemoStep(stepIndex: number): number {
  return Math.min(stepIndex + 1, DEMO_SCENARIOS[0].prompts.length - 1)
}
```

Wire `App.tsx` to:

- show a small demo launcher above the chat composer,
- let the user start the scenario from one click,
- expose a reset button that returns to the first prompt,
- preserve normal freeform chat when demo mode is not active.

Style the launcher so it reads like a deliberate presenter control, not a settings panel.

- [ ] **Step 4: Run the frontend checks**

Run:
```bash
cd web_ui
npm test -- --run src/demoMode.test.ts
npm run build
```

Expected: the helper test passes and the Vite build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web_ui/package.json web_ui/src/App.tsx web_ui/src/styles.css web_ui/src/demoMode.ts web_ui/src/demoMode.test.ts
git commit -m "feat: add guided demo mode"
```

## Task 2: Add Answer Grounding and Source Transparency

**Files:**
- Create: `orchestrator/app/demo_metadata.py`
- Create: `tests/unit/test_demo_metadata.py`
- Modify: `orchestrator/app/main.py`
- Modify: `orchestrator/app/work_packets.py`
- Modify: `web_ui/src/Cards.tsx`
- Modify: `web_ui/src/App.tsx`
- Modify: `tests/smoke/test_orchestrator.py`

- [ ] **Step 1: Write the failing metadata assertions**

```py
from app.demo_metadata import build_demo_metadata


def test_build_demo_metadata_marks_fallback_when_source_errors():
    metadata = build_demo_metadata(
        work_packet={
            'reconciliation': {'status': 'partial', 'source_count': 1, 'confidence': 0.42},
            'evidence': [{'source': 'sql', 'title': 'Open pipeline', 'summary': 'partial result'}],
        },
        mcp_results=[
            {'service': 'sql', 'error': 'timeout'},
        ],
    )

    assert metadata['is_demo_fallback'] is True
    assert metadata['fallback_reason'] == 'source_unavailable'
    assert metadata['confidence'] == 0.42
```

```py
@pytest.mark.asyncio
async def test_chat_batch_includes_demo_metadata():
    async with httpx.AsyncClient(timeout=45) as client:
        resp = await client.post(
            f"{_base_url()}/chat/batch",
            json={"message": "Show me the sales pipeline", "user_id": "smoke-test"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "demo_metadata" in body
        assert body["demo_metadata"]["source_class"] in {"sql", "knowledge", "documents", "memory"}
        assert isinstance(body["demo_metadata"]["confidence"], float)
        assert isinstance(body["demo_metadata"]["follow_up_suggestions"], list)
```

- [ ] **Step 2: Run the smoke test and confirm it fails**

Run:
```bash
python -m pytest tests/unit/test_demo_metadata.py -v
python -m pytest tests/smoke/test_orchestrator.py -k demo_metadata -v
```

Expected: fail because `build_demo_metadata` and the response field do not exist yet.

- [ ] **Step 3: Add the minimal backend metadata shape**

```py
class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    mcp_results: list[dict[str, Any]] = Field(default_factory=list)
    work_packet: dict[str, Any] | None = None
    document_actions: list[dict[str, Any]] = Field(default_factory=list)
    demo_metadata: dict[str, Any] | None = None
```

```py
def build_demo_metadata(work_packet: dict[str, Any], mcp_results: list[dict[str, Any]]) -> dict[str, Any]:
    reconciliation = work_packet.get('reconciliation') or {}
    evidence = work_packet.get('evidence') or []
    source_class = 'sql'
    fallback_reason = None
    if any(result.get('documents') for result in mcp_results):
        source_class = 'documents'
    elif any(result.get('messages') for result in mcp_results):
        source_class = 'memory'
    elif any(result.get('insights') for result in mcp_results):
        source_class = 'knowledge'
    elif any(result.get('error') for result in mcp_results):
        fallback_reason = 'source_unavailable'
    confidence = float(reconciliation.get('confidence') or 0.75)
    return {
        'source_class': source_class,
        'source_count': int(reconciliation.get('source_count') or len(evidence)),
        'confidence': confidence,
        'is_demo_fallback': fallback_reason is not None or confidence < 0.5,
        'fallback_reason': fallback_reason,
        'follow_up_suggestions': [
            'Show the breakdown by source.',
            'Compare the answer to open items.',
            'Export this result to PDF or Excel.',
        ],
    }
```

Use the helper in `_final_chat_payload(...)` so the SSE `done` event includes one consistent metadata object. Reuse the existing `work_packet` and `mcp_results` instead of inventing a new data path.

Update `Cards.tsx` to render the new metadata as:

- a source badge,
- a confidence indicator,
- 2-3 follow-up suggestion chips after each assistant answer.

Keep the presentation compact. The point is to make the answer feel grounded, not to add more charts.

- [ ] **Step 4: Run the backend and frontend checks**

Run:
```bash
python -m pytest tests/unit/test_demo_metadata.py -v
python -m pytest tests/smoke/test_orchestrator.py -k "chat_batch_includes_demo_metadata or chat_with_tool_calls_includes_work_packet" -v
cd web_ui
npm run build
```

Expected: the new metadata assertion passes and the frontend build still succeeds.

- [ ] **Step 5: Commit**

```bash
git add orchestrator/app/main.py orchestrator/app/work_packets.py orchestrator/app/demo_metadata.py web_ui/src/Cards.tsx web_ui/src/App.tsx tests/smoke/test_orchestrator.py
git commit -m "feat: add grounded chat metadata"
```

## Task 3: Polish Export Artifact States and Report Review

**Files:**
- Create: `web_ui/src/exportPreview.ts`
- Create: `web_ui/src/exportPreview.test.ts`
- Modify: `web_ui/src/DocumentWorkflowPanel.tsx`
- Modify: `web_ui/src/App.tsx`
- Modify: `web_ui/src/styles.css`
- Modify: `tests/smoke/test_orchestrator.py`

- [ ] **Step 1: Write the failing export-state assertion**

```ts
import { describe, expect, it } from 'vitest'
import { buildExportPreview } from './exportPreview'

describe('buildExportPreview', () => {
  it('shows a completed export package as a polished demo artifact', () => {
    expect(
      buildExportPreview({
        status: 'completed',
        artifacts: [
          { format: 'pdf', file_name: 'portfolio-summary.pdf' },
          { format: 'docx', file_name: 'portfolio-summary.docx' },
          { format: 'xlsx', file_name: 'portfolio-summary.xlsx' },
        ],
      }),
    ).toEqual({
      statusLabel: 'Completed',
      artifactCountLabel: '3 artifacts ready',
      primaryFormats: ['pdf', 'docx', 'xlsx'],
    })
  })
})
```

- [ ] **Step 2: Run the smoke test and confirm it fails or is incomplete**

Run:
```bash
cd web_ui
npm test -- --run src/exportPreview.test.ts
```

Expected: fail because `exportPreview.ts` does not exist yet.

- [ ] **Step 3: Upgrade the export presentation**

```tsx
export function buildExportPreview(packageState: {
  status?: string
  artifacts?: Array<{ format?: string; file_name?: string }>
}) {
  const artifacts = packageState.artifacts || []
  const statusLabel =
    packageState.status === 'completed'
      ? 'Completed'
      : packageState.status === 'failed'
        ? 'Failed'
        : 'In progress'
  return {
    statusLabel,
    artifactCountLabel:
      artifacts.length === 0
        ? 'Awaiting artifacts'
        : artifacts.length === 1
          ? '1 artifact ready'
          : `${artifacts.length} artifacts ready`,
    primaryFormats: artifacts.map((artifact) => artifact.format).filter(Boolean),
  }
}
```

```tsx
<article className="report-stat">
  <span>Export package</span>
  <strong>{document.export_package?.status || 'not started'}</strong>
  <p>
    {document.export_package?.artifacts?.length
      ? `${document.export_package.artifacts.length} artifact(s) ready`
      : 'PDF, DOCX, XLSX when ready'}
  </p>
</article>
```

```tsx
{(document.export_package?.artifacts || []).map((artifact, index) => (
  <article key={`export-${artifact.file_name || artifact.format || 'artifact'}-${index}`} className="mini-card">
    <span>{artifact.format || 'export'}</span>
    <strong>{artifact.file_name || 'Export package file'}</strong>
    <p>{artifact.blob_url || artifact.storage_ref || 'Stored'}</p>
  </article>
))}
```

Add a compact export-preview panel in `DocumentWorkflowPanel.tsx` so the presenter can show the output formats and state before and after finalization. Keep the same business language the report viewer uses: status, artifacts, delivery.

Style the export area so it reads like a finished deliverable:

- clear status chips,
- artifact count,
- file names or storage refs,
- obvious back-to-chat navigation.

- [ ] **Step 4: Run the full verification set**

Run:
```bash
cd web_ui
npm test -- --run src/exportPreview.test.ts
npm run build
python -m pytest tests/smoke/test_orchestrator.py -k document_workflow_export_package_endpoint -v
```

Expected: the export endpoint smoke coverage passes and the frontend build succeeds.

- [ ] **Step 5: Commit**

```bash
git add web_ui/src/DocumentWorkflowPanel.tsx web_ui/src/App.tsx web_ui/src/styles.css tests/smoke/test_orchestrator.py
git commit -m "feat: polish export artifact states"
```

## Self-Review Checklist

- The demo-mode task owns only presenter flow and prompt choreography.
- The grounding task owns only answer trust and source transparency.
- The export task owns only deliverable presentation and artifact visibility.
- The plan does not introduce a new backend subsystem.
- The frontend test runner addition is limited to pure helper logic, not a broad JS testing migration.
- The smoke tests cover the real orchestrator payloads and export endpoint.

## Exit Criteria

The plan is done when:

- the demo can be launched from a clear presenter path,
- each answer shows where it came from,
- the audience can ask a follow-up and stay in the same story,
- export feels like a real product outcome,
- the full chat/export flow passes build and smoke verification.
