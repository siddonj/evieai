import { useEffect, useState } from 'react'
import type { DocumentAction } from './Cards'

const STATUS_LABELS: Record<DocumentAction['status'], string> = {
  draft: 'Draft ready',
  approved: 'Approved for finalization',
  executed: 'Finalized',
  blocked: 'Approval required',
}

type DocumentWorkflowPanelProps = {
  action: DocumentAction
  orchestratorUrl: string
  userId?: string
  authHeader?: string
  workPacketId: string
  sourceSummary: string
  onActionChange: (action: DocumentAction) => void
  onViewReport?: (documentActionId: number) => void
}

export function DocumentWorkflowPanel({
  action,
  orchestratorUrl,
  userId,
  authHeader,
  workPacketId,
  sourceSummary,
  onActionChange,
  onViewReport,
}: DocumentWorkflowPanelProps) {
  const [destinationType, setDestinationType] = useState(action.destination_type || 'onedrive')
  const [destinationRef, setDestinationRef] = useState(action.destination_ref || '')
  const [selectedFormats, setSelectedFormats] = useState<string[]>(action.output_formats?.length ? action.output_formats : ['pdf', 'docx'])
  const [busy, setBusy] = useState<'create' | 'approve' | 'finalize' | 'export' | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setDestinationType(action.destination_type || 'onedrive')
    setDestinationRef(action.destination_ref || '')
    setSelectedFormats(action.output_formats?.length ? action.output_formats : ['pdf', 'docx'])
  }, [action])

  const isSuggested = action.id < 0
  const canApprove = action.id > 0 && (action.status === 'draft' || action.status === 'blocked')
  const canFinalize = action.id > 0 && action.status === 'approved'
  const canExportPackage = action.id > 0 && action.status === 'executed'
  const canViewReport = action.id > 0 && action.status === 'executed'

  function toggleFormat(format: string) {
    setSelectedFormats((prev) => (
      prev.includes(format)
        ? prev.filter((item) => item !== format)
        : [...prev, format]
    ))
  }

  async function handleCreateDraft() {
    if (!userId || busy) return
    setBusy('create')
    setError('')
    try {
      const res = await fetch(`${orchestratorUrl}/document-actions/draft`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: JSON.stringify({
          user_id: userId,
          work_packet_id: workPacketId,
          document_type: action.document_type,
          title: action.title,
          source_summary: sourceSummary,
        }),
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const created = await res.json() as DocumentAction
      onActionChange(created)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create draft')
    } finally {
      setBusy(null)
    }
  }

  async function handleApprove() {
    if (busy || !destinationRef.trim() || selectedFormats.length === 0) return
    setBusy('approve')
    setError('')
    try {
      const res = await fetch(`${orchestratorUrl}/document-actions/${action.id}/approve`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: JSON.stringify({
          destination_type: destinationType,
          destination_ref: destinationRef.trim(),
          output_formats: selectedFormats,
        }),
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const approved = await res.json() as DocumentAction
      onActionChange(approved)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not approve draft')
    } finally {
      setBusy(null)
    }
  }

  async function handleFinalize() {
    if (busy) return
    setBusy('finalize')
    setError('')
    try {
      const res = await fetch(`${orchestratorUrl}/document-actions/${action.id}/finalize`, {
        method: 'POST',
        headers: authHeader ? { Authorization: authHeader } : undefined,
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const finalized = await res.json() as {
        document_action?: DocumentAction
      }
      if (!finalized.document_action) {
        throw new Error('Missing finalized document action')
      }
      onActionChange(finalized.document_action)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not finalize draft')
    } finally {
      setBusy(null)
    }
  }

  async function handleExportPackage() {
    if (busy) return
    setBusy('export')
    setError('')
    try {
      const res = await fetch(`${orchestratorUrl}/document-actions/${action.id}/export-package`, {
        method: 'POST',
        headers: authHeader ? { Authorization: authHeader } : undefined,
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const exported = await res.json() as {
        document_action?: DocumentAction
      }
      if (!exported.document_action) {
        throw new Error('Missing export package document action')
      }
      onActionChange(exported.document_action)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not export package')
    } finally {
      setBusy(null)
    }
  }

  return (
    <section
      className="result-card"
      onClick={isSuggested ? handleCreateDraft : undefined}
      role={isSuggested ? 'button' : undefined}
      tabIndex={isSuggested ? 0 : undefined}
      onKeyDown={isSuggested ? (event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          void handleCreateDraft()
        }
      } : undefined}
    >
      <div className="result-card-header">
        <strong>{action.title}</strong>
        <span>{STATUS_LABELS[action.status] ?? action.status}</span>
      </div>
      <p>{action.document_type.split('_').join(' ')}</p>
      {isSuggested && (
        <div className="tool-bar">
          <button className="status-btn" onClick={(event) => {
            event.stopPropagation()
            void handleCreateDraft()
          }} disabled={busy === 'create' || !userId}>
            {busy === 'create' ? 'Creating…' : 'Create Draft'}
          </button>
        </div>
      )}
      {!isSuggested && (
        <div className="result-grid">
          <article className="mini-card">
            <span>Destination</span>
            <strong>{destinationType}</strong>
            <input
              value={destinationRef}
              onChange={(event) => setDestinationRef(event.target.value)}
              placeholder="Reports/Board"
              disabled={action.status === 'approved' || action.status === 'executed' || busy !== null}
            />
          </article>
          <article className="mini-card">
            <span>Formats</span>
            <strong>{selectedFormats.join(', ') || 'Select formats'}</strong>
            <div className="tool-bar">
              {['pdf', 'docx', 'xlsx'].map((format) => (
                <button
                  key={format}
                  className="status-btn"
                  onClick={(event) => {
                    event.stopPropagation()
                    toggleFormat(format)
                  }}
                  disabled={action.status === 'approved' || action.status === 'executed' || busy !== null}
                >
                  {selectedFormats.includes(format) ? `✓ ${format}` : format}
                </button>
              ))}
            </div>
          </article>
        </div>
      )}
      {(action.destination_type || action.output_formats?.length) && (
        <div className="result-grid">
          {action.destination_type && (
            <article className="mini-card">
              <span>Destination</span>
              <strong>{action.destination_type}</strong>
              <p>{action.destination_ref || 'Pending selection'}</p>
            </article>
          )}
          {action.output_formats?.length ? (
            <article className="mini-card">
              <span>Formats</span>
              <strong>{action.output_formats.join(', ')}</strong>
              <p>{action.artifacts?.length ? `${action.artifacts.length} artifact(s) recorded` : 'Awaiting finalization'}</p>
            </article>
          ) : null}
        </div>
      )}
      {!isSuggested && (
        <div className="tool-bar">
          <button
            className="status-btn"
            onClick={(event) => {
              event.stopPropagation()
              void handleApprove()
            }}
            disabled={!canApprove || !destinationRef.trim() || selectedFormats.length === 0 || busy !== null}
          >
            {busy === 'approve' ? 'Approving…' : 'Approve'}
          </button>
          <button
            className="status-btn"
            onClick={(event) => {
              event.stopPropagation()
              void handleFinalize()
            }}
            disabled={!canFinalize || busy !== null}
          >
            {busy === 'finalize' ? 'Finalizing…' : 'Finalize'}
          </button>
          <button
            className="status-btn"
            onClick={(event) => {
              event.stopPropagation()
              void handleExportPackage()
            }}
            disabled={!canExportPackage || busy !== null}
          >
            {busy === 'export' ? 'Exporting…' : 'Export package'}
          </button>
          <button
            className="status-btn"
            onClick={(event) => {
              event.stopPropagation()
              if (canViewReport) {
                onViewReport?.(action.id)
              }
            }}
            disabled={!canViewReport}
          >
            View report
          </button>
        </div>
      )}
      {action.artifacts?.length ? (
        <div className="result-grid">
          {action.artifacts.map((artifact, index) => (
            <article key={`${artifact.file_name || artifact.format || 'artifact'}-${index}`} className="mini-card">
              <span>{artifact.format || 'artifact'}</span>
              <strong>{artifact.file_name || 'Generated file'}</strong>
              <p>{artifact.blob_url || artifact.storage_ref || 'Stored'}</p>
            </article>
          ))}
        </div>
      ) : null}
      {action.announcement?.action_id ? (
        <div className="result-grid">
          <article className="mini-card">
            <span>Announcement</span>
            <strong>{action.announcement.status || 'queued'}</strong>
            <p>{action.announcement.result?.message || action.announcement.action_id}</p>
          </article>
        </div>
      ) : null}
      {action.export_package?.status ? (
        <div className="result-grid">
          <article className="mini-card">
            <span>Export package</span>
            <strong>{action.export_package.status}</strong>
            <p>{action.export_package.result?.message || `${action.export_package.artifacts?.length || 0} export artifact(s)`}</p>
          </article>
          {action.export_package.artifacts?.length ? (
            <article className="mini-card">
              <span>Formats</span>
              <strong>{action.export_package.artifacts.map((artifact) => artifact.format).filter(Boolean).join(', ')}</strong>
              <p>{action.export_package.action_id || 'Tracked export workflow'}</p>
            </article>
          ) : null}
        </div>
      ) : null}
      {error ? <p>{error}</p> : null}
    </section>
  )
}
