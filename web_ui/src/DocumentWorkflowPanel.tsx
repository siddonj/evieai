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
}

export function DocumentWorkflowPanel({
  action,
  orchestratorUrl,
  userId,
  authHeader,
  workPacketId,
  sourceSummary,
  onActionChange,
}: DocumentWorkflowPanelProps) {
  const [destinationType, setDestinationType] = useState(action.destination_type || 'onedrive')
  const [destinationRef, setDestinationRef] = useState(action.destination_ref || '')
  const [selectedFormats, setSelectedFormats] = useState<string[]>(action.output_formats?.length ? action.output_formats : ['pdf', 'docx'])
  const [busy, setBusy] = useState<'create' | 'approve' | 'finalize' | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    setDestinationType(action.destination_type || 'onedrive')
    setDestinationRef(action.destination_ref || '')
    setSelectedFormats(action.output_formats?.length ? action.output_formats : ['pdf', 'docx'])
  }, [action])

  const isSuggested = action.id < 0
  const canApprove = action.id > 0 && (action.status === 'draft' || action.status === 'blocked')
  const canFinalize = action.id > 0 && action.status === 'approved'

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
        </div>
      )}
      {action.artifacts?.length ? (
        <div className="result-grid">
          {action.artifacts.map((artifact, index) => (
            <article key={`${artifact.file_name || artifact.format || 'artifact'}-${index}`} className="mini-card">
              <span>{artifact.format || 'artifact'}</span>
              <strong>{artifact.file_name || 'Generated file'}</strong>
              <p>{artifact.storage_ref || 'Stored'}</p>
            </article>
          ))}
        </div>
      ) : null}
      {error ? <p>{error}</p> : null}
    </section>
  )
}
