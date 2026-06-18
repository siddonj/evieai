/* ─── Types ─────────────────────────────────────────────────────── */
import { useState } from 'react'

const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'

export type McpFile = {
  name: string
  size?: number
  lastModifiedDateTime?: string
  folder?: string
  description?: string
  category?: string
  url?: string
}

export type McpMessage = {
  subject: string
  from: string
  receivedDateTime?: string
  bodyPreview?: string
  isRead?: boolean
  importance?: string
}

export type KbDocument = {
  id?: string
  type?: string
  category?: string
  title?: string
  version?: string
  effective_date?: string
  owner?: string
  status?: string
  summary?: string
  key_points?: string[]
  related?: string[]
}

export type MemoryBookmark = {
  type: string
  name?: string
  id?: string
  reason?: string
}

export type MemorySnippet = {
  type: string
  content: string | MemoryBookmark
}

export type KpiCard = {
  name: string
  value: string
  change: string
  period: string
  status: string
  target: string
  target_status: string
}

export type TrendData = {
  metric: string
  data: Array<Record<string, any>>
  trend_direction: string
  trend_strength: string
}

export type GeneratedDocument = {
  id?: string
  type?: string
  title?: string
  generated_at?: string
  author?: string
  status?: string
  pages?: number
  word_count?: number
  sections?: Array<{
    heading: string
    content: string
    key_metrics?: Array<{ label: string; value: string; trend?: string }>
  }>
  action_items?: string[]
  tags?: string[]
}

export type SqlContact = {
  id?: number
  first_name?: string
  last_name?: string
  email?: string
  phone?: string
  company?: string
  job_title?: string
  stage?: string
  deal_value?: number
  region?: string
  owner?: string
  last_contact_date?: string
  notes?: string
}

export type SqlCompany = {
  id?: number
  name?: string
  industry?: string
  revenue_tier?: string
  employee_count?: number
  region?: string
  website?: string
  annual_revenue?: number
  active_deals?: number
}

export type SqlMetrics = {
  total_pipeline_value?: number
  active_deals_count?: number
  closed_won_value?: number
  closed_won_count?: number
  closed_lost_value?: number
  average_deal_size?: number
  by_region?: Record<string, { count: number; value: number }>
  by_stage?: Record<string, { count: number; value: number }>
}

export type McpResult = {
  service?: string
  summary?: string
  query?: string
  files?: McpFile[]
  messages?: McpMessage[]
  items?: McpFile[] | string[]
  documents?: KbDocument[]
  generated_documents?: GeneratedDocument[]
  kpi_cards?: KpiCard[]
  trends?: TrendData[]
  insights?: string[]
  contacts?: SqlContact[]
  companies?: SqlCompany[]
  metrics?: SqlMetrics
  contacts_summary?: string
  companies_summary?: string
  metrics_summary?: string
  category?: string
  profile?: Record<string, any>
  preferences?: Record<string, any>
  recent_topics?: string[]
  bookmarks?: MemoryBookmark[]
  frequent_queries?: string[]
  relevant_snippets?: MemorySnippet[]
  role_based_defaults?: Record<string, any>
  error?: string
}

export type ToolCall = {
  name: string
  args?: Record<string, any>
}

export type ChatResponse = {
  reply: string
  tool_calls?: ToolCall[]
  mcp_results?: McpResult[]
}

const DEFAULT_SQL_DEMO_SUMMARY = 'demo mode: returning multifamily & brokerage database'

function isDefaultSqlDemoResult(result: McpResult): boolean {
  return (
    (result.service === 'sql' || !!result.metrics || (result.contacts?.length || 0) > 0 || (result.companies?.length || 0) > 0) &&
    typeof result.summary === 'string' &&
    result.summary.trim().toLowerCase() === DEFAULT_SQL_DEMO_SUMMARY
  )
}

/* ─── Helpers ───────────────────────────────────────────────────── */

function formatBytes(bytes?: number): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}

