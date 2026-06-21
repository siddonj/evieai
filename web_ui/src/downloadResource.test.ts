import test from 'node:test'
import assert from 'node:assert/strict'

import { downloadResource } from './downloadResource.js'

test('downloadResource keeps the blob URL alive until after the click', async () => {
  const appended: any[] = []
  const removed: any[] = []
  let revokedUrl: string | null = null
  let timeoutCallback: (() => void) | null = null
  let clickCount = 0

  const originalFetch = globalThis.fetch
  const originalDocument = globalThis.document
  const originalUrl = globalThis.URL
  const originalWindow = globalThis.window
  const originalSetTimeout = globalThis.setTimeout

  try {
    globalThis.fetch = async () => ({
      ok: true,
      blob: async () => new Blob(['hello world']),
    } as Response)
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
    globalThis.window = {
      open() {
        return null
      },
    } as Window & typeof globalThis
    globalThis.setTimeout = ((callback: (...args: any[]) => void) => {
      timeoutCallback = () => callback()
      return 1 as unknown as ReturnType<typeof setTimeout>
    }) as typeof setTimeout

    await downloadResource('https://example.com/report.pdf', 'report.pdf')

    assert.equal(clickCount, 1)
    assert.equal(appended.length, 1)
    assert.equal(removed.length, 0)
    assert.equal(revokedUrl, null)

    timeoutCallback?.()

    assert.equal(removed.length, 1)
    assert.equal(revokedUrl, 'blob:download-target')
  } finally {
    globalThis.fetch = originalFetch
    globalThis.document = originalDocument
    globalThis.URL = originalUrl
    globalThis.window = originalWindow
    globalThis.setTimeout = originalSetTimeout
  }
})
