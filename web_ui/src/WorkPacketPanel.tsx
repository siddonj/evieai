import type { WorkPacket } from './Cards'

const STATUS_LABELS = {
  confirmed: 'Confirmed across sources',
  partial: 'Partial evidence',
  conflicting: 'Conflicting evidence',
  inferred: 'Inference used',
} as const

export function WorkPacketPanel({ packet }: { packet: WorkPacket }) {
  const status = packet.reconciliation?.status
  const statusLabel = status && status in STATUS_LABELS
    ? STATUS_LABELS[status as keyof typeof STATUS_LABELS]
    : STATUS_LABELS.partial

  return (
    <section className="result-card">
      <div className="result-card-header">
        <strong>Work Packet</strong>
        <span>{statusLabel}</span>
      </div>
      {packet.answer?.summary ? <p>{packet.answer.summary}</p> : null}
      <div className="result-grid">
        {(packet.evidence || []).map((item, index) => (
          <article key={`${item.source}-${item.title}-${index}`} className="mini-card">
            <span>{item.source}</span>
            <strong>{item.title}</strong>
            <p>{item.summary}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
