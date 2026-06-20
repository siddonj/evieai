import type { WorkPacket } from './Cards'

const STATUS_LABELS = {
  confirmed: 'Confirmed across sources',
  partial: 'Partial evidence',
  conflicting: 'Conflicting evidence',
  inferred: 'Inference used',
} as const

export function WorkPacketPanel({ packet }: { packet: WorkPacket }) {
  const status = packet.reconciliation?.status
  const sourceCount = packet.reconciliation?.source_count ?? packet.evidence?.length ?? 0
  const statusLabel = status && status in STATUS_LABELS
    ? STATUS_LABELS[status as keyof typeof STATUS_LABELS]
    : STATUS_LABELS.partial

  return (
    <section className="result-card">
      <div className="result-card-header">
        <div className="result-card-heading">
          <strong>Work packet</strong>
          <span>{statusLabel}</span>
        </div>
        <span className="workflow-pill inferred">{sourceCount} source{sourceCount === 1 ? '' : 's'}</span>
      </div>
      {packet.answer?.summary ? <p className="result-card-summary">{packet.answer.summary}</p> : null}
      <div className="result-grid">
        {(packet.evidence || []).map((item, index) => (
          <article key={`${item.source}-${item.title}-${index}`} className="mini-card">
            <span>{item.source}</span>
            <strong>{item.title}</strong>
            <p>{item.summary}</p>
          </article>
        ))}
      </div>
      {packet.reconciliation?.notes?.length ? (
        <div className="result-note-row">
          {packet.reconciliation.notes.map((note, index) => (
            <span key={`${note}-${index}`} className="result-note">
              {note}
            </span>
          ))}
        </div>
      ) : null}
    </section>
  )
}
