# Card Export Centralization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every card-driven export and download path use one shared implementation so the export menu, file cards, and document workflow downloads behave consistently and do not produce empty or broken files.

**Architecture:** Extract the browser download logic into a single helper module that handles blob downloads, content-disposition filename extraction, and safe cleanup. Reuse that helper from the export menu, report viewer downloads, and workflow artifact downloads so all card surfaces follow the same code path. Keep the orchestrator and document-generation services unchanged unless the shared UI path exposes a real server-side defect.

**Tech Stack:** React, TypeScript, Vite, Node test runner, Fetch API, DOM blob downloads.

---

### Task 1: Build a shared export/download helper

**Files:**
- Create: `web_ui/src/exportDownload.ts`
- Modify: `web_ui/src/Cards.tsx`
- Modify: `web_ui/src/App.tsx`
- Test: `web_ui/src/exportDownload.test.ts`

- [ ] **Step 1: Write the failing test**

```ts
import test from 'node:test'
import assert from 'node:assert/strict'
import { downloadExportResponse } from './exportDownload.js'

test('downloadExportResponse waits before revoking the object URL', async () => {
  // stub fetch, document, URL, and setTimeout
  // assert the anchor is clicked before cleanup runs
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `npm test -- --run src/exportDownload.test.ts`
Expected: fail because `downloadExportResponse` does not exist yet.

- [ ] **Step 3: Write the shared helper**

```ts
export async function downloadBlob(blob: Blob, filename: string) {
  const blobUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = blobUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  setTimeout(() => {
    document.body.removeChild(anchor)
    URL.revokeObjectURL(blobUrl)
  }, 1000)
}

export function filenameFromDisposition(disposition: string | null, fallback: string) {
  const match = disposition?.match(/filename="?([^";]+)"?/)
  return match ? match[1] : fallback
}

export async function downloadExportResponse(res: Response, fallbackFilename: string) {
  if (!res.ok) throw new Error(`Export failed (${res.status})`)
  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/') && !contentType.includes('octet-stream')) {
    throw new Error(`Unexpected export content type: ${contentType}`)
  }
  const blob = await res.blob()
  const filename = filenameFromDisposition(res.headers.get('content-disposition'), fallbackFilename)
  await downloadBlob(blob, filename)
}
```

- [ ] **Step 4: Rewire the card surfaces to use the helper**

```ts
import { downloadExportResponse, downloadResource } from './exportDownload'
```

Update `ExportMenu` to call `downloadExportResponse(res, fallbackFilename)` instead of duplicating blob handling.
Keep `downloadResource(url, filename)` for raw file URLs, but make it call `downloadBlob(...)` internally.

- [ ] **Step 5: Run the test to verify it passes**

Run: `npm test -- --run src/exportDownload.test.ts`
Expected: pass.

### Task 2: Verify the shared helper compiles through the app

**Files:**
- Modify: `web_ui/src/App.tsx`
- Modify: `web_ui/src/Cards.tsx`

- [ ] **Step 1: Replace direct blob/download logic with the shared helper**

```ts
import { downloadExportResponse, downloadResource } from './exportDownload'
```

Use the shared helper everywhere a card or report view triggers a download.

- [ ] **Step 2: Run the frontend build**

Run: `npm run build`
Expected: exit 0.

- [ ] **Step 3: Sanity-check the download call sites**

Ensure the following all route through the same helper code path:
- export menu downloads
- file card downloads
- report viewer artifact downloads

### Task 3: Commit the refactor

**Files:**
- All files changed above

- [ ] **Step 1: Review the diff**

Run: `git diff -- web_ui/src/App.tsx web_ui/src/Cards.tsx web_ui/src/DocumentWorkflowPanel.tsx web_ui/src/exportDownload.ts web_ui/src/exportDownload.test.ts`

- [ ] **Step 2: Commit the verified fix**

Run:

```bash
git add web_ui/src/App.tsx web_ui/src/Cards.tsx web_ui/src/DocumentWorkflowPanel.tsx web_ui/src/exportDownload.ts web_ui/src/exportDownload.test.ts
git commit -m "fix: centralize card export downloads"
```
