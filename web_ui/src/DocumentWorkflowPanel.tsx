import type { DocumentAction } from './Cards'

const STATUS_LABELS: Record<DocumentAction['status'], string> = {
  draft: 'Draft ready',
  approved: 'Approved for finalization',
  executed: 'Finalized',
  blocked: 'Approval required',
}

export function DocumentWorkflowPanel({ action }: { action: DocumentAction }) {
  return (
    <section className="result-card">
      <div className="result-card-header">
        <strong>{action.title}</strong>
        <span>{STATUS_LABELS[action.status] ?? action.status}</span>
      </div>
      <p>{action.document_type.split('_').join(' ')}</p>
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
    </section>
  )
}