function fileIcon(name: string): string {
  const ext = name.split('.').pop()?.toLowerCase() || ''
  const map: Record<string, string> = {
    xlsx: '📊',
    xls: '📊',
    csv: '📊',
    pdf: '📄',
    docx: '📝',
    doc: '📝',
    pptx: '📽️',
    ppt: '📽️',
    vsdx: '📐',
    md: '📋',
    txt: '📋',
    json: '⚙️',
  }
  return map[ext] || '📁'
}

/* ─── Export Menu ──────────────────────────────────────────────────── */

export function ExportMenu({ type, title, data }: { type: 'report' | 'table'; title: string; data: any }) {
  const [open, setOpen] = useState(false)
  const [exporting, setExporting] = useState<string | null>(null)

  const formats = [
    { key: 'xlsx', label: 'Excel (.xlsx)', icon: '📊' },
    { key: 'docx', label: 'Word (.docx)', icon: '📝' },
    { key: 'pdf', label: 'PDF (.pdf)', icon: '📄' },
  ]

  const handleExport = async (format: string) => {
    setExporting(format)
    try {
      const res = await fetch(`${ORCHESTRATOR_URL}/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, format, title, data }),
      })
      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText)
        alert(`Export failed (${res.status}): ${text.slice(0, 300)}`)
        return
      }
      const contentType = res.headers.get('content-type') || ''
      if (!contentType.includes('application/') && !contentType.includes('octet-stream')) {
        const text = await res.text().catch(() => '')
        alert(`Export returned unexpected content type "${contentType}".${text ? ' Response: ' + text.slice(0, 200) : ''}`)
        return
      }
      const blob = await res.blob()
      const contentDisposition = res.headers.get('content-disposition') || ''
      const match = contentDisposition.match(/filename="?([^";]+)"?/)
      const filename = match ? match[1] : `${title.replace(/[^a-zA-Z0-9]+/g, '-').replace(/^-|-$/g, '').toLowerCase() || 'export'}.${format}`
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.style.display = 'none'
      document.body.appendChild(a)
      a.click()
      setTimeout(() => {
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
      }, 1000)
    } catch (e) {
      alert('Export failed. See console for details.')
      console.error('Export error:', e)
    } finally {
      setExporting(null)
      setOpen(false)
    }
  }

  return (
    <div className="export-menu-wrapper" onClick={(e) => e.stopPropagation()} onKeyDown={(e) => { if (e.key === 'Escape') setOpen(false) }}>
      <button className="export-btn" onClick={() => setOpen(!open)} title="Export" aria-label="Export options">
        <span className="export-btn-icon">⬇️</span>
        <span className="export-btn-arrow">{open ? '▲' : '▼'}</span>
      </button>
      {open && (
        <div className="export-dropdown">
          {formats.map((f) => (
            <button
              key={f.key}
              className="export-option"
              onClick={() => handleExport(f.key)}
              disabled={exporting === f.key}
            >
              {exporting === f.key ? <span className="export-spinner">⏳</span> : f.icon} {f.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Tool Badge ────────────────────────────────────────────────── */

export function ToolBadge({ name }: { name: string }) {
  const labels: Record<string, string> = {
    query_mail: '📧 Mail',
    query_onedrive: '☁️ OneDrive',
    query_files: '📁 Files',
    query_sql: '🗃️ SQL',
    query_knowledge_base: '📚 Knowledge Base',
    query_memory: '🧠 Memory',
    query_document_generation: '📄 Document',
    query_analytics: '📊 Analytics',
  }
  return <span className="tool-badge">{labels[name] || name}</span>
}

/* ─── Live Tool Badge (streaming) ─────────────────────────────────── */

export function LiveToolBadge({ name, label, status, summary }: { name: string; label: string; status: 'calling' | 'done' | 'error'; summary?: string }) {
  const icons: Record<string, string> = {
    query_mail: '📧',
    query_onedrive: '☁️',
    query_files: '📁',
    query_sql: '🗃️',
    query_knowledge_base: '📚',
    query_memory: '🧠',
    query_document_generation: '📄',
    query_analytics: '📊',
  }
  const icon = icons[name] || '🔧'

  if (status === 'calling') {
    return (
      <span className="live-tool live-tool-calling">
        <span className="live-tool-icon spinning">{icon}</span>
        <span className="live-tool-label">{label}</span>
        <span className="live-tool-pulse" />
      </span>
    )
  }

  if (status === 'error') {
    return (
      <span className="live-tool live-tool-error">
        <span className="live-tool-icon">❌</span>
        <span className="live-tool-label">{label}</span>
        {summary && <span className="live-tool-summary">{summary}</span>}
      </span>
    )
  }

  return (
    <span className="live-tool live-tool-done">
      <span className="live-tool-icon">✅</span>
      <span className="live-tool-label">{label}</span>
      {summary && <span className="live-tool-summary">{summary}</span>}
    </span>
  )
}

/* ─── Email Card ────────────────────────────────────────────────── */

export function EmailCard({ msg }: { msg: McpMessage }) {
  return (
    <div className={`card email-card ${msg.isRead === false ? 'unread' : ''}`}>
      <div className="email-header">
        <div className="email-sender">
          <div className="avatar">{msg.from?.charAt(0).toUpperCase() || '?'}</div>
          <div className="email-meta">
            <div className="email-from">{msg.from}</div>
            <div className="email-date">{formatDate(msg.receivedDateTime)}</div>
          </div>
        </div>
        {msg.isRead === false && <span className="unread-dot">●</span>}
      </div>
      <div className="email-subject">{msg.subject}</div>
      <div className="email-preview">{msg.bodyPreview}</div>
    </div>
  )
}

/* ─── File Card ─────────────────────────────────────────────────── */

async function downloadFile(file: McpFile) {
  if (!file.url) return
  const url = file.url.startsWith('http') ? file.url : `${ORCHESTRATOR_URL}${file.url}`
  try {
    const res = await fetch(url)
    if (!res.ok) throw new Error(`Download failed: ${res.status}`)
    const blob = await res.blob()
    const blobUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = blobUrl
    a.download = file.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(blobUrl)
  } catch {
    window.open(url, '_blank')
  }
}

export function FileCard({ file }: { file: McpFile }) {
  const clickable = !!file.url
  return (
    <div
      className={`card file-card${clickable ? ' clickable' : ''}`}
      onClick={clickable ? () => downloadFile(file) : undefined}
      title={clickable ? `Download ${file.name}` : undefined}
      role={clickable ? 'button' : undefined}
      tabIndex={clickable ? 0 : undefined}
      onKeyDown={clickable ? (e) => { if (e.key === 'Enter') downloadFile(file) } : undefined}
    >
      <div className="file-icon">{fileIcon(file.name)}</div>
      <div className="file-body">
        <div className="file-name">{file.name}</div>
        <div className="file-desc">{file.description || file.folder || ''}</div>
        <div className="file-footer">
          <span className="file-folder">📂 {file.folder || 'General'}</span>
          {file.size ? <span className="file-size">{formatBytes(file.size)}</span> : null}
          {file.lastModifiedDateTime ? (
            <span className="file-date">{formatDate(file.lastModifiedDateTime)}</span>
          ) : null}
        </div>
      </div>
    </div>
  )
}

/* ─── Knowledge Base Card ─────────────────────────────────────── */

export function KnowledgeBaseCard({ doc }: { doc: KbDocument }) {
  const typeIcon = doc.type === 'SOP' ? '⚙️' : '📋'
  const statusClass = doc.status === 'Active' ? 'status-active' : 'status-draft'

  return (
    <div className="card kb-card">
      <div className="kb-header">
        <div className="kb-type-icon">{typeIcon}</div>
        <div className="kb-meta">
          <div className="kb-title">{doc.title}</div>
          <div className="kb-subtitle">
            <span className={`kb-status ${statusClass}`}>{doc.status}</span>
            <span className="kb-category">{doc.category}</span>
            {doc.version && <span className="kb-version">v{doc.version}</span>}
          </div>
        </div>
      </div>
      <div className="kb-summary">{doc.summary}</div>
      {doc.key_points && doc.key_points.length > 0 && (
        <ul className="kb-points">
          {doc.key_points.map((p, i) => (
            <li key={i}>{p}</li>
          ))}
        </ul>
      )}
      {doc.owner && (
        <div className="kb-footer">
          <span className="kb-owner">Owner: {doc.owner}</span>
          {doc.effective_date && (
            <span className="kb-date">Effective: {formatDate(doc.effective_date)}</span>
          )}
        </div>
      )}
    </div>
  )
}

/* ─── Memory Card ─────────────────────────────────────────────────── */

export function MemoryCard({ result }: { result: McpResult }) {
  const profile = result.profile || {}
  const prefs = result.preferences || {}
  const topics = result.recent_topics || []
  const bookmarks = result.bookmarks || []
  const snippets = result.relevant_snippets || []

  return (
    <div className="card memory-card">
      <div className="memory-header">
        <div className="memory-avatar">{profile.name ? profile.name.charAt(0).toUpperCase() : '👤'}</div>
        <div className="memory-meta">
          <div className="memory-name">{profile.name || 'User'}</div>
          <div className="memory-role">{profile.role || 'User'}{profile.department ? ` · ${profile.department}` : ''}</div>
        </div>
      </div>

      {prefs.data_focus && prefs.data_focus.length > 0 && (
        <div className="memory-section">
          <div className="memory-label">Focus Areas</div>
          <div className="memory-tags">
            {prefs.data_focus.map((t: string, i: number) => (
              <span key={i} className="memory-tag">{t}</span>
            ))}
          </div>
        </div>
      )}

      {snippets.length > 0 && (
        <div className="memory-section">
          <div className="memory-label">Relevant Context</div>
          <ul className="memory-snippets">
            {snippets.map((s, i) => {
              const text = typeof s.content === 'string' ? s.content : s.content?.reason || JSON.stringify(s.content)
              return <li key={i}>{text}</li>
            })}
          </ul>
        </div>
      )}

      {topics.length > 0 && (
        <div className="memory-section">
          <div className="memory-label">Recent Topics</div>
          <ul className="memory-list">
            {topics.slice(0, 5).map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {bookmarks.length > 0 && (
        <div className="memory-section">
          <div className="memory-label">Bookmarks</div>
          <div className="memory-bookmarks">
            {bookmarks.map((bm, i) => (
              <div key={i} className="memory-bm">
                <span className="memory-bm-icon">{bm.type === 'sop' ? '⚙️' : bm.type === 'file' ? '📁' : bm.type === 'email_thread' ? '📧' : '🔖'}</span>
                <span className="memory-bm-name">{bm.name || bm.id || 'Item'}</span>
                <span className="memory-bm-reason">{bm.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Document Card ─────────────────────────────────────────────────── */

export function DocumentCard({ doc }: { doc: GeneratedDocument }) {
  const typeIcon = doc.type === 'executive_summary' ? '📊' : doc.type === 'board_briefing' ? '📋' : doc.type === 'sales_report' ? '💼' : doc.type === 'security_assessment' ? '🔒' : '📄'

  const exportData = {
    sections: doc.sections || [],
    action_items: doc.action_items || [],
    tags: doc.tags || [],
  }

  return (
    <div className="card doc-card">
      <div className="doc-header">
        <div className="doc-type-icon">{typeIcon}</div>
        <div className="doc-meta">
          <div className="doc-title">{doc.title}</div>
          <div className="doc-subtitle">
            <span className="doc-status">{doc.status}</span>
            <span className="doc-pages">{doc.pages} pages</span>
            <span className="doc-words">{doc.word_count?.toLocaleString()} words</span>
          </div>
        </div>
        <div className="card-export">
          <ExportMenu type="report" title={doc.title || 'Report'} data={exportData} />
        </div>
      </div>

      {doc.sections && doc.sections.length > 0 && (
        <div className="doc-sections">
          {doc.sections.map((section, i) => (
            <div key={i} className="doc-section">
              <div className="doc-section-heading">{section.heading}</div>
              <div className="doc-section-content">{section.content}</div>
              {section.key_metrics && section.key_metrics.length > 0 && (
                <div className="doc-metrics">
                  {section.key_metrics.map((m, j) => (
                    <div key={j} className="doc-metric">
                      <span className="doc-metric-label">{m.label}</span>
                      <span className="doc-metric-value">{m.value}</span>
                      {m.trend && <span className="doc-metric-trend">{m.trend}</span>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {doc.action_items && doc.action_items.length > 0 && (
        <div className="doc-action-items">
          <div className="doc-action-label">Action Items</div>
          <ul className="doc-action-list">
            {doc.action_items.map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}

      {doc.tags && doc.tags.length > 0 && (
        <div className="doc-tags">
          {doc.tags.map((t, i) => (
            <span key={i} className="doc-tag">{t}</span>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── Analytics Card ────────────────────────────────────────────────── */

export function AnalyticsCard({ result }: { result: McpResult }) {
  const kpis = result.kpi_cards || []
  const trends = result.trends || []
  const insights = result.insights || []

  const exportTableData = {
    headers: ['Name', 'Value', 'Change', 'Period', 'Status', 'Target'],
    rows: kpis.map((k) => [k.name, k.value, k.change, k.period, k.status, k.target]),
  }

  return (
    <div className="card analytics-card">
      <div className="analytics-header">
        <div className="analytics-icon">📊</div>
        <div className="analytics-meta">
          <div className="analytics-title">{result.category || 'Analytics Dashboard'}</div>
          <div className="analytics-summary">{result.summary}</div>
        </div>
        <div className="card-export">
          <ExportMenu type="table" title={result.category || 'Analytics'} data={exportTableData} />
        </div>
      </div>

      {kpis.length > 0 && (
        <div className="analytics-kpis">
          {kpis.map((kpi, i) => {
            const statusClass = kpi.status === 'positive' ? 'kpi-positive' : kpi.status === 'negative' ? 'kpi-negative' : 'kpi-neutral'
            return (
              <div key={i} className={`analytics-kpi ${statusClass}`}>
                <div className="kpi-name">{kpi.name}</div>
                <div className="kpi-value">{kpi.value}</div>
                <div className="kpi-change">{kpi.change} <span className="kpi-period">{kpi.period}</span></div>
                <div className={`kpi-target ${kpi.target_status}`}>Target: {kpi.target}</div>
              </div>
            )
          })}
        </div>
      )}

      {trends.length > 0 && (
        <div className="analytics-trends">
          <div className="analytics-section-label">Trends</div>
          {trends.map((trend, i) => (
            <div key={i} className="analytics-trend">
              <div className="trend-name">{trend.metric}</div>
              <div className={`trend-direction trend-${trend.trend_direction}`}>
                {trend.trend_direction === 'up' ? '↗️' : trend.trend_direction === 'down' ? '↘️' : '➡️'} {trend.trend_strength}
              </div>
              <div className="trend-data">
                {trend.data.map((d, j) => (
                  <span key={j} className="trend-point">
                    {d.month || d.quarter}: {d.value}
                    {j < trend.data.length - 1 ? ' → ' : ''}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {insights.length > 0 && (
        <div className="analytics-insights">
          <div className="analytics-section-label">Key Insights</div>
          <ul className="insights-list">
            {insights.map((insight, i) => (
              <li key={i}>{insight}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/* ─── SQL Data Card ────────────────────────────────────────────────── */

function stageBadge(stage?: string): string {
  const map: Record<string, string> = {
    'Closed Won': '🟢',
    'Closed Lost': '🔴',
    'Negotiation': '🟡',
    'Proposal Sent': '🔵',
    'Discovery': '🟣',
    'Qualified': '⚪',
  }
  return map[stage || ''] || ''
}

function fmtCurrency(n?: number): string {
  if (n == null) return ''
  if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`
  return `$${n.toFixed(0)}`
}

export function SqlDataCard({ result }: { result: McpResult }) {
  const contacts = result.contacts || []
  const companies = result.companies || []
  const metrics = result.metrics

  const sqlTableData = {
    headers: contacts.length > 0
      ? ['First Name', 'Last Name', 'Email', 'Phone', 'Company', 'Stage', 'Deal Value']
      : companies.length > 0
        ? ['Name', 'Industry', 'Revenue Tier', 'Region', 'Website']
        : ['Metric', 'Value'],
    rows: contacts.length > 0
      ? contacts.map((c) => [c.first_name || '', c.last_name || '', c.email || '', c.phone || '', c.company || '', c.stage || '', c.deal_value != null ? `$${c.deal_value.toLocaleString()}` : ''])
      : companies.length > 0
        ? companies.map((c) => [c.name || '', c.industry || '', c.revenue_tier || '', c.region || '', c.website || ''])
        : Object.entries(metrics || {}).filter(([_, v]) => typeof v === 'string' || typeof v === 'number').map(([k, v]) => [k, String(v)]),
  }

  return (
    <div className="card sql-card">
      <div className="sql-header">
        <span className="sql-icon">🗃️</span>
        <span className="sql-title">{result.summary || 'SQL Database'}</span>
        <div className="card-export">
          <ExportMenu type="table" title={result.summary || 'Data Export'} data={sqlTableData} />
        </div>
      </div>

      {metrics && (
        <div className="sql-metrics">
          {metrics.total_pipeline_value != null && (
            <div className="sql-metric">
              <span className="sql-metric-label">Pipeline</span>
              <span className="sql-metric-value">{fmtCurrency(metrics.total_pipeline_value)}</span>
            </div>
          )}
          {metrics.active_deals_count != null && (
            <div className="sql-metric">
              <span className="sql-metric-label">Active Deals</span>
              <span className="sql-metric-value">{metrics.active_deals_count}</span>
            </div>
          )}
          {metrics.closed_won_value != null && (
            <div className="sql-metric">
              <span className="sql-metric-label">Closed Won</span>
              <span className="sql-metric-value">{fmtCurrency(metrics.closed_won_value)} ({metrics.closed_won_count})</span>
            </div>
          )}
        </div>
      )}

      {contacts.length > 0 && (
        <div className="sql-section">
          <div className="sql-section-label">{result.contacts_summary || 'Contacts'}</div>
          <div className="sql-contacts">
            {contacts.slice(0, 8).map((c, i) => (
              <div key={i} className="sql-row">
                <div className="sql-row-left">
                  <span className="sql-contact-name">{c.first_name} {c.last_name}</span>
                  <span className="sql-contact-company">{c.company}</span>
                </div>
                <div className="sql-row-right">
                  <span className="sql-contact-stage">{stageBadge(c.stage)} {c.stage}</span>
                  <span className="sql-contact-value">{fmtCurrency(c.deal_value)}</span>
                </div>
              </div>
            ))}
            {contacts.length > 8 && (
              <div className="sql-more">+{contacts.length - 8} more</div>
            )}
          </div>
        </div>
      )}

      {companies.length > 0 && (
        <div className="sql-section">
          <div className="sql-section-label">{result.companies_summary || 'Companies'}</div>
          <div className="sql-companies">
            {companies.slice(0, 5).map((c, i) => (
              <div key={i} className="sql-row">
                <div className="sql-row-left">
                  <span className="sql-company-name">{c.name}</span>
                  <span className="sql-company-industry">{c.industry}</span>
                </div>
                <div className="sql-row-right">
                  <span className="sql-company-tier">{c.revenue_tier}</span>
                  <span className="sql-company-region">{c.region}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {metrics?.by_stage && Object.keys(metrics.by_stage).length > 0 && (
        <div className="sql-section">
          <div className="sql-section-label">By Stage</div>
          <div className="sql-bars">
            {Object.entries(metrics.by_stage).map(([stage, data]) => {
              const maxVal = Math.max(...Object.values(metrics.by_stage!).map((d: any) => d.value || 0), 1)
              const width = ((data.value || 0) / maxVal) * 100
              return (
                <div key={stage} className="sql-bar-row">
                  <span className="sql-bar-label">{stageBadge(stage)} {stage}</span>
                  <div className="sql-bar-track">
                    <div className="sql-bar-fill" style={{ width: `${width}%` }} />
                  </div>
                  <span className="sql-bar-value">{fmtCurrency(data.value)}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

/* ─── Error Card ──────────────────────────────────────────────────── */

export function ErrorCard({ error }: { error: string }) {
  return (
    <div className="card error-card">
      <div className="error-icon">⚠️</div>
      <div className="error-text">{error}</div>
    </div>
  )
}

/* ─── Result Deck ───────────────────────────────────────────────── */

export function ResultDeck({ result }: { result: McpResult }) {
  if (result.error) {
    return <ErrorCard error={result.error} />
  }

  // Suppress the generic SQL demo card so it does not appear on unrelated requests.
  if (isDefaultSqlDemoResult(result)) {
    return null
  }

  const files = result.files || (result.items as McpFile[]) || []
  const messages = result.messages || []
  const documents = result.documents || []

  if (documents.length > 0 && result.service !== 'document_generation') {
    return (
      <div className="deck">
        <div className="deck-header">
          📚 {result.summary || 'Policies & SOPs'}
        </div>
        <div className="deck-grid kb-grid">
          {documents.map((d, i) => (
            <KnowledgeBaseCard key={i} doc={d} />
          ))}
        </div>
      </div>
    )
  }

  if (messages.length > 0) {
    return (
      <div className="deck">
        <div className="deck-header">
          📧 {result.summary || 'Messages'}
        </div>
        <div className="deck-grid email-grid">
          {messages.map((m, i) => (
            <EmailCard key={i} msg={m} />
          ))}
        </div>
      </div>
    )
  }

  if (files.length > 0) {
    return (
      <div className="deck">
        <div className="deck-header">
          📁 {result.summary || 'Files'}
        </div>
        <div className="deck-grid file-grid">
          {files.map((f, i) => (
            <FileCard key={i} file={f} />
          ))}
        </div>
      </div>
    )
  }

  if (result.service === 'memory' || result.profile || result.recent_topics || result.bookmarks) {
    return (
      <div className="deck">
        <div className="deck-header">
          🧠 {result.summary || 'Personal Context'}
        </div>
        <div className="deck-grid memory-grid">
          <MemoryCard result={result} />
        </div>
      </div>
    )
  }

  if (result.service === 'document_generation' || (result.generated_documents && result.generated_documents.length > 0)) {
    const docs = result.generated_documents || result.documents || []
    return (
      <div className="deck">
        <div className="deck-header">
          📄 {result.summary || 'Generated Documents'}
        </div>
        <div className="deck-grid doc-grid">
          {docs.map((d, i) => (
            <DocumentCard key={i} doc={d} />
          ))}
        </div>
      </div>
    )
  }

  if (result.service === 'analytics' || (result.kpi_cards && result.kpi_cards.length > 0)) {
    return (
      <div className="deck">
        <div className="deck-header">
          📊 {result.summary || 'Analytics'}
        </div>
        <div className="deck-grid analytics-grid">
          <AnalyticsCard result={result} />
        </div>
      </div>
    )
  }

  if (result.service === 'sql' || (result.contacts && result.contacts.length > 0) || (result.companies && result.companies.length > 0) || result.metrics) {
    return (
      <div className="deck">
        <div className="deck-header">
          🗃️ {result.summary || 'SQL Database'}
        </div>
        <div className="deck-grid sql-grid">
          <SqlDataCard result={result} />
        </div>
      </div>
    )
  }

  return null
}
