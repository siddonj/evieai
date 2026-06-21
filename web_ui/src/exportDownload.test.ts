import test from 'node:test'
import assert from 'node:assert/strict'

import { downloadBlob, downloadExportResponse, filenameFromDisposition } from './exportDownload.js'

test('filenameFromDisposition falls back cleanly when no filename exists', () => {
  assert.equal(filenameFromDisposition(null, 'fallback.pdf'), 'fallback.pdf')
  assert.equal(filenameFromDisposition('attachment; filename="report.pdf"', 'fallback.pdf'), 'report.pdf')
})

test('downloadBlob keeps the object URL alive until after the click', async () => {
  const appended: any[] = []
  const removed: any[] = []
  let revokedUrl: string | null = null
  let timeoutCallback: (() => void) | null = null
  let clickCount = 0

  const originalDocument = globalThis.document
  const originalUrl = globalThis.URL
  const originalSetTimeout = globalThis.setTimeout

  try {
    globalThis.document = {
      body: {
        appendChild(node: any) {
          appended.push(node)
        },
        removeChild(node: any) {
          removed.push(node)
        },
      },
      createElement(tag: string) {
        assert.equal(tag, 'a')
        return {
          style: {},
          click() {
            clickCount += 1
          },
        } as any
      },
    } as Document
    globalThis.URL = {
      createObjectURL() {
        return 'blob:download-target'
      },
      revokeObjectURL(url: string) {
        revokedUrl = url
      },
    } as typeof URL
    globalThis.setTimeout = ((callback: (...args: any[]) => void) => {
      timeoutCallback = () => callback()
      return 1 as unknown as ReturnType<typeof setTimeout>
    }) as typeof setTimeout

    await downloadBlob(new Blob(['hello world']), 'report.pdf')

    assert.equal(clickCount, 1)
    assert.equal(appended.length, 1)
    assert.equal(removed.length, 0)
    assert.equal(revokedUrl, null)

    timeoutCallback?.()

    assert.equal(removed.length, 1)
    assert.equal(revokedUrl, 'blob:download-target')
  } finally {
    globalThis.document = originalDocument
    globalThis.URL = originalUrl
    globalThis.setTimeout = originalSetTimeout
  }
})

test('downloadExportResponse rejects non-ok export responses', async () => {
  await assert.rejects(
    downloadExportResponse(
      new Response('missing', { status: 404, headers: { 'content-type': 'application/json' } }),
      'report.pdf',
    ),
    /Export failed \(404\):/,
  )
})

test('downloadExportResponse uses the exported filename and downloads the blob', async () => {
  const appended: any[] = []
  const removed: any[] = []
  let revokedUrl: string | null = null
  let timeoutCallback: (() => void) | null = null
  let clickedFilename: string | null = null

  const originalDocument = globalThis.document
  const originalUrl = globalThis.URL
  const originalSetTimeout = globalThis.setTimeout

  try {
    globalThis.document = {
      body: {
        appendChild(node: any) {
          appended.push(node)
        },
        removeChild(node: any) {
          removed.push(node)
        },
      },
      createElement() {
        return {
          style: {},
          click() {},
          set download(value: string) {
            clickedFilename = value
          },
        } as any
      },
    } as Document
    globalThis.URL = {
      createObjectURL() {
        return 'blob:export-target'
      },
      revokeObjectURL(url: string) {
        revokedUrl = url
      },
    } as typeof URL
    globalThis.setTimeout = ((callback: (...args: any[]) => void) => {
      timeoutCallback = () => callback()
      return 1 as unknown as ReturnType<typeof setTimeout>
    }) as typeof setTimeout

    await downloadExportResponse(
      new Response('fake pdf', {
        status: 200,
        headers: {
          'content-type': 'application/pdf',
          'content-disposition': 'attachment; filename="board-report.pdf"',
        },
      }),
      'fallback.pdf',
    )

    assert.equal(appended.length, 1)
    assert.equal(removed.length, 0)
    assert.equal(revokedUrl, null)
    assert.equal(clickedFilename, 'board-report.pdf')

    timeoutCallback?.()

    assert.equal(removed.length, 1)
    assert.equal(revokedUrl, 'blob:export-target')
  } finally {
    globalThis.document = originalDocument
    globalThis.URL = originalUrl
    globalThis.setTimeout = originalSetTimeout
  }
})
