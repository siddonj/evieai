import { useEffect, useMemo, useState } from 'react'
import { useAuth } from './auth'

const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'

type McpServer = {
  key: string
  name: string
  enabled: boolean
  url: string
  has_admin_data: boolean
}

type ConnectorInfo = {
  source_id: string
  display_name: string
  enabled: boolean
  tenant_id: string | null
  capabilities: string[]
}

type ActionRow = {
  action_id: string
  source_id: string
  entity_type: string
  status: string
  risk_level: string
  requires_approval: boolean
  requested_by: string | null
  approved_by: string | null
  idempotency_key: string
  created_at: string
  updated_at: string
  result?: Record<string, any> | null
}

type ApprovalRow = {
  action_id: string
  source_id: string
  entity_type: string
  requested_by: string | null
  risk_level: string
  status: string
  created_at: string
  updated_at: string
}

type ReliabilityResponse = {
  pass: boolean
  checks: Record<string, boolean>
  thresholds: Record<string, any>
  current: Record<string, any>
}

type CircuitState = {
  source_id: string
  state: 'open' | 'closed'
  reason?: string | null
  updated_at: string
}

type Tab = 'data_sources' | 'approvals' | 'service_health'

type SettingsPageProps = {
  initialTab?: Tab
}

type ServiceHealthRow = {
  key: string
  name: string
  enabled: boolean
  cooldown_remaining_seconds: number
  reachable: boolean
  status_code: number | null
  response_ms: number
  health_url: string
  error?: string | null
}

