import { useEffect, useMemo, useRef, useState } from 'react'
import { marked } from 'marked'
import { AuthProvider, useAuth } from './auth'
import { LoginPage } from './LoginPage'
import { SettingsPage } from './SettingsPage'
import { AdminPage } from './AdminPage'
import type { ChatResponse } from './Cards'
import { ResultDeck, ToolBadge, LiveToolBadge } from './Cards'

type View = 'chat' | 'settings' | 'service_health' | 'performance' | 'network' | 'admin'

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
}

type LegacyChatMessage = {
  id?: unknown
  role?: unknown
  text?: unknown
  content?: unknown
  data?: unknown
}

type LiveTool = {
  name: string
  label: string
  status: 'calling' | 'done' | 'error'
  summary?: string
}

const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'
const STORAGE_KEY = 'aiagent_chat_history'

// Multifamily & brokerage suggested prompts
const SUGGESTED_PROMPTS = [
  { icon: '🏢', label: 'Portfolio overview', query: 'Show me our full multifamily portfolio — all properties, total units, occupancy rate, and average rent.' },
  { icon: '📊', label: 'Deal pipeline', query: 'Show me the full deal pipeline — all active deals, their stages, offer prices, and commission projections.' },
  { icon: '📈', label: 'Market analytics', query: 'Show me Memphis multifamily market analytics — cap rates, occupancy trends, and new supply.' },
  { icon: '📄', label: 'Portfolio performance', query: 'Generate a portfolio performance summary with NOI, cap rates, and rent growth across all properties.' },
  { icon: '🏠', label: 'Properties by status', query: 'List all properties by status — active, under contract, and recently sold.' },
  { icon: '👥', label: 'Key contacts', query: 'Show me my key contacts — owners, brokers, and investors in the Memphis market.' },
  { icon: '💰', label: 'Commission tracker', query: 'What is my YTD commission income and how does it compare to last year?' },
  { icon: '🔍', label: 'Upcoming activities', query: 'What are my upcoming property tours, inspections, and deal deadlines this month?' },
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
    return marked.parse(text || '', { breaks: true }) as string
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

function PerformanceDashboardView({ userId, onBack }: { userId?: string; onBack: () => void }) {
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
      <header className="hero">
        <p className="eyebrow">Live Operations</p>
        <h1>Performance Dashboard</h1>
        <p className="subtitle">
          Portfolio, pipeline, and execution performance in one view.
        </p>
      </header>

      <div className="dashboard-shell">
        <div className="dashboard-toolbar">
          <button className="status-btn" onClick={onBack}>← Back to Chat</button>
          <button className="status-btn" onClick={() => void loadDashboard()} disabled={loading}>⟳ Refresh</button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}

        {loading && !data && <div className="dashboard-loading">Loading dashboard...</div>}

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

function NetworkDashboardView({ userId, onBack }: { userId?: string; onBack: () => void }) {
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
      <header className="hero">
        <p className="eyebrow">Network Operations</p>
        <h1>Network Dashboard</h1>
        <p className="subtitle">Wireless reliability, event pressure, and site-level performance across provider sources.</p>
      </header>

      <div className="dashboard-shell">
        <div className="dashboard-toolbar">
          <button className="status-btn" onClick={onBack}>← Back to Chat</button>
          <button className="status-btn" onClick={() => void loadDashboard()} disabled={loading}>⟳ Refresh</button>
        </div>

        {error && <div className="dashboard-error">{error}</div>}
        {loading && !data && <div className="dashboard-loading">Loading network dashboard...</div>}

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
  const { user, isAdmin, logout } = useAuth()
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
  const [showPrompts, setShowPrompts] = useState(true)

  // Streaming state
  const [streamingText, setStreamingText] = useState('')
  const [activeTools, setActiveTools] = useState<LiveTool[]>([])
  const [completedTools, setCompletedTools] = useState<LiveTool[]>([])
  const [streamError, setStreamError] = useState('')

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

  const statusText = useMemo(() => {
    if (loading) {
      const calling = activeTools.filter((t) => t.status === 'calling')
      if (calling.length > 0) return `🔍 Querying: ${calling.map((t) => t.label.split(' → ')[0]).join(', ')}...`
      return 'Generating response...'
    }
    return `Connected to ${ORCHESTRATOR_URL}  |  User: ${user?.email}  |  MF Brokerage`
  }, [loading, activeTools, user])

  function clearChat() {
    const welcome: ChatMessage = {
      id: nextId(),
      role: 'assistant',
      text: `Chat cleared. How can I assist you, ${user?.email || 'Guest'}?`,
    }
    setMessages([welcome])
    setShowPrompts(true)
    saveHistory([welcome])
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
    setStreamError('')
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
        throw new Error(`HTTP ${res.status}: ${errText}`)
      }

      const reader = res.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullReply = ''

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
                setActiveTools((prev) => [...prev, { name: event.name, label: event.label, status: 'calling' }])
              } else if (event.status === 'done') {
                setActiveTools((prev) => prev.filter((t) => t.name !== event.name))
                setCompletedTools((prev) => [...prev, { name: event.name, label: event.label, status: 'done', summary: event.summary }])
              } else if (event.status === 'error') {
                setActiveTools((prev) => prev.filter((t) => t.name !== event.name))
                setCompletedTools((prev) => [...prev, { name: event.name, label: event.label, status: 'error', summary: event.summary }])
              }
              break

            case 'done':
              fullReply = event.reply || fullReply
              finalDataRef.current = {
                reply: fullReply,
                tool_calls: event.tool_calls || [],
                mcp_results: event.mcp_results || [],
              }
              break

            case 'error':
              setStreamError(event.message || 'Unknown error')
              break
          }
        }
      }

      // Finalize the streaming message
      const finalText = streamError ? `I encountered an error: ${streamError}` : (fullReply || 'No response from orchestrator.')

      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: 'assistant',
        text: finalText,
        data: finalDataRef.current ?? undefined,
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setMessages((prev) => [
        ...prev,
        { id: nextId(), role: 'assistant', text: `I could not reach the orchestrator. ${message}` },
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

  if (view === 'settings') {
    return <SettingsPage initialTab="service_health" />
  }

  if (view === 'service_health') {
    return <SettingsPage initialTab="service_health" />
  }

  if (view === 'admin') {
    return <AdminPage onBack={() => setView('chat')} />
  }

  if (view === 'performance') {
    return <PerformanceDashboardView userId={user?.email} onBack={() => setView('chat')} />
  }

  if (view === 'network') {
    return <NetworkDashboardView userId={user?.email} onBack={() => setView('chat')} />
  }

  const hasConversation = messages.length > 1

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />

      <header className="hero hero-chat">
        <div className="evie-brand">
          <div className="evie-mark" aria-hidden="true">
            <span className="mark-segment mark-segment-top" />
            <span className="mark-segment mark-segment-mid" />
            <span className="mark-segment mark-segment-bot" />
          </div>
          <div className="evie-wordmark">
            <div className="evie-wordmark-title">EVIEAI</div>
            <div className="evie-wordmark-tag">MULTIFAMILY AI SOLUTIONS</div>
          </div>
        </div>
        <p className="eyebrow">AI-Powered Agentic Q&A</p>
        <h1>Workspace Intelligence Console</h1>
        <p className="subtitle">
          Ask natural-language questions across properties, deals, contacts, market data, and documents — the agent routes your query through the right tools and synthesizes a comprehensive answer.
        </p>
      </header>

      {/* Suggested Prompts */}
      {showPrompts && !loading && (
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
      )}

      <div className="chat-shell">
        {/* Status Bar */}
        <div className="status">
          <span>{statusText}</span>
          <span className="status-actions">
            {isAdmin && (
              <>
                <button className="status-btn" onClick={() => setView('admin')} title="System Health">
                  🖥️ Admin
                </button>
                <button className="status-btn" onClick={() => setView('settings')} title="Settings">
                  ⚙️ Settings
                </button>
              </>
            )}
            {!isAdmin && (
              <button className="status-btn" onClick={() => setView('settings')} title="Settings">
                ⚙️ Settings
              </button>
            )}
            <button className="status-btn" onClick={() => setView('service_health')} title="Service Health">
              ⏱️ Services
            </button>
            <button className="status-btn" onClick={() => setView('performance')} title="Performance Dashboard">
              📊 Dashboard
            </button>
            <button className="status-btn" onClick={() => setView('network')} title="Network Dashboard">
              📡 Network Dashboard
            </button>
            {hasConversation && (
              <button className="status-btn" onClick={clearChat} title="Clear conversation">
                🗑️ Clear
              </button>
            )}
            <button className="status-btn" onClick={logout} title="Logout">
              🚪 Logout
            </button>
          </span>
        </div>

        {/* Messages */}
        <div className="messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`bubble ${msg.role}`}>
              <div className="label">{msg.role === 'user' ? 'You' : 'Agent'}</div>
              <div
                className="text prose"
                dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.text) }}
              />
              {msg.data?.tool_calls && msg.data.tool_calls.length > 0 && (
                <div className="tool-bar">
                  {msg.data.tool_calls.map((tc, i) => (
                    <ToolBadge key={i} name={tc.name} />
                  ))}
                </div>
              )}
              {msg.data?.mcp_results && msg.data.mcp_results.length > 0 && (
                <div className="card-panel">
                  {msg.data.mcp_results.map((r, i) => <ResultDeck key={i} result={r} />)}
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
                    <LiveToolBadge key={t.name} name={t.name} label={t.label} status="calling" />
                  ))}
                </div>
              )}

              {/* Completed Tool Calls */}
              {completedTools.length > 0 && (
                <div className="live-tools">
                  {completedTools.map((t) => (
                    <LiveToolBadge
                      key={t.name}
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

        {/* Composer */}
        <div className="composer">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about properties, deals, market data, or documents..."
            rows={4}
            disabled={loading}
          />
          <button className="composer-send" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
            {loading ? 'Thinking…' : 'Send'}
          </button>
          <div className="composer-hint">Enter to send · Shift+Enter for new line</div>
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

