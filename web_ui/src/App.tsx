import { useEffect, useMemo, useRef, useState, lazy, Suspense } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { AuthProvider, useAuth } from './auth'
import { getOrchestratorUrl } from './apiBase'
import { DocumentWorkflowPanel } from './DocumentWorkflowPanel'
import { LoginPage } from './LoginPage'
import { ResultDeck, ToolBadge, LiveToolBadge, downloadResource, type ChatResponse, type DocumentAction } from './Cards'
import { WorkPacketPanel } from './WorkPacketPanel'
import { useDemoLauncher } from './useDemoLauncher.js'

const SettingsPage = lazy(() => import('./SettingsPage').then(m => ({ default: m.SettingsPage })))
const AdminPage = lazy(() => import('./AdminPage').then(m => ({ default: m.AdminPage })))
const ORCHESTRATOR_URL = getOrchestratorUrl()

type DocumentsResponse = {
  items: DocumentAction[]
}

type ActionRow = {
  action_id: string
  source_id: string
  entity_type: string
  status: string
  created_at: string
  updated_at: string
  payload?: {
    document_action_id?: number
    title?: string
    document_type?: string
    message?: string
    artifact_count?: number
  }
  result?: {
    delivered?: boolean
    channel?: string
    message?: string
    artifact_count?: number
  } | null
}

type ActionsResponse = {
  actions: ActionRow[]
}

type View = 'chat' | 'settings' | 'service_health' | 'performance' | 'network' | 'admin' | 'documents' | 'outbox' | 'report'

type Playbook = {
  id: string
  eyebrow: string
  title: string
  question: string
  outputs: string[]
}

type PerformanceData = {
  generated_at: string
  overview: {
    portfolio_value: number
    total_units: number
    occupied_units: number
    occupancy: number
    total_noi: number
    pipeline_value: number
    pipeline_commission: number
    active_deals: number
    closed_ytd: number
    properties_count: number
  }
  pipeline: {
    pipeline_total: number
    commission_pipeline: number
    by_stage: Record<string, { count: number; value: number; commission: number }>
  }
  activities: {
    upcoming_count: number
    completed_count: number
    by_type: Record<string, number>
  }
  top_properties_by_noi: Array<{ name: string; city: string; noi: number; value: number; cap: number }>
}

type NetworkData = {
  generated_at: string
  summary: {
    sites: number
    devices: number
    events: number
    daily_metrics: number
    avg_uptime_pct: number
    avg_latency_ms: number
    avg_packet_loss_pct: number
    avg_throughput_mbps: number
    total_incidents: number
    open_events: number
    open_event_rate_pct: number
    isp_count?: number
    sla_target_uptime_pct?: number
    sla_met_pct?: number
    sla_breach_days?: number
    incident_rate_per_100_device_days?: number
  }
  severity_distribution: Array<{ severity: string; count: number; pct_of_events: number }>
  site_snapshot_30d: Array<{
    site_code: string
    site_name: string
    isp_primary?: string
    isp_secondary?: string
    sla_target_uptime_pct?: number
    sla_met_pct?: number
    sla_breach_days?: number
    avg_uptime_pct: number
    avg_latency_ms: number
    avg_packet_loss_pct: number
    incidents: number
  }>
  monthly_trend: Array<{
    month: string
    avg_uptime_pct: number
    avg_latency_ms: number
    avg_packet_loss_pct: number
    incidents: number
  }>
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  data?: ChatResponse
  errorDetail?: string
}

type LegacyChatMessage = {
  id?: unknown
  role?: unknown
  text?: unknown
  content?: unknown
  data?: unknown
}

type LiveTool = {
  id: string
  name: string
  label: string
  status: 'calling' | 'done' | 'error'
  summary?: string
}

const STORAGE_KEY = 'aiagent_chat_history'
const IS_DEV_DEMO = import.meta.env.DEV && import.meta.env.VITE_DISABLE_DEV_LOGIN_BYPASS !== 'true'
const DEMO_PATH = '/demo'

// Multifamily & brokerage suggested prompts
const SUGGESTED_PROMPTS = [
  { icon: 'PO', label: 'Portfolio overview', query: 'Show me our full multifamily portfolio — all properties, total units, occupancy rate, and average rent.' },
  { icon: 'DP', label: 'Deal pipeline', query: 'Show me the full deal pipeline — all active deals, their stages, offer prices, and commission projections.' },
  { icon: 'MA', label: 'Market analytics', query: 'Show me Memphis multifamily market analytics — cap rates, occupancy trends, and new supply.' },
  { icon: 'PP', label: 'Portfolio performance', query: 'Generate a portfolio performance summary with NOI, cap rates, and rent growth across all properties.' },
  { icon: 'PS', label: 'Properties by status', query: 'List all properties by status — active, under contract, and recently sold.' },
  { icon: 'KC', label: 'Key contacts', query: 'Show me my key contacts — owners, brokers, and investors in the Memphis market.' },
  { icon: 'CT', label: 'Commission tracker', query: 'What is my YTD commission income and how does it compare to last year?' },
  { icon: 'AA', label: 'Upcoming activities', query: 'What are my upcoming property tours, inspections, and deal deadlines this month?' },
]

const PLAYBOOKS: Playbook[] = [
  {
    id: 'portfolio-performance-review',
    eyebrow: 'Primary workflow',
    title: 'Portfolio performance review',
    question: 'Generate a portfolio performance review with NOI, occupancy, rent trends, risk flags, and an export-ready executive summary.',
    outputs: ['Governed draft', 'Presentation report', 'PDF / DOCX / XLSX package'],
  },
  {
    id: 'board-packet',
    eyebrow: 'Secondary workflow',
    title: 'Board packet',
    question: 'Prepare a board packet summarizing portfolio health, key risks, capital priorities, and next-quarter actions.',
    outputs: ['Board-ready narrative', 'Approval workflow', 'Formal export package'],
  },
]

