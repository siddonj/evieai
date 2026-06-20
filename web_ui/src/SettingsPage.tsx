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

type Tab = 'data_sources' | 'approvals' | 'service_health' | 'gateway'

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

type LlmProviderStatus = {
  provider: string
  supported: boolean
  configured: boolean
  model: string
  endpoint: string | null
  missing_env_vars: string[]
  error: string | null
}

type GatewayConfig = {
  enabled: boolean
  configured: boolean
  base_url: string
  base_url_masked: string | null
  auth_mode: string
  timeout_seconds: number
  fallback_mode: string
  cache_enabled: boolean
  rollout: {
    state: 'live' | 'canary' | 'paused'
    canary_traffic_pct: number
    reason?: string
    updated_at: string
  }
  last_sync_at: string | null
  disabled_routes: string[]
  upstreams: Array<{
    service: string
    target_url: string
    enabled: boolean
  }>
}

type GatewayHealth = {
  enabled: boolean
  configured: boolean
  reachable_services: number
  total_services: number
  health_percentage: number
  timestamp: string
  services: Array<{
    key?: string
    name?: string
    service?: string
    reachable: boolean
    response_ms?: number
    response_time_ms?: number
    status_code?: number | null
    error?: string | null
  }>
}

export function SettingsPage({ initialTab = 'service_health' }: SettingsPageProps) {
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
  const [llmStatus, setLlmStatus] = useState<LlmProviderStatus | null>(null)
  const [llmStatusLoading, setLlmStatusLoading] = useState(false)
  const [gatewayLoading, setGatewayLoading] = useState(false)
  const [gatewayMessage, setGatewayMessage] = useState('')
  const [gatewayConfig, setGatewayConfig] = useState<GatewayConfig | null>(null)
  const [gatewayHealth, setGatewayHealth] = useState<GatewayHealth | null>(null)
  const [gatewayReliability, setGatewayReliability] = useState<ReliabilityResponse | null>(null)
  const [gatewayCanaryPct, setGatewayCanaryPct] = useState(100)
  const [gatewayRolloutReason, setGatewayRolloutReason] = useState('')

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
    void loadLlmProviderStatus()
  }, [])

  useEffect(() => {
    if (tab === 'approvals') {
      void loadApprovalAdminData()
    }
    if (tab === 'service_health') {
      void loadServiceHealth()
    }
    if (tab === 'gateway') {
      void loadGatewayAdminData()
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

  async function loadLlmProviderStatus() {
    setLlmStatusLoading(true)
    try {
      const data = await fetchJson<LlmProviderStatus>(`${ORCHESTRATOR_URL}/admin/llm-provider`)
      setLlmStatus(data)
    } catch {
      setLlmStatus(null)
    } finally {
      setLlmStatusLoading(false)
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

  async function loadGatewayAdminData() {
    setGatewayLoading(true)
    setGatewayMessage('')
    try {
      const [config, health, reliability] = await Promise.all([
        fetchJson<GatewayConfig>(`${ORCHESTRATOR_URL}/admin/gateway-config`),
        fetchJson<GatewayHealth>(`${ORCHESTRATOR_URL}/admin/gateway-health`),
        fetchJson<ReliabilityResponse>(`${ORCHESTRATOR_URL}/admin/gateway-reliability`),
      ])
      setGatewayConfig(config)
      setGatewayHealth(health)
      setGatewayReliability(reliability)
      setGatewayCanaryPct(config.rollout?.canary_traffic_pct ?? 100)
    } catch (err) {
      setGatewayMessage(err instanceof Error ? err.message : 'Failed to load gateway admin data')
    } finally {
      setGatewayLoading(false)
    }
  }

  async function toggleGateway(enabled: boolean) {
    setGatewayMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/admin/gateway-toggle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled }),
      })
      setGatewayMessage(`Gateway ${enabled ? 'enabled' : 'disabled'}`)
      await loadGatewayAdminData()
    } catch (err) {
      setGatewayMessage(err instanceof Error ? err.message : 'Failed to toggle gateway')
    }
  }

  async function applyGatewayRollout(state: 'live' | 'canary' | 'paused') {
    setGatewayMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/admin/gateway-rollout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state,
          canary_traffic_pct: gatewayCanaryPct,
          reason: gatewayRolloutReason || 'Updated from settings',
        }),
      })
      setGatewayMessage(`Gateway rollout set to ${state}`)
      await loadGatewayAdminData()
    } catch (err) {
      setGatewayMessage(err instanceof Error ? err.message : 'Failed to update rollout')
    }
  }

  async function syncGateway() {
    setGatewayMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/admin/gateway-sync`, { method: 'POST' })
      setGatewayMessage('Gateway sync triggered')
      await loadGatewayAdminData()
    } catch (err) {
      setGatewayMessage(err instanceof Error ? err.message : 'Failed to sync gateway')
    }
  }

  async function resetGateway() {
    setGatewayMessage('')
    try {
      await fetchJson(`${ORCHESTRATOR_URL}/admin/gateway-reset`, { method: 'POST' })
      setGatewayMessage('Gateway routing cooldown reset')
      await loadGatewayAdminData()
    } catch (err) {
      setGatewayMessage(err instanceof Error ? err.message : 'Failed to reset gateway')
    }
  }

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />
      <header className="hero settings-hero">
        <p className="eyebrow">Operations</p>
        <h1>Settings</h1>
        <p className="subtitle">Manage data sources, service health, and write-back controls.</p>
      </header>

      <main className="settings-shell">
        {/* Tab Navigation */}
        <div className="settings-tabs">
          <button className={`settings-tab ${tab === 'service_health' ? 'active' : ''}`} onClick={() => setTab('service_health')}>
            Service health
          </button>
          <button className={`settings-tab ${tab === 'gateway' ? 'active' : ''}`} onClick={() => setTab('gateway')}>
            Gateway
          </button>
          <button className={`settings-tab ${tab === 'approvals' ? 'active' : ''}`} onClick={() => setTab('approvals')}>
            Approvals
          </button>
        </div>

        {tab === 'data_sources' && (
          <>
            {userMessage && <section className="settings-section"><div className="settings-message">{userMessage}</div></section>}
            <section className="settings-section">
              <div className="approval-toolbar">
              <h2>Model provider</h2>
                <button onClick={() => void loadLlmProviderStatus()} disabled={llmStatusLoading}>
                  {llmStatusLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
              {!llmStatus ? (
                <div className="settings-hint">Provider status unavailable.</div>
              ) : (
                <div className="llm-status-card">
                  <div className="llm-status-row">
                    <span>Provider</span>
                    <strong>{llmStatus.provider || 'unknown'}</strong>
                  </div>
                  <div className="llm-status-row">
                    <span>Model</span>
                    <strong>{llmStatus.model || 'n/a'}</strong>
                  </div>
                  <div className="llm-status-row">
                    <span>Supported</span>
                    <span className={`status-pill ${llmStatus.supported ? 'completed' : 'failed'}`}>
                      {llmStatus.supported ? 'yes' : 'no'}
                    </span>
                  </div>
                  <div className="llm-status-row">
                    <span>Configured</span>
                    <span className={`status-pill ${llmStatus.configured ? 'completed' : 'failed'}`}>
                      {llmStatus.configured ? 'yes' : 'no'}
                    </span>
                  </div>
                  <div className="llm-status-row">
                    <span>Endpoint</span>
                    <strong className="llm-endpoint">{llmStatus.endpoint || 'not set'}</strong>
                  </div>
                  {llmStatus.missing_env_vars?.length > 0 && (
                    <div className="llm-status-warning">
                      Missing env vars: {llmStatus.missing_env_vars.join(', ')}
                    </div>
                  )}
                  {llmStatus.error && <div className="llm-status-warning">{llmStatus.error}</div>}
                </div>
              )}
            </section>

            <section className="settings-section">
              <h2>MCP server status</h2>
              <p className="settings-hint">Toggle MCP services on or off. Disabled services are hidden from the agent.</p>
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
                  {previewLoading === s.key ? 'Loading...' : 'Preview data'}
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
                <h2>Data preview</h2>
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
              <h2>Add data to an MCP service</h2>
              <p className="settings-hint">
                Upload new documents, user context, templates, or analytics records. Select a service and paste JSON.
              </p>
              <div className="add-data-form">
                <div className="settings-row">
                  <div className="settings-field">
                    <label>Target service</label>
                    <select value={addDataService} onChange={(e) => setAddDataService(e.target.value)}>
                      <option value="knowledge_base">Knowledge base</option>
                      <option value="memory">Memory</option>
                      <option value="document_generation">Document generation</option>
                      <option value="analytics">Analytics</option>
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
                <button onClick={submitData}>Submit data</button>
                {addDataMessage && <div className={`settings-message ${addDataMessage.startsWith('Success') ? 'success' : ''}`}>{addDataMessage}</div>}
              </div>
            </section>
          </>
        )}

        {tab === 'service_health' && (
          <>
            <section className="settings-section">
              <div className="approval-toolbar">
                <h2>MCP service health</h2>
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
                    <th>Response ms</th>
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

        {tab === 'gateway' && (
          <>
            <section className="settings-section">
              <div className="approval-toolbar">
                <h2>Gateway</h2>
                <button onClick={() => void loadGatewayAdminData()} disabled={gatewayLoading}>
                  {gatewayLoading ? 'Refreshing...' : 'Refresh'}
                </button>
              </div>
              {gatewayMessage && <div className="settings-message">{gatewayMessage}</div>}

              {!gatewayConfig ? (
                <div className="settings-hint">Gateway configuration unavailable.</div>
              ) : (
                <div className="gateway-summary-grid">
                  <div className="gateway-summary-card">
                    <span>Enabled</span>
                    <span className={`status-pill ${gatewayConfig.enabled ? 'completed' : 'failed'}`}>{gatewayConfig.enabled ? 'yes' : 'no'}</span>
                  </div>
                  <div className="gateway-summary-card">
                    <span>Configured</span>
                    <span className={`status-pill ${gatewayConfig.configured ? 'completed' : 'failed'}`}>{gatewayConfig.configured ? 'yes' : 'no'}</span>
                  </div>
                  <div className="gateway-summary-card">
                    <span>Auth mode</span>
                    <strong>{gatewayConfig.auth_mode}</strong>
                  </div>
                  <div className="gateway-summary-card">
                    <span>Fallback mode</span>
                    <strong>{gatewayConfig.fallback_mode}</strong>
                  </div>
                  <div className="gateway-summary-card wide">
                    <span>Base URL</span>
                    <strong className="llm-endpoint">{gatewayConfig.base_url_masked || gatewayConfig.base_url || 'not set'}</strong>
                  </div>
                  <div className="gateway-summary-card">
                    <span>Last sync</span>
                    <strong>{gatewayConfig.last_sync_at ? new Date(gatewayConfig.last_sync_at).toLocaleString() : 'never'}</strong>
                  </div>
                </div>
              )}

              <div className="gateway-actions-row">
                <button onClick={() => void toggleGateway(!(gatewayConfig?.enabled ?? false))}>
                  {gatewayConfig?.enabled ? 'Disable' : 'Enable'}
                </button>
                <button onClick={() => void syncGateway()}>Sync registry</button>
                <button onClick={() => void resetGateway()}>Reset cooldown</button>
              </div>
            </section>

            <section className="settings-section">
              <div className="approval-toolbar">
                <h2>Gateway rollout</h2>
              </div>
              <div className="settings-row">
                <div className="settings-field">
                  <label>Canary traffic %</label>
                  <input
                    type="number"
                    min={0}
                    max={100}
                    value={gatewayCanaryPct}
                    onChange={(e) => setGatewayCanaryPct(Math.max(0, Math.min(100, Number(e.target.value) || 0)))}
                  />
                </div>
                <div className="settings-field">
                  <label>Reason</label>
                  <input
                    value={gatewayRolloutReason}
                    onChange={(e) => setGatewayRolloutReason(e.target.value)}
                    placeholder="Reason for rollout update"
                  />
                </div>
              </div>
              <div className="gateway-actions-row">
                <button onClick={() => void applyGatewayRollout('live')}>Set live</button>
                <button onClick={() => void applyGatewayRollout('canary')}>Set canary</button>
                <button className="btn-danger" onClick={() => void applyGatewayRollout('paused')}>Pause</button>
              </div>
              {gatewayConfig?.rollout && (
                <div className="settings-hint">
                  Current rollout: {gatewayConfig.rollout.state} ({gatewayConfig.rollout.canary_traffic_pct}% canary) · updated {new Date(gatewayConfig.rollout.updated_at).toLocaleString()}
                </div>
              )}
            </section>

            <section className="settings-section">
              <h2>Upstream service health</h2>
              {gatewayHealth?.services?.length ? (
                <table className="users-table approvals-table">
                  <thead>
                    <tr>
                      <th>Service</th>
                      <th>Reachable</th>
                      <th>Status</th>
                      <th>Response (ms)</th>
                      <th>Error</th>
                    </tr>
                  </thead>
                  <tbody>
                    {gatewayHealth.services.map((row, idx) => (
                      <tr key={`${row.key || row.service || row.name || 'svc'}-${idx}`}>
                        <td>{row.name || row.service || row.key || 'unknown'}</td>
                        <td><span className={`status-pill ${row.reachable ? 'completed' : 'failed'}`}>{row.reachable ? 'yes' : 'no'}</span></td>
                        <td>{row.status_code ?? 'n/a'}</td>
                        <td>{row.response_ms ?? row.response_time_ms ?? 0}</td>
                        <td>{row.error || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="settings-hint">No upstream health records available.</div>
              )}
            </section>

            <section className="settings-section">
                <h2>Gateway reliability</h2>
              <div className="approval-grid">
                <ReliabilityCard title="Gateway" data={gatewayReliability} />
              </div>
            </section>
          </>
        )}

        {tab === 'approvals' && (
          <>
            <section className="settings-section">
              <div className="approval-toolbar">
                <h2>Write-back reliability</h2>
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
              <h2>Circuit breaker controls</h2>
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
              <h2>Pending approval queue</h2>
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
                    <th>Requested by</th>
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
                <h2>Action history</h2>
                <div className="settings-field action-filter-field">
                  <label>Status filter</label>
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
