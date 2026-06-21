export function filenameFromDisposition(disposition: string | null, fallback: string): string {
  const match = disposition?.match(/filename="?([^";]+)"?/)
  return match ? match[1] : fallback
}

export async function downloadBlob(blob: Blob, filename: string) {
  const blobUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = blobUrl
  anchor.download = filename
  anchor.style.display = 'none'
  document.body.appendChild(anchor)
  anchor.click()
  setTimeout(() => {
    document.body.removeChild(anchor)
    URL.revokeObjectURL(blobUrl)
  }, 1000)
}

export async function downloadExportResponse(res: Response, fallbackFilename: string) {
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`Export failed (${res.status}): ${text.slice(0, 300)}`)
  }

  const contentType = res.headers.get('content-type') || ''
  if (!contentType.includes('application/') && !contentType.includes('octet-stream')) {
    const text = await res.text().catch(() => '')
    throw new Error(
      `Export returned unexpected content type "${contentType}".${text ? ` Response: ${text.slice(0, 200)}` : ''}`,
    )
  }

  const blob = await res.blob()
  const filename = filenameFromDisposition(res.headers.get('content-disposition'), fallbackFilename)
  await downloadBlob(blob, filename)
}

export async function downloadResource(url: string, filename: string) {
  try {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`Download failed: ${res.status}`)
    const blob = await res.blob()
    await downloadBlob(blob, filename)
  } catch {
    window.open(url, '_blank')
  }
}