function loadHistory(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []

    const parsed: unknown = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []

    const normalized: ChatMessage[] = []
    for (const item of parsed as LegacyChatMessage[]) {
      const role = item?.role === 'user' || item?.role === 'assistant' ? item.role : null
      if (!role) continue

      const text = typeof item?.text === 'string'
        ? item.text
        : typeof item?.content === 'string'
          ? item.content
          : ''

      normalized.push({
        id: typeof item?.id === 'string' && item.id.trim().length > 0 ? item.id : nextId(),
        role,
        text,
        data: (item?.data as ChatResponse | undefined),
      })
    }

    return normalized
  } catch {
    return []
  }
}

function renderMarkdown(text: string): string {
  try {
    return DOMPurify.sanitize(marked.parse(text || '', { breaks: true }) as string)
  } catch {
    return text || ''
  }
}

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value)
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('en-US').format(value)
}

function formatDocumentType(value?: string): string {
  return (value || 'document_workflow').split('_').join(' ')
}

function TopNav({
  currentView,
  onNavigate,
  onClear,
}: {
  currentView: View
  onNavigate: (view: View) => void
  onClear?: () => void
}) {
  const { user, isAdmin, logout } = useAuth()

  const links: { id: View; label: string }[] = [
    { id: 'chat', label: 'Chat' },
    { id: 'performance', label: 'Portfolio' },
    { id: 'network', label: 'Sites' },
    { id: 'documents', label: 'Workflows' },
    { id: 'outbox', label: 'Deliveries' },
    ...(isAdmin ? [{ id: 'admin' as View, label: 'Operations' }] : []),
    { id: 'settings', label: 'Settings' },
  ]

  return (
    <nav className="app-nav" aria-label="Main navigation">
      <div className="app-nav-brand">
        <div className="evie-mark evie-mark-sm" aria-hidden="true">
          <span className="mark-segment mark-segment-top" />
          <span className="mark-segment mark-segment-mid" />
          <span className="mark-segment mark-segment-bot" />
        </div>
        <span className="app-nav-title">EVIEAI</span>
      </div>

      <div className="app-nav-links" role="menubar">
        {links.map(({ id, label }) => (
          <button
            key={id}
            className={`nav-link${currentView === id || (id === 'settings' && currentView === 'service_health') ? ' active' : ''}`}
            onClick={() => onNavigate(id)}
            role="menuitem"
          >
            {label}
          </button>
        ))}
      </div>

      <div className="app-nav-user">
        {onClear && (
          <button className="nav-action" onClick={onClear}>
            Clear thread
          </button>
        )}
        <span className="nav-email" title={user?.email}>{user?.email}</span>
        <button className="nav-action" onClick={logout}>
          Sign out
        </button>
      </div>
    </nav>
  )
}