export function SettingsPage({ initialTab = 'data_sources' }: SettingsPageProps) {
  const { logout, user: currentUser } = useAuth()
  const [tab, setTab] = useState<Tab>(initialTab)
  const [userMessage, setUserMessage] = useState('')

  // ─── Data Sources State ─────────────────────────────────────────────
  const [servers, setServers] = useState<McpServer[]>([])
  const [serverLoading, setServerLoading] = useState(false)
  const [dataPreview, setDataPreview] = useState<Record<string, any>>({})
  const [previewLoading, setPreviewLoading] = useState<string | null>(null)
  const [addDataService, setAddDataService] = useState('knowledge_base')
  const [addDataJson, setAddDataJson] = useState('')
  const [addDataMessage, setAddDataMessage] = useState('')

  // ─── Approvals / Actions State ──────────────────────────────────────
  const [actionsLoading, setActionsLoading] = useState(false)
  const [actionsError, setActionsError] = useState('')
  const [actionsMessage, setActionsMessage] = useState('')
  const [actions, setActions] = useState<ActionRow[]>([])
  const [approvals, setApprovals] = useState<ApprovalRow[]>([])
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([])
  const [actionReliability, setActionReliability] = useState<ReliabilityResponse | null>(null)
  const [syncReliability, setSyncReliability] = useState<ReliabilityResponse | null>(null)
  const [selectedConnector, setSelectedConnector] = useState('')
  const [circuitState, setCircuitState] = useState<CircuitState | null>(null)
  const [actionStatusFilter, setActionStatusFilter] = useState('')

  const [serviceHealthRows, setServiceHealthRows] = useState<ServiceHealthRow[]>([])
  const [serviceHealthLoading, setServiceHealthLoading] = useState(false)
  const [serviceHealthMessage, setServiceHealthMessage] = useState('')

  const activeWriteConnectors = useMemo(
    () => connectors.filter((c) => c.capabilities?.includes('write')),
    [connectors],
  )

  // Load MCP config on mount
  useEffect(() => {
    setTab(initialTab)
  }, [initialTab])

  useEffect(() => {
    loadMcpConfig()
  }, [])

  useEffect(() => {
    if (tab === 'approvals') {
      void loadApprovalAdminData()
    }
    if (tab === 'service_health') {
      void loadServiceHealth()
    }
  }, [tab])

  useEffect(() => {
    if (!selectedConnector && activeWriteConnectors.length > 0) {
      setSelectedConnector(activeWriteConnectors[0].source_id)
    }
  }, [activeWriteConnectors, selectedConnector])

  useEffect(() => {
    if (tab === 'approvals' && selectedConnector) {
      void loadCircuit(selectedConnector)
    }
  }, [selectedConnector, tab])

  async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
    const res = await fetch(url, init)
    if (!res.ok) {
      const text = await res.text()
      throw new Error(`HTTP ${res.status}: ${text}`)
    }
    return res.json() as Promise<T>
  }

  async function loadMcpConfig() {
    setServerLoading(true)
    try {
      const data = await fetchJson<{ servers?: McpServer[]; services?: McpServer[] }>(`${ORCHESTRATOR_URL}/admin/mcp-config`)
      const normalized = Array.isArray(data.servers)
        ? data.servers
        : Array.isArray(data.services)
          ? data.services
          : []
      setServers(normalized)
    } catch {
      setUserMessage('Failed to load MCP configuration.')
      setServers([])
    } finally {
      setServerLoading(false)
    }
  }

  async function toggleMcp(key: string, enabled: boolean) {
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/admin/mcp-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, enabled }),
      })
      setServers((prev) => prev.map((s) => (s.key === key ? { ...s, enabled } : s)))
    } catch {
      setUserMessage(`Failed to toggle ${key}.`)
    }
  }

  async function previewData(service: string) {
    setPreviewLoading(service)
    try {
      const data = await fetchJson(`${ORCHESTRATOR_URL}/admin/mcp-data/${service}`)
      setDataPreview((prev) => ({ ...prev, [service]: data }))
    } catch {
      setDataPreview((prev) => ({ ...prev, [service]: { error: 'Failed to load data' } }))
    } finally {
      setPreviewLoading(null)
    }
  }

  async function submitData() {
    setAddDataMessage('')
    if (!addDataJson.trim()) {
      setAddDataMessage('Please enter JSON data.')
      return
    }
    let payload: any
    try {
      payload = JSON.parse(addDataJson)
    } catch {
      setAddDataMessage('Invalid JSON. Please check your syntax.')
      return
    }
    try {
      const result = await fetchJson<any>(`${ORCHESTRATOR_URL}/admin/mcp-data/${addDataService}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (result.error) {
        setAddDataMessage(`Error: ${result.error}`)
      } else {
        setAddDataMessage(`Success: ${result.action} ${result.id || result.category || result.user_id || ''}`)
        setAddDataJson('')
        if (dataPreview[addDataService]) {
          void previewData(addDataService)
        }
      }
    } catch {
      setAddDataMessage('Failed to send data to MCP server.')
    }
  }

  async function loadApprovalAdminData() {
    setActionsLoading(true)
    setActionsError('')
    setActionsMessage('')
    try {
      const [actionsRes, approvalsRes, connectorsRes, actionRelRes, syncRelRes] = await Promise.all([
        fetchJson<{ actions: ActionRow[] }>(`${ORCHESTRATOR_URL}/actions?limit=200`),
        fetchJson<{ approvals: ApprovalRow[] }>(`${ORCHESTRATOR_URL}/actions/approvals?status=pending&limit=200`),
        fetchJson<{ connectors: ConnectorInfo[] }>(`${ORCHESTRATOR_URL}/connectors?include_disabled=true`),
        fetchJson<ReliabilityResponse>(`${ORCHESTRATOR_URL}/actions/reliability`),
        fetchJson<ReliabilityResponse>(`${ORCHESTRATOR_URL}/connectors/sync/reliability`),
      ])

      setActions(actionsRes.actions || [])
      setApprovals(approvalsRes.approvals || [])
      setConnectors(connectorsRes.connectors || [])
      setActionReliability(actionRelRes)
      setSyncReliability(syncRelRes)
    } catch (err) {
      setActionsError(err instanceof Error ? err.message : 'Failed to load approvals admin data')
    } finally {
      setActionsLoading(false)
    }
  }

  async function loadCircuit(sourceId: string) {
    try {
      const state = await fetchJson<CircuitState>(`${ORCHESTRATOR_URL}/actions/circuit?source_id=${encodeURIComponent(sourceId)}`)
      setCircuitState(state)
    } catch {
      setCircuitState(null)
    }
  }

  async function approveAction(actionId: string) {
    setActionsMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/actions/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, decided_by: currentUser?.email || 'admin' }),
      })
      setActionsMessage(`Approved ${actionId}`)
      await loadApprovalAdminData()
    } catch (err) {
      setActionsMessage(`Approve failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    }
  }

  async function rejectAction(actionId: string) {
    const reason = window.prompt('Rejection reason:', 'Rejected by admin') || 'Rejected by admin'
    setActionsMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/actions/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId, decided_by: currentUser?.email || 'admin', reason }),
      })
      setActionsMessage(`Rejected ${actionId}`)
      await loadApprovalAdminData()
    } catch (err) {
      setActionsMessage(`Reject failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    }
  }

  async function executeAction(actionId: string) {
    setActionsMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/actions/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action_id: actionId }),
      })
      setActionsMessage(`Executed ${actionId}`)
      await loadApprovalAdminData()
    } catch (err) {
      setActionsMessage(`Execute failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    }
  }

  async function setCircuit(state: 'open' | 'closed') {
    if (!selectedConnector) return
    const reason = state === 'open'
      ? (window.prompt('Open circuit reason:', 'Manual safety stop') || 'Manual safety stop')
      : (window.prompt('Close circuit reason:', 'Manual reset') || 'Manual reset')

    setActionsMessage('')
    try {
      const next = await fetchJson<CircuitState>(`${ORCHESTRATOR_URL}/actions/circuit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id: selectedConnector, state, reason }),
      })
      setCircuitState(next)
      setActionsMessage(`Circuit ${state} for ${selectedConnector}`)
      await loadApprovalAdminData()
    } catch (err) {
      setActionsMessage(`Circuit update failed: ${err instanceof Error ? err.message : 'unknown error'}`)
    }
  }

  const filteredActions = useMemo(() => {
    if (!actionStatusFilter.trim()) return actions
    return actions.filter((a) => a.status === actionStatusFilter)
  }, [actions, actionStatusFilter])

  async function loadServiceHealth() {
    setServiceHealthLoading(true)
    setServiceHealthMessage('')
    try {
      const data = await fetchJson<{ services?: ServiceHealthRow[] }>(`${ORCHESTRATOR_URL}/admin/mcp-status`)
      setServiceHealthRows(Array.isArray(data.services) ? data.services : [])
    } catch (err) {
      setServiceHealthMessage(err instanceof Error ? err.message : 'Failed to load service health')
      setServiceHealthRows([])
    } finally {
      setServiceHealthLoading(false)
    }
  }

  async function resetService(serviceKey: string) {
    setServiceHealthMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/admin/mcp-reset/${encodeURIComponent(serviceKey)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
      setServiceHealthMessage(`Reset ${serviceKey}`)
      await loadServiceHealth()
    } catch (err) {
      setServiceHealthMessage(err instanceof Error ? err.message : `Failed to reset ${serviceKey}`)
    }
  }

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />
      <header className="hero settings-hero">
        <p className="eyebrow">Settings</p>
        <h1>Admin Console</h1>
        <p className="subtitle">
          Manage data sources and write-back safety controls.
        </p>
      </header>

      <main className="settings-shell">
        {/* Tab Navigation */}
        <div className="settings-tabs">
          <button className={`settings-tab ${tab === 'data_sources' ? 'active' : ''}`} onClick={() => setTab('data_sources')}>
            🧩 Service Status
          </button>
          <button className={`settings-tab ${tab === 'service_health' ? 'active' : ''}`} onClick={() => setTab('service_health')}>
            ⏱️ Service Health
          </button>
          <button className={`settings-tab ${tab === 'approvals' ? 'active' : ''}`} onClick={() => setTab('approvals')}>
            ✅ Approvals
          </button>
        </div>

        {tab === 'data_sources' && (
          <>
            {userMessage && <section className="settings-section"><div className="settings-message">{userMessage}</div></section>}
            <section className="settings-section">
              <h2>MCP Server Status</h2>
              <p className="settings-hint">Toggle MCP servers on or off. Disabled servers will not be available to the AI agent.</p>
              {serverLoading ? (
                <div className="settings-loading">Loading MCP configuration...</div>
              ) : (
                <div className="mcp-server-list">
                  {servers.map((s) => (
                    <div key={s.key} className={`mcp-server-row ${s.enabled ? 'enabled' : 'disabled'}`}>
                      <div className="mcp-server-info">
                        <div className="mcp-server-name">{s.name}</div>
                        <div className="mcp-server-key">{s.key}</div>
                      </div>
                      <label className="mcp-toggle">
                        <input
                          type="checkbox"
                          checked={s.enabled}
                          onChange={(e) => toggleMcp(s.key, e.target.checked)}
                        />
                        <span className="mcp-toggle-slider" />
                      </label>
                      {s.has_admin_data && (
                        <button
                          className="btn-preview"
                          onClick={() => previewData(s.key)}
                          disabled={previewLoading === s.key}
                        >
                          {previewLoading === s.key ? 'Loading...' : 'Preview Data'}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </section>

            {/* Data Preview Panel */}
            {Object.keys(dataPreview).length > 0 && (
              <section className="settings-section">
                <h2>Data Preview</h2>
                {Object.entries(dataPreview).map(([service, data]) => (
                  <div key={service} className="data-preview-panel">
                    <div className="data-preview-header">
                      <span className="data-preview-service">{service.replace('_', ' ').toUpperCase()}</span>
                      <button className="btn-close-preview" onClick={() => setDataPreview((prev) => { const n = { ...prev }; delete n[service]; return n })}>✕</button>
                    </div>
                    <pre className="data-preview-json">{JSON.stringify(data, null, 2)}</pre>
                  </div>
                ))}
              </section>
            )}

            <section className="settings-section">
              <h2>Add Data to MCP Server</h2>
              <p className="settings-hint">
                Upload new documents, user contexts, templates, or analytics categories. Select a server and paste JSON data.
              </p>
              <div className="add-data-form">
                <div className="settings-row">
                  <div className="settings-field">
                    <label>Target MCP Server</label>
                    <select value={addDataService} onChange={(e) => setAddDataService(e.target.value)}>
                      <option value="knowledge_base">📚 Knowledge Base (document object)</option>
                      <option value="memory">🧠 Memory (user_id + context object)</option>
                      <option value="document_generation">📄 Document Generation (document template)</option>
                      <option value="analytics">📊 Analytics (category + data object)</option>
                    </select>
                  </div>
                </div>
                <div className="settings-field">
                  <label>JSON Payload</label>
                  <textarea
                    className="json-textarea"
                    value={addDataJson}
                    onChange={(e) => setAddDataJson(e.target.value)}
                    placeholder={getPlaceholder(addDataService)}
                    rows={10}
                  />
                </div>
                <button onClick={submitData}>Submit Data</button>
                {addDataMessage && <div className={`settings-message ${addDataMessage.startsWith('Success') ? 'success' : ''}`}>{addDataMessage}</div>}
              </div>
            </section>
          </>
        )}

        {tab === 'service_health' && (
          <>
            <section className="settings-section">
              <div className="approval-toolbar">
                <h2>MCP Service Health</h2>
                <button onClick={() => void loadServiceHealth()} disabled={serviceHealthLoading}>
                  {serviceHealthLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
              <p className="settings-hint">
                Live status, response time, and reset controls for each MCP service.
              </p>
              {serviceHealthMessage && <div className="settings-message">{serviceHealthMessage}</div>}

              <table className="users-table approvals-table">
                <thead>
                  <tr>
                    <th>Service</th>
                    <th>Enabled</th>
                    <th>Reachable</th>
                    <th>Status</th>
                    <th>Response (ms)</th>
                    <th>Cooldown</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {serviceHealthRows.map((row) => (
                    <tr key={row.key}>
                      <td>{row.name}</td>
                      <td><span className={`status-pill ${row.enabled ? 'completed' : 'failed'}`}>{row.enabled ? 'on' : 'off'}</span></td>
                      <td><span className={`status-pill ${row.reachable ? 'completed' : 'failed'}`}>{row.reachable ? 'yes' : 'no'}</span></td>
                      <td>{row.status_code ?? 'n/a'}</td>
                      <td>{row.response_ms}</td>
                      <td>{row.cooldown_remaining_seconds > 0 ? `${row.cooldown_remaining_seconds}s` : '-'}</td>
                      <td>
                        <button onClick={() => void resetService(row.key)}>Reset</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}

        {tab === 'approvals' && (
          <>
            <section className="settings-section">
              <div className="approval-toolbar">
                <h2>Write-Back Reliability</h2>
                <button onClick={() => void loadApprovalAdminData()} disabled={actionsLoading}>
                  {actionsLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
              {actionsError && <div className="settings-message">{actionsError}</div>}
              {actionsMessage && <div className="settings-message success">{actionsMessage}</div>}

              <div className="approval-grid">
                <ReliabilityCard title="Actions" data={actionReliability} />
                <ReliabilityCard title="Connector Sync" data={syncReliability} />
              </div>
            </section>

            <section className="settings-section">
              <h2>Circuit Breaker Controls</h2>
              <div className="settings-row">
                <div className="settings-field">
                  <label>Connector</label>
                  <select value={selectedConnector} onChange={(e) => setSelectedConnector(e.target.value)}>
                    {activeWriteConnectors.map((c) => (
                      <option key={c.source_id} value={c.source_id}>{c.display_name} ({c.source_id})</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="circuit-row">
                <span className={`circuit-pill ${circuitState?.state === 'open' ? 'open' : 'closed'}`}>
                  {circuitState ? `${circuitState.state.toUpperCase()}` : 'UNKNOWN'}
                </span>
                <button className="btn-danger" onClick={() => void setCircuit('open')} disabled={!selectedConnector}>Open</button>
                <button onClick={() => void setCircuit('closed')} disabled={!selectedConnector}>Close</button>
              </div>
              {circuitState && (
                <div className="settings-hint">
                  last update: {new Date(circuitState.updated_at).toLocaleString()} {circuitState.reason ? `· ${circuitState.reason}` : ''}
                </div>
              )}
            </section>

            <section className="settings-section">
              <h2>Pending Approval Queue</h2>
              {approvals.length === 0 ? (
                <div className="settings-hint">No pending approvals.</div>
              ) : (
                <table className="users-table approvals-table">
                  <thead>
                    <tr>
                      <th>Action</th>
                      <th>Source</th>
                      <th>Entity</th>
                      <th>Risk</th>
                      <th>Requested By</th>
                      <th>Created</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {approvals.map((a) => (
                      <tr key={a.action_id}>
                        <td className="mono-cell">{a.action_id.slice(0, 12)}…</td>
                        <td>{a.source_id}</td>
                        <td>{a.entity_type}</td>
                        <td><span className={`risk-pill ${a.risk_level}`}>{a.risk_level}</span></td>
                        <td>{a.requested_by || 'system'}</td>
                        <td>{new Date(a.created_at).toLocaleString()}</td>
                        <td className="action-buttons-cell">
                          <button onClick={() => void approveAction(a.action_id)}>Approve</button>
                          <button className="btn-danger" onClick={() => void rejectAction(a.action_id)}>Reject</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>

            <section className="settings-section">
              <div className="approval-toolbar">
                <h2>Action History</h2>
                <div className="settings-field action-filter-field">
                  <label>Status Filter</label>
                  <select value={actionStatusFilter} onChange={(e) => setActionStatusFilter(e.target.value)}>
                    <option value="">All</option>
                    <option value="pending_approval">pending_approval</option>
                    <option value="approved">approved</option>
                    <option value="rejected">rejected</option>
                    <option value="completed">completed</option>
                    <option value="failed">failed</option>
                  </select>
                </div>
              </div>

              <table className="users-table approvals-table">
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>Status</th>
                    <th>Risk</th>
                    <th>Source</th>
                    <th>Entity</th>
                    <th>Updated</th>
                    <th>Op</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredActions.map((a) => (
                    <tr key={a.action_id}>
                      <td className="mono-cell">{a.action_id.slice(0, 12)}…</td>
                      <td><span className={`status-pill ${a.status}`}>{a.status}</span></td>
                      <td><span className={`risk-pill ${a.risk_level}`}>{a.risk_level}</span></td>
                      <td>{a.source_id}</td>
                      <td>{a.entity_type}</td>
                      <td>{new Date(a.updated_at).toLocaleString()}</td>
                      <td className="action-buttons-cell">
                        {(a.status === 'approved' || (!a.requires_approval && a.status !== 'completed' && a.status !== 'failed' && a.status !== 'rejected')) && (
                          <button onClick={() => void executeAction(a.action_id)}>Execute</button>
                        )}
                        {a.status === 'pending_approval' && (
                          <>
                            <button onClick={() => void approveAction(a.action_id)}>Approve</button>
                            <button className="btn-danger" onClick={() => void rejectAction(a.action_id)}>Reject</button>
                          </>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}

        <section className="settings-footer">
          <button className="btn-logout" onClick={logout}>Sign Out</button>
        </section>
      </main>
    </div>
  )
}

function ReliabilityCard({ title, data }: { title: string; data: ReliabilityResponse | null }) {
  return (
    <div className="reliability-card">
      <div className="reliability-header">
        <strong>{title}</strong>
        <span className={`status-pill ${data?.pass ? 'completed' : 'failed'}`}>{data?.pass ? 'PASS' : 'FAIL'}</span>
      </div>
      {data ? (
        <>
          <div className="settings-hint">checks</div>
          <ul className="reliability-list">
            {Object.entries(data.checks).map(([k, v]) => (
              <li key={k}><span>{k}</span><span>{v ? '✅' : '❌'}</span></li>
            ))}
          </ul>
          <div className="settings-hint">current</div>
          <pre className="data-preview-json reliability-json">{JSON.stringify(data.current, null, 2)}</pre>
        </>
      ) : (
        <div className="settings-hint">not loaded</div>
      )}
    </div>
  )
}

function getPlaceholder(service: string): string {
  switch (service) {
    case 'knowledge_base':
      return JSON.stringify({
        document: {
          id: 'sop-009',
          type: 'SOP',
          category: 'IT Security',
          title: 'Cloud Access Security Broker Policy',
          version: '1.0',
          effective_date: '2026-05-01',
          owner: 'CISO',
          status: 'Active',
          summary: 'All cloud service access must go through the approved CASB.',
          key_points: ['CASB required for all SaaS', 'DLP policies enforced at egress'],
          related: ['sop-001', 'sop-002'],
        },
      }, null, 2)
    case 'memory':
      return JSON.stringify({
        user_id: 'new-user',
        context: {
          user_id: 'new-user',
          profile: { name: 'Sam Taylor', role: 'Product Manager', department: 'Product' },
          preferences: { data_focus: ['roadmap', 'user_feedback', 'metrics'] },
          recent_topics: ['Q3 roadmap planning'],
          bookmarks: [],
        },
      }, null, 2)
    case 'document_generation':
      return JSON.stringify({
        document: {
          id: 'doc-005',
          type: 'product_roadmap',
          title: 'Q3 2026 Product Roadmap',
          generated_at: '2026-05-06T10:00:00Z',
          status: 'Generated',
          pages: 3,
          word_count: 1200,
          sections: [{ heading: 'Overview', content: '...', key_metrics: [] }],
          action_items: [],
          tags: ['product', 'roadmap'],
        },
      }, null, 2)
    case 'analytics':
      return JSON.stringify({
        category: 'product',
        data: {
          category: 'Product Metrics',
          kpi_cards: [{ name: 'NPS', value: '72', change: '+4', period: 'QoQ', status: 'positive', target: '70', target_status: 'exceeded' }],
          trends: [],
          insights: ['NPS at all-time high'],
        },
      }, null, 2)
    default:
      return '{"document": {...}}'
  }
}