function PerformanceDashboardView({ userId, onNavigate }: { userId?: string; onNavigate: (view: View) => void }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<PerformanceData | null>(null)

  async function loadDashboard() {
    setLoading(true)
    setError('')
    try {
      const url = `${ORCHESTRATOR_URL}/dashboard/performance${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`
      const res = await fetch(url)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = (await res.json()) as PerformanceData
      setData(payload)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Could not load performance dashboard: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDashboard()
  }, [userId])

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />
      <TopNav currentView="performance" onNavigate={onNavigate} />
      <header className="hero">
        <p className="eyebrow">Portfolio signal</p>
        <h1>Portfolio performance</h1>
        <p className="subtitle">Portfolio, pipeline, and execution performance in one view.</p>
      </header>

      <div className="dashboard-shell">
        <div className="dashboard-toolbar">
          <button className="status-btn" onClick={() => onNavigate('chat')}>Back to chat</button>
          <button className="status-btn" onClick={() => void loadDashboard()} disabled={loading}>
            {loading ? 'Updating...' : 'Update now'}
          </button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}

        {loading && !data && <div className="dashboard-loading">Loading portfolio data...</div>}

        {data && (
          <>
            <div className="kpi-grid">
              <div className="kpi-card"><span>Portfolio Value</span><strong>{formatCurrency(data.overview.portfolio_value)}</strong></div>
              <div className="kpi-card"><span>Occupancy</span><strong>{data.overview.occupancy}%</strong></div>
              <div className="kpi-card"><span>Total NOI</span><strong>{formatCurrency(data.overview.total_noi)}</strong></div>
              <div className="kpi-card"><span>Pipeline Value</span><strong>{formatCurrency(data.overview.pipeline_value)}</strong></div>
              <div className="kpi-card"><span>Pipeline Commission</span><strong>{formatCurrency(data.overview.pipeline_commission)}</strong></div>
              <div className="kpi-card"><span>Active Deals</span><strong>{data.overview.active_deals}</strong></div>
            </div>

            <div className="dashboard-row">
              <section className="dashboard-panel">
                <h3>Pipeline by Stage</h3>
                <ul>
                  {Object.entries(data.pipeline.by_stage).map(([stage, value]) => (
                    <li key={stage}>
                      <span>{stage}</span>
                      <span>{value.count} deals · {formatCurrency(value.value)}</span>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="dashboard-panel">
                <h3>Activity Workload</h3>
                <ul>
                  <li><span>Upcoming</span><span>{data.activities.upcoming_count}</span></li>
                  <li><span>Completed</span><span>{data.activities.completed_count}</span></li>
                  {Object.entries(data.activities.by_type).map(([atype, count]) => (
                    <li key={atype}><span>{atype}</span><span>{count}</span></li>
                  ))}
                </ul>
              </section>
            </div>

            <section className="dashboard-panel">
              <h3>Top Properties by NOI</h3>
              <div className="table-wrap">
                <table className="perf-table">
                  <thead>
                    <tr>
                      <th>Property</th>
                      <th>City</th>
                      <th>NOI</th>
                      <th>Value</th>
                      <th>Cap Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.top_properties_by_noi.map((p) => (
                      <tr key={p.name}>
                        <td>{p.name}</td>
                        <td>{p.city}</td>
                        <td>{formatCurrency(p.noi)}</td>
                        <td>{formatCurrency(p.value)}</td>
                        <td>{p.cap}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}

function NetworkDashboardView({ userId, onNavigate }: { userId?: string; onNavigate: (view: View) => void }) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState<NetworkData | null>(null)

  async function loadDashboard() {
    setLoading(true)
    setError('')
    try {
      const url = `${ORCHESTRATOR_URL}/dashboard/network${userId ? `?user_id=${encodeURIComponent(userId)}` : ''}`
      const res = await fetch(url)
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = (await res.json()) as NetworkData
      setData(payload)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Could not load network dashboard: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDashboard()
  }, [userId])

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />
      <TopNav currentView="network" onNavigate={onNavigate} />
      <header className="hero">
        <p className="eyebrow">Site reliability</p>
        <h1>Network performance</h1>
        <p className="subtitle">Wireless reliability, event pressure, and site-level performance across provider sources.</p>
      </header>

      <div className="dashboard-shell">
        <div className="dashboard-toolbar">
          <button className="status-btn" onClick={() => onNavigate('chat')}>Back to chat</button>
          <button className="status-btn" onClick={() => void loadDashboard()} disabled={loading}>
            {loading ? 'Updating...' : 'Update now'}
          </button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}
        {loading && !data && <div className="dashboard-loading">Loading network data...</div>}

        {data && (
          <>
            <div className="kpi-grid">
              <div className="kpi-card"><span>Sites</span><strong>{formatNumber(data.summary.sites)}</strong></div>
              <div className="kpi-card"><span>Devices</span><strong>{formatNumber(data.summary.devices)}</strong></div>
              <div className="kpi-card"><span>ISPs</span><strong>{formatNumber(data.summary.isp_count ?? 0)}</strong></div>
              <div className="kpi-card"><span>Avg Uptime</span><strong>{data.summary.avg_uptime_pct}%</strong></div>
              <div className="kpi-card"><span>SLA Met</span><strong>{data.summary.sla_met_pct ?? 0}%</strong></div>
              <div className="kpi-card"><span>Avg Latency</span><strong>{data.summary.avg_latency_ms} ms</strong></div>
              <div className="kpi-card"><span>Packet Loss</span><strong>{data.summary.avg_packet_loss_pct}%</strong></div>
              <div className="kpi-card"><span>SLA Breach Days</span><strong>{formatNumber(data.summary.sla_breach_days ?? 0)}</strong></div>
              <div className="kpi-card"><span>Open Events</span><strong>{formatNumber(data.summary.open_events)}</strong></div>
              <div className="kpi-card"><span>Incident Rate</span><strong>{data.summary.incident_rate_per_100_device_days ?? 0}/100d</strong></div>
            </div>

            <div className="dashboard-row">
              <section className="dashboard-panel">
                <h3>Event Severity Mix</h3>
                <ul>
                  {data.severity_distribution.map((row) => (
                    <li key={row.severity}>
                      <span>{row.severity}</span>
                      <span>{formatNumber(row.count)} · {row.pct_of_events}%</span>
                    </li>
                  ))}
                </ul>
              </section>

              <section className="dashboard-panel">
                <h3>Monthly Incident Trend</h3>
                <ul>
                  {data.monthly_trend.slice(0, 6).map((row) => (
                    <li key={row.month}>
                      <span>{row.month}</span>
                      <span>{formatNumber(row.incidents)} incidents</span>
                    </li>
                  ))}
                </ul>
              </section>
            </div>

            <section className="dashboard-panel">
                <h3>Network Site Snapshot (Last 30 Days)</h3>
              <div className="table-wrap">
                <table className="perf-table">
                  <thead>
                    <tr>
                      <th>Site</th>
                      <th>ISP(s)</th>
                      <th>SLA</th>
                      <th>Uptime</th>
                      <th>Latency</th>
                      <th>Packet Loss</th>
                      <th>Incidents</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.site_snapshot_30d.map((s) => (
                      <tr key={s.site_code}>
                        <td>{s.site_name} ({s.site_code})</td>
                        <td>{s.isp_primary ?? 'unknown'}{s.isp_secondary ? ` / ${s.isp_secondary}` : ''}</td>
                        <td>{s.sla_met_pct ?? 0}% met (target {s.sla_target_uptime_pct ?? 0}%)</td>
                        <td>{s.avg_uptime_pct}%</td>
                        <td>{s.avg_latency_ms} ms</td>
                        <td>{s.avg_packet_loss_pct}%</td>
                        <td>{formatNumber(s.incidents)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}

function DocumentsView({
  userId,
  authHeader,
  onNavigate,
  onOpenReport,
}: {
  userId?: string
  authHeader?: string
  onNavigate: (view: View) => void
  onOpenReport: (documentActionId: number) => void
}) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [documents, setDocuments] = useState<DocumentAction[]>([])

  async function loadDocuments() {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      params.set('limit', '50')
      if (userId) {
        params.set('user_id', userId)
      }
      const res = await fetch(`${ORCHESTRATOR_URL}/document-actions?${params.toString()}`, {
        headers: authHeader ? { Authorization: authHeader } : undefined,
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = await res.json() as DocumentsResponse
      setDocuments(payload.items || [])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Could not load document workflows: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDocuments()
  }, [userId, authHeader])

  function updateDocument(nextAction: DocumentAction) {
    setDocuments((prev) => prev.map((action) => (
      action.id === nextAction.id ? nextAction : action
    )))
  }

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />
      <TopNav currentView="documents" onNavigate={onNavigate} />
      <header className="hero">
        <p className="eyebrow">Governed Workflows</p>
        <h1>Workflow library</h1>
        <p className="subtitle">
          Reopen governed document workflows, inspect artifacts, and continue approvals outside chat.
        </p>
      </header>

      <div className="dashboard-shell">
        <div className="dashboard-toolbar">
          <button className="status-btn" onClick={() => onNavigate('chat')}>Back to chat</button>
          <button className="status-btn" onClick={() => void loadDocuments()} disabled={loading}>
            {loading ? 'Updating...' : 'Update now'}
          </button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}
        {loading && !documents.length && <div className="dashboard-loading">Loading workflows...</div>}
        {!loading && !documents.length && <div className="dashboard-loading">No workflows yet.</div>}

        {documents.length > 0 && (
          <div className="messages">
            {documents.map((action) => (
              <div key={action.id} className="message-section">
                <DocumentWorkflowPanel
                  action={action}
                  orchestratorUrl={ORCHESTRATOR_URL}
                  userId={userId}
                  authHeader={authHeader}
                  workPacketId={action.work_packet_id || `document-${action.id}`}
                  sourceSummary={action.title}
                  onActionChange={updateDocument}
                  onViewReport={onOpenReport}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function OutboxView({
  authHeader,
  onNavigate,
  onOpenReport,
}: {
  authHeader?: string
  onNavigate: (view: View) => void
  onOpenReport: (documentActionId: number) => void
}) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [actions, setActions] = useState<ActionRow[]>([])

  async function loadOutbox() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${ORCHESTRATOR_URL}/actions?source_id=document_workflow&limit=50`, {
        headers: authHeader ? { Authorization: authHeader } : undefined,
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = await res.json() as ActionsResponse
      const outbox = (payload.actions || []).filter((action) => action.entity_type === 'announcement')
      setActions(outbox)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Could not load announcement outbox: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadOutbox()
  }, [authHeader])

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />
      <TopNav currentView="outbox" onNavigate={onNavigate} />
      <header className="hero">
        <p className="eyebrow">Downstream Handoffs</p>
        <h1>Delivery outbox</h1>
        <p className="subtitle">
          Visible completion feed for governed document announcements and downstream workflow handoffs.
        </p>
      </header>

      <div className="dashboard-shell">
        <div className="dashboard-toolbar">
          <button className="status-btn" onClick={() => onNavigate('chat')}>Back to chat</button>
          <button className="status-btn" onClick={() => void loadOutbox()} disabled={loading}>
            {loading ? 'Updating...' : 'Update now'}
          </button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}
        {loading && !actions.length && <div className="dashboard-loading">Loading delivery feed...</div>}
        {!loading && !actions.length && <div className="dashboard-loading">No delivery events yet.</div>}

        {actions.length > 0 && (
          <div className="messages">
            {actions.map((action) => (
              <section key={action.action_id} className="result-card">
                <div className="result-card-header">
                  <strong>{action.payload?.title || 'Document announcement'}</strong>
                  <span>{action.status}</span>
                </div>
                <p>{action.payload?.document_type?.split('_').join(' ') || 'announcement'}</p>
                <div className="result-grid">
                  <article className="mini-card">
                    <span>Delivery</span>
                    <strong>{action.result?.delivered ? 'Delivered' : 'Pending'}</strong>
                    <p>{action.result?.channel || 'internal_queue'}</p>
                  </article>
                  <article className="mini-card">
                    <span>Message</span>
                    <strong>{action.result?.artifact_count || action.payload?.artifact_count || 0} artifact(s)</strong>
                    <p>{action.result?.message || action.payload?.message || 'Announcement queued'}</p>
                  </article>
                </div>
                {action.payload?.document_action_id ? (
                  <div className="tool-bar">
                    <button className="status-btn" onClick={() => onOpenReport(action.payload?.document_action_id || 0)}>
                      Open report
                    </button>
                  </div>
                ) : null}
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function ReportViewer({
  documentActionId,
  authHeader,
  onNavigate,
}: {
  documentActionId: number
  authHeader?: string
  onNavigate: (view: View) => void
}) {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [document, setDocument] = useState<DocumentAction | null>(null)

  function artifactDownloadUrl(fileName: string) {
    return `${ORCHESTRATOR_URL}/document-actions/${documentActionId}/artifacts/${encodeURIComponent(fileName)}`
  }

  async function handleDownloadArtifact(fileName: string) {
    setError('')
    try {
      await downloadResource(artifactDownloadUrl(fileName), fileName)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Download failed'
      setError(`Could not download ${fileName}: ${message}`)
    }
  }

  async function loadDocument() {
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${ORCHESTRATOR_URL}/document-actions/${documentActionId}`, {
        headers: authHeader ? { Authorization: authHeader } : undefined,
      })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const payload = await res.json() as DocumentAction
      setDocument(payload)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Could not load report view: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadDocument()
  }, [documentActionId, authHeader])

  return (
    <div className="page report-viewer-page">
      <div className="bg-grid" aria-hidden="true" />
      <TopNav currentView="documents" onNavigate={onNavigate} />
      <header className="hero report-hero">
        <p className="eyebrow">Document review</p>
        <h1>{document?.title || 'Executive report'}</h1>
        <p className="subtitle">
          {document ? `Review the approved narrative, artifacts, export package, and downstream handoff state for ${formatDocumentType(document.document_type)}.` : 'Loading governed report view.'}
        </p>
      </header>

      <div className="dashboard-shell report-shell">
        <div className="dashboard-toolbar">
          <button className="status-btn" onClick={() => onNavigate('documents')}>Back to workflows</button>
          <button className="status-btn" onClick={() => void loadDocument()} disabled={loading}>
            {loading ? 'Updating...' : 'Update now'}
          </button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}
        {loading && !document && <div className="dashboard-loading">Loading executive report...</div>}

        {document && (
          <>
            <div className="report-summary-grid">
              <article className="report-stat">
                <span>Status</span>
                <strong>{document.status}</strong>
                <p>{formatDocumentType(document.document_type)}</p>
              </article>
              <article className="report-stat">
                <span>Artifacts</span>
                <strong>{document.artifacts?.length || 0}</strong>
                <p>{document.artifacts?.map((artifact) => artifact.format).filter(Boolean).join(', ') || 'Awaiting finalization'}</p>
              </article>
              <article className="report-stat">
                <span>Export package</span>
                <strong>{document.export_package?.status || 'not started'}</strong>
                <p>{document.export_package?.artifacts?.map((artifact) => artifact.format).filter(Boolean).join(', ') || 'PDF, DOCX, XLSX when ready'}</p>
              </article>
              <article className="report-stat">
                <span>Delivery</span>
                <strong>{document.announcement?.status || 'pending'}</strong>
                <p>{document.announcement?.result?.message || 'Announcement visible in outbox after finalization'}</p>
              </article>
            </div>

            <div className="dashboard-row">
              <section className="dashboard-panel report-panel">
                <h3>Executive narrative</h3>
                <div
                  className="text prose report-body"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(document.draft_markdown || `# ${document.title}\n\n${formatDocumentType(document.document_type)}`) }}
                />
              </section>

              <section className="dashboard-panel report-panel">
                <h3>Lifecycle timeline</h3>
                <div className="report-timeline">
                  <div className="report-timeline-item">
                    <strong>Drafted</strong>
                    <p>{document.created_at || 'Created in current session'}</p>
                  </div>
                  <div className="report-timeline-item">
                    <strong>Finalized</strong>
                    <p>{document.executed_at || 'Awaiting finalization'}</p>
                  </div>
                  <div className="report-timeline-item">
                    <strong>Export package</strong>
                    <p>{document.export_package?.status || 'Not started'}</p>
                  </div>
                  <div className="report-timeline-item">
                    <strong>Announcement</strong>
                    <p>{document.announcement?.status || 'Pending'}</p>
                  </div>
                </div>
              </section>
            </div>

            <section className="dashboard-panel report-panel">
              <h3>Files and deliverables</h3>
              <div className="result-grid">
                {(document.artifacts || []).map((artifact, index) => (
                  <article key={`${artifact.file_name || artifact.format || 'artifact'}-${index}`} className="mini-card">
                    <span>{artifact.format || 'artifact'}</span>
                    <strong>{artifact.file_name || 'Generated file'}</strong>
                    <p>{artifact.blob_url || artifact.storage_ref || 'Stored'}</p>
                    {artifact.file_name && (
                      <button
                        className="status-btn"
                        onClick={() => void handleDownloadArtifact(artifact.file_name!)}
                      >
                        Download
                      </button>
                    )}
                  </article>
                ))}
                {(document.export_package?.artifacts || []).map((artifact, index) => (
                  <article key={`export-${artifact.file_name || artifact.format || 'artifact'}-${index}`} className="mini-card">
                    <span>{artifact.format || 'export'}</span>
                    <strong>{artifact.file_name || 'Export package file'}</strong>
                    <p>{artifact.blob_url || artifact.storage_ref || 'Stored'}</p>
                    {artifact.file_name && (
                      <button
                        className="status-btn"
                        onClick={() => void handleDownloadArtifact(artifact.file_name!)}
                      >
                        Download
                      </button>
                    )}
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}

function saveHistory(msgs: ChatMessage[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(msgs.slice(-50))) // keep last 50
  } catch { /* quota exceeded — ignore */ }
}

let _msgId = 0
function nextId(): string {
  _msgId += 1
  return `msg_${Date.now()}_${_msgId}`
}

function ChatView() {
  const { user, token, logout } = useAuth()
  const authHeader = token && token !== 'dev-session' ? `Bearer ${token}` : undefined
  const isDemoPath = window.location.pathname === DEMO_PATH || window.location.pathname.startsWith(`${DEMO_PATH}/`)
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    // Seed welcome if no history
    const stored = loadHistory()
    if (stored.length > 0) return stored
    return [
      {
        id: nextId(),
        role: 'assistant',
        text: `Welcome, ${user?.email || 'Guest'}. Ask about multifamily properties, deal pipeline, market analytics, or brokerage activities — I will route through the right systems and synthesize a comprehensive response.`,
      },
    ]
  })
  const [view, setView] = useState<View>('chat')
  const [selectedDocumentId, setSelectedDocumentId] = useState<number | null>(null)
  const [showPrompts, setShowPrompts] = useState(true)
  const {
    activeDemoScenario,
    currentPrompt,
    demoStepIndex,
    isDemoComplete,
    defaultDemoScenario,
    startDemoMode,
    resetDemoMode,
    exitDemoMode,
    selectDemoPrompt,
    advanceDemoStep,
  } = useDemoLauncher()
  const [demoRoutePrimed, setDemoRoutePrimed] = useState(false)

  // Streaming state
  const [streamingText, setStreamingText] = useState('')
  const [activeTools, setActiveTools] = useState<LiveTool[]>([])
  const [completedTools, setCompletedTools] = useState<LiveTool[]>([])

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const finalDataRef = useRef<ChatResponse | null>(null)

  // Auto-scroll to bottom during streaming
  useEffect(() => {
    if (loading) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'auto' })
    }
  }, [streamingText, activeTools, completedTools, loading])

  // Save history when messages change (debounced via effect)
  useEffect(() => {
    if (messages.length > 0) {
      saveHistory(messages)
    }
  }, [messages])

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!isDemoPath || demoRoutePrimed || activeDemoScenario) {
      return
    }
    setShowPrompts(true)
    setInput(startDemoMode())
    setDemoRoutePrimed(true)
  }, [activeDemoScenario, demoRoutePrimed, isDemoPath, startDemoMode])

  const statusText = useMemo(() => {
    if (loading) {
      const calling = activeTools.filter((t) => t.status === 'calling')
      if (calling.length > 0) return `🔍 Querying: ${calling.map((t) => t.label.split(' → ')[0]).join(', ')}...`
      return 'Generating response...'
    }
    return 'Evie · Multifamily Intelligence · Ready'
  }, [loading, activeTools])

  function updateDocumentAction(messageId: string, nextAction: DocumentAction) {
    setMessages((prev) => prev.map((msg) => {
      if (msg.id !== messageId || !msg.data?.document_actions) {
        return msg
      }
      const currentActions = msg.data.document_actions
      const existingIndex = currentActions.findIndex((action) => action.id === nextAction.id)
      const replacementIndex = existingIndex >= 0
        ? existingIndex
        : currentActions.findIndex((action) => action.document_type === nextAction.document_type && action.title === nextAction.title)
      const updatedActions = replacementIndex >= 0
        ? currentActions.map((action, index) => (index === replacementIndex ? nextAction : action))
        : [...currentActions, nextAction]
      return {
        ...msg,
        data: {
          ...msg.data,
          document_actions: updatedActions,
        },
      }
    }))
  }

  function clearChat() {
    const welcome: ChatMessage = {
      id: nextId(),
      role: 'assistant',
      text: `Chat cleared. How can I assist you, ${user?.email || 'Guest'}?`,
    }
    setMessages([welcome])
    setShowPrompts(true)
    if (activeDemoScenario) {
      setInput(resetDemoMode())
    }
    saveHistory([welcome])
  }

  function openReport(documentActionId: number) {
    setSelectedDocumentId(documentActionId)
    setView('report')
  }

  async function sendMessage(textOverride?: string) {
    const text = (textOverride ?? input).trim()
    if (!text || loading) return

    const userMsg: ChatMessage = { id: nextId(), role: 'user', text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setShowPrompts(false)
    setLoading(true)
    setStreamingText('')
    setActiveTools([])
    setCompletedTools([])
    finalDataRef.current = null

    try {
      const history = messages
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({ role: m.role, content: m.text }))

      const res = await fetch(`${ORCHESTRATOR_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({ message: text, user_id: user?.email, history }),
      })

      if (!res.ok) {
        const errText = await res.text()
        if (res.status === 401) {
          setMessages((prev) => [
            ...prev,
            { id: nextId(), role: 'assistant', text: 'Your session has expired. Please sign in again to continue.' },
          ])
          logout()
          return
        }
        const friendly = res.status >= 500
          ? 'I ran into a problem on the server while answering. Please try again in a moment.'
          : 'I could not process that request. Please try rephrasing or try again.'
        const detailError = new Error(friendly)
        ;(detailError as Error & { detail?: string }).detail = `HTTP ${res.status}: ${errText}`
        throw detailError
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullReply = ''
      let streamErrorMsg = ''
      let toolSeq = 0
      const liveActive: LiveTool[] = []
      const liveCompleted: LiveTool[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE events: each event is "data: <json>\n\n"
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || '' // keep incomplete last part

        for (const part of parts) {
          const dataLine = part.trim()
          if (!dataLine.startsWith('data: ')) continue
          const jsonStr = dataLine.slice(6)
          if (!jsonStr) continue

          let event: any
          try {
            event = JSON.parse(jsonStr)
          } catch {
            continue
          }

          switch (event.type) {
            case 'token':
              fullReply += event.content
              setStreamingText(fullReply)
              break

            case 'tool':
              if (event.status === 'calling') {
                toolSeq += 1
                liveActive.push({ id: `${event.name}-${toolSeq}`, name: event.name, label: event.label, status: 'calling' })
              } else if (event.status === 'done' || event.status === 'error') {
                const matchIndex = liveActive.findIndex((t) => t.name === event.name)
                toolSeq += 1
                const finished: LiveTool = {
                  id: matchIndex >= 0 ? liveActive[matchIndex].id : `${event.name}-${toolSeq}`,
                  name: event.name,
                  label: event.label,
                  status: event.status,
                  summary: event.summary,
                }
                if (matchIndex >= 0) liveActive.splice(matchIndex, 1)
                liveCompleted.push(finished)
              }
              setActiveTools([...liveActive])
              setCompletedTools([...liveCompleted])
              break

            case 'done':
              fullReply = event.reply || fullReply
              finalDataRef.current = {
                reply: fullReply,
                tool_calls: event.tool_calls || [],
                mcp_results: event.mcp_results || [],
                work_packet: event.work_packet || undefined,
                document_actions: event.document_actions || [],
              }
              break

            case 'error':
              streamErrorMsg = event.message || 'Unknown error'
              break
          }
        }
      }

      // Finalize the streaming message
      const finalText = streamErrorMsg
        ? 'I ran into a problem while putting that answer together. Please try again in a moment.'
        : (fullReply || 'I did not get a response back. Please try again.')

      if (activeDemoScenario && text === currentPrompt) {
        const nextPrompt = advanceDemoStep(text)
        if (nextPrompt) {
          setInput(nextPrompt)
        }
      }

      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: 'assistant',
        text: finalText,
        data: finalDataRef.current ?? undefined,
        errorDetail: streamErrorMsg || undefined,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const isNetworkError = err instanceof TypeError
      const friendly = isNetworkError
        ? 'I am having trouble reaching the data services right now. Please check the connection and try again.'
        : err instanceof Error ? err.message : 'Something went wrong. Please try again.'
      const detail = err instanceof Error ? (err as Error & { detail?: string }).detail || (isNetworkError ? err.message : undefined) : undefined
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: friendly, errorDetail: detail },
      ])
    } finally {
      setLoading(false)
      setStreamingText('')
      setActiveTools([])
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (view === 'settings' || view === 'service_health') {
    return <Suspense fallback={<div className="dashboard-loading">Loading settings panel...</div>}><SettingsPage initialTab="service_health" onBack={() => setView('chat')} /></Suspense>
  }

  if (view === 'admin') {
    return <Suspense fallback={<div className="dashboard-loading">Loading operations console...</div>}><AdminPage onBack={() => setView('chat')} /></Suspense>
  }

  if (view === 'performance') {
    return <PerformanceDashboardView userId={user?.email} onNavigate={setView} />
  }

  if (view === 'network') {
    return <NetworkDashboardView userId={user?.email} onNavigate={setView} />
  }

  if (view === 'documents') {
    return <DocumentsView userId={user?.email} authHeader={authHeader} onNavigate={setView} onOpenReport={openReport} />
  }

  if (view === 'outbox') {
    return <OutboxView authHeader={authHeader} onNavigate={setView} onOpenReport={openReport} />
  }

  if (view === 'report' && selectedDocumentId) {
    return <ReportViewer documentActionId={selectedDocumentId} authHeader={authHeader} onNavigate={setView} />
  }

  const hasConversation = messages.length > 1

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />

      <TopNav
        currentView={view}
        onNavigate={setView}
        onClear={hasConversation ? clearChat : undefined}
      />

      <header className="hero hero-chat">
        {IS_DEV_DEMO && <div className="mode-badge">Demo mode</div>}
        <p className="eyebrow">Operations workspace</p>
        <h1>Workspace Intelligence</h1>
        <p className="subtitle">
          Ask about properties, deals, market data, or documents — Evie routes each request through the right systems.
        </p>
      </header>

      {/* Recommended workflows — first-run only */}
      {showPrompts && !loading && !hasConversation && (
        <>
          <div className="section-label-row">
            <span className="section-label">Recommended workflows</span>
            <span className="section-label-meta">{PLAYBOOKS.length} options</span>
          </div>
          <div className="playbook-grid">
            {PLAYBOOKS.map((playbook) => (
              <button
                key={playbook.id}
                className="playbook-card"
                onClick={() => sendMessage(playbook.question)}
                disabled={loading}
              >
                <span className="playbook-eyebrow">{playbook.eyebrow}</span>
                <strong>{playbook.title}</strong>
                <p>{playbook.question}</p>
                <div className="playbook-output-row">
                  {playbook.outputs.map((output) => (
                    <span key={output} className="playbook-pill">{output}</span>
                  ))}
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      {/* Quick prompts — always reachable */}
      {!loading && (
        <>
          <div className="section-label-row">
            <span className="section-label">Quick prompts</span>
            <span className="section-label-meta">{SUGGESTED_PROMPTS.length} shortcuts</span>
          </div>
          <div className="suggested-prompts">
            {SUGGESTED_PROMPTS.map((p) => (
              <button
                key={p.query}
                className="prompt-chip"
                onClick={() => sendMessage(p.query)}
                disabled={loading}
              >
                <span className="prompt-icon">{p.icon}</span>
                <span className="prompt-label">{p.label}</span>
              </button>
            ))}
          </div>
        </>
      )}

      <div className="chat-shell">
        {/* Status Bar */}
        <div className="status">
          <div className="status-meta">
            <span>{statusText}</span>
          </div>
        </div>

        {/* Messages */}
        <div className="messages" aria-live="polite">
          {messages.map((msg) => (
            <div key={msg.id} className={`bubble ${msg.role}`}>
              <div className="label">{msg.role === 'user' ? 'You' : 'Agent'}</div>
              <div
                className="text prose"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
              />
              {msg.errorDetail && (
                <details className="bubble-error-detail">
                  <summary>Technical details</summary>
                  <pre>{msg.errorDetail}</pre>
                </details>
              )}
              {msg.data?.document_actions?.map((action) => (
                <div key={action.id} className="message-section">
                  <DocumentWorkflowPanel
                    action={action}
                    orchestratorUrl={ORCHESTRATOR_URL}
                    userId={user?.email}
                  authHeader={authHeader}
                  workPacketId={msg.data?.work_packet?.answer?.summary ? `${msg.id}-${action.document_type}` : msg.id}
                  sourceSummary={msg.data?.work_packet?.answer?.summary || msg.text}
                  onActionChange={(nextAction) => updateDocumentAction(msg.id, nextAction)}
                  onViewReport={openReport}
                />
              </div>
            ))}
              {msg.data?.work_packet && (
                <div className="message-section">
                  <WorkPacketPanel packet={msg.data.work_packet} />
                </div>
              )}
              {msg.data?.tool_calls && msg.data.tool_calls.length > 0 && (
                <div className="message-section">
                  <div className="message-section-header">
                    <span className="message-section-title">Tools used</span>
                    <span className="message-section-meta">{msg.data.tool_calls.length}</span>
                  </div>
                  <div className="tool-bar">
                    {msg.data.tool_calls.map((tc, i) => (
                      <ToolBadge key={`${tc.name}-${i}`} name={tc.name} />
                    ))}
                  </div>
                </div>
              )}
              {msg.data?.mcp_results && msg.data.mcp_results.length > 0 && (
                <div className="message-section">
                  <div className="message-section-header">
                    <span className="message-section-title">Results</span>
                    <span className="message-section-meta">{msg.data.mcp_results.length}</span>
                  </div>
                  <div className="card-panel">
                    {msg.data.mcp_results.map((r, i) => <ResultDeck key={i} result={r} />)}
                  </div>
                </div>
              )}
            </div>
          ))}

          {/* Streaming Message */}
          {loading && (
            <div className="bubble assistant streaming">
              <div className="label">Agent</div>

              {/* Live Tool Calls */}
              {activeTools.length > 0 && (
                <div className="live-tools">
                  {activeTools.map((t) => (
                    <LiveToolBadge key={t.id} name={t.name} label={t.label} status="calling" />
                  ))}
                </div>
              )}

              {/* Completed Tool Calls */}
              {completedTools.length > 0 && (
                <div className="live-tools">
                  {completedTools.map((t) => (
                    <LiveToolBadge
                      key={t.id}
                      name={t.name}
                      label={t.label}
                      status={t.status === 'error' ? 'error' : 'done'}
                      summary={t.summary}
                    />
                  ))}
                </div>
              )}

              {/* Streaming text or typing indicator */}
              {streamingText ? (
                <div
                  className="text prose"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(streamingText) }}
                />
              ) : (
                !activeTools.length && !completedTools.length && (
                  <div className="typing-indicator">
                    <span /><span /><span />
                  </div>
                )
              )}

              {/* Streaming cursor when text is building */}
              {streamingText && <span className="streaming-cursor">▊</span>}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <section className="demo-launcher" aria-label="Guided demo mode">
          <div className="demo-launcher-header">
            <div>
              <span className="demo-launcher-eyebrow">
                {isDemoComplete ? 'Guided demo complete' : activeDemoScenario ? 'Guided demo active' : 'Presenter flow'}
              </span>
              <h2>{activeDemoScenario?.title || defaultDemoScenario?.title}</h2>
              <p>
                {isDemoComplete
                  ? 'The guided flow is complete. Ask a follow-up or exit demo mode to return to a clean presenter state.'
                  : activeDemoScenario?.description || defaultDemoScenario?.description}
              </p>
            </div>
            <div className="demo-launcher-actions">
              {!activeDemoScenario ? (
                <button className="demo-launcher-button demo-launcher-button-primary" onClick={() => {
                  setShowPrompts(true)
                  setInput(startDemoMode())
                }}>
                  Start guided demo
                </button>
              ) : (
                <>
                  <div className="demo-launcher-step">
                    Step {demoStepIndex + 1} of {activeDemoScenario.prompts.length}
                  </div>
                  <button className="demo-launcher-button" onClick={() => {
                    setShowPrompts(true)
                    setInput(resetDemoMode())
                  }}>
                    Reset demo
                  </button>
                  <button className="demo-launcher-button" onClick={() => {
                    exitDemoMode()
                    setShowPrompts(true)
                    setInput('')
                  }}>
                    Exit demo
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="demo-launcher-prompts" aria-label="Guided demo prompts">
            {(activeDemoScenario?.prompts || defaultDemoScenario?.prompts || []).map((prompt, index) => (
              <button
                key={prompt}
                className={`demo-launcher-prompt${activeDemoScenario && demoStepIndex === index ? ' is-active' : ''}`}
                aria-pressed={!!(activeDemoScenario && demoStepIndex === index)}
                onClick={() => {
                  setInput(selectDemoPrompt(prompt, index))
                  setShowPrompts(true)
                }}
                disabled={loading}
              >
                <span className="demo-launcher-index">{index + 1}</span>
                <span className="demo-launcher-prompt-text">{prompt}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Composer */}
        <div className="composer">
          <div className="composer-top">
            <div className="composer-title">Compose request</div>
            <div className="composer-hint">Enter to send · Shift+Enter for new line</div>
          </div>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about properties, deals, market data, or documents..."
            aria-label="Message Evie"
            rows={4}
          />
          <div className="composer-actions">
            <button className="composer-send" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
              {loading ? 'Thinking…' : 'Send request'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export function App() {
  return (
    <AuthProvider>
      <AppGate />
    </AuthProvider>
  )
}

function AppGate() {
  const { user } = useAuth()
  return user ? <ChatView /> : <LoginPage />
}
