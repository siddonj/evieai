import { useState, useEffect, useRef } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'
const ALERT_THRESHOLD = 80
const INCIDENT_THRESHOLD = 3

interface ServiceStatus {
  name: string
  reachable: boolean
  response_time_ms?: number
  error?: string
}

interface HealthResponse {
  orchestrator_status: string
  health_percentage: number
  services: ServiceStatus[]
  timestamp: string
}

interface HealthDataPoint {
  timestamp: string
  health: number
  reachable: number
  total: number
}

interface Alert {
  id: string
  timestamp: Date
  severity: 'warning' | 'critical'
  message: string
  dismissed: boolean
}

interface ServiceDetail {
  name: string
  reachable: boolean
  response_time_ms?: number
  error?: string
}

interface AdminPageProps {
  onBack: () => void
}

const SERVICE_CATEGORIES: Record<string, { label: string; color: string }> = {
  sql: { label: 'SQL database', color: '#3b82f6' },
  files: { label: 'File share', color: '#f59e0b' },
  mail: { label: 'Mail', color: '#ef4444' },
  onedrive: { label: 'OneDrive', color: '#0ea5e9' },
  memory: { label: 'Memory', color: '#8b5cf6' },
  knowledge_base: { label: 'Knowledge base', color: '#10b981' },
  document_generation: { label: 'Documents', color: '#ec4899' },
  analytics: { label: 'Analytics', color: '#f97316' },
  postgresql: { label: 'PostgreSQL', color: '#06b6d4' },
  dashboard: { label: 'Dashboard', color: '#14b8a6' },
}

function getServiceCategory(name: string) {
  return SERVICE_CATEGORIES[name] ?? { label: 'Service', color: '#64748b' }
}

export function AdminPage({ onBack }: AdminPageProps) {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // History tracking for chart
  const historyRef = useRef<HealthDataPoint[]>([])
  const [history, setHistory] = useState<HealthDataPoint[]>([])

  // Alerts
  const [alerts, setAlerts] = useState<Alert[]>([])
  const lastHealthRef = useRef<number | null>(null)

  // Service detail modal
  const [selectedService, setSelectedService] = useState<ServiceDetail | null>(null)

  // Restart state
  const [restarting, setRestarting] = useState<string | null>(null)
  const [restartStatus, setRestartStatus] = useState<Record<string, { status: string; message?: string }>>({})

  async function fetchHealth() {
    try {
      setError('')
      const response = await fetch(`${ORCHESTRATOR_URL}/ready`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const data = (await response.json()) as HealthResponse
      setHealth(data)
      setLastUpdate(new Date())

      // Track history for chart
      const reachable = data.services.filter((s) => s.reachable).length
      const dataPoint: HealthDataPoint = {
        timestamp: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
        health: data.health_percentage,
        reachable,
        total: data.services.length,
      }

      historyRef.current = [...historyRef.current.slice(-19), dataPoint]
      setHistory([...historyRef.current])

      // Check for alerts
      checkAlerts(data, reachable)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Failed to fetch health status: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  function checkAlerts(data: HealthResponse, reachableCount: number) {
    const newAlerts: Alert[] = [...alerts]
    const now = new Date()

    // Health threshold alert
    if (data.health_percentage < ALERT_THRESHOLD && lastHealthRef.current !== data.health_percentage) {
      const alert: Alert = {
        id: `health-${now.getTime()}`,
        timestamp: now,
        severity: data.health_percentage < 50 ? 'critical' : 'warning',
        message: `System health dropped to ${data.health_percentage}%`,
        dismissed: false,
      }
      newAlerts.unshift(alert)
      setAlerts(newAlerts.slice(0, 10))
    }

    // Incident correlation alert (3+ services down)
    const downCount = data.services.length - reachableCount
    if (downCount >= INCIDENT_THRESHOLD) {
      const downServices = data.services
        .filter((s) => !s.reachable)
        .map((s) => s.name)
        .join(', ')
      const alert: Alert = {
        id: `incident-${now.getTime()}`,
        timestamp: now,
        severity: 'critical',
        message: `${downCount} services are unavailable: ${downServices}`,
        dismissed: false,
      }
      newAlerts.unshift(alert)
      setAlerts(newAlerts.slice(0, 10))
    }

    lastHealthRef.current = data.health_percentage
  }

  function dismissAlert(id: string) {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
  }

  async function handleRestart(serviceName: string) {
    setRestarting(serviceName)
    try {
      const response = await fetch(`${ORCHESTRATOR_URL}/restart`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ service: serviceName }),
      })

      const data = (await response.json()) as any

      if (response.ok && data.status === 'restarting') {
        setRestartStatus((prev) => ({
          ...prev,
          [serviceName]: {
            status: 'success',
            message: 'Restart initiated ✓',
          },
        }))
        // Auto-refresh health after a delay
        setTimeout(() => void fetchHealth(), 3000)
        // Clear success message after 3 seconds
        setTimeout(() => {
          setRestartStatus((prev) => {
            const updated = { ...prev }
            delete updated[serviceName]
            return updated
          })
        }, 3000)
      } else {
        setRestartStatus((prev) => ({
          ...prev,
          [serviceName]: {
            status: 'error',
            message: data.error || 'Failed to restart',
          },
        }))
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setRestartStatus((prev) => ({
        ...prev,
        [serviceName]: {
          status: 'error',
          message,
        },
      }))
    } finally {
      setRestarting(null)
    }
  }

  useEffect(() => {
    void fetchHealth()
  }, [])

  // Auto-refresh every 5 seconds
  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      void fetchHealth()
    }, 5000)

    return () => clearInterval(interval)
  }, [autoRefresh])

  if (loading && !health) {
    return (
      <div className="admin-container">
        <div className="dashboard-header">
          <h1>Operations Health</h1>
          <p>Real-time service status and recovery controls</p>
        </div>
        <div className="dashboard-loading">Loading current health data...</div>
      </div>
    )
  }

  const reachableCount = health?.services.filter((s) => s.reachable).length ?? 0
  const totalCount = health?.services.length ?? 0
  const downServices = health?.services.filter((s) => !s.reachable).length ?? 0

  return (
    <div className="admin-container">
      {/* Header */}
      <div className="dashboard-header">
        <h1>Operations Health</h1>
        <p>Real-time service status and recovery controls</p>
      </div>

      {/* Toolbar */}
      <div className="dashboard-toolbar">
        <div className="toolbar-left">
          <label className="toolbar-checkbox">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (5s)
          </label>
          <button className="toolbar-button" onClick={() => void fetchHealth()} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </button>
          <button className="toolbar-button" onClick={onBack}>
            Back to chat
          </button>
        </div>
        <div className="toolbar-right">
          <span className="toolbar-time">Last updated: {lastUpdate?.toLocaleTimeString()}</span>
        </div>
      </div>

      {/* Error Message */}
      {error && <div className="dashboard-error">{error}</div>}

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="alerts-section">
          {alerts.map((alert) => (
            <div key={alert.id} className={`alert alert-${alert.severity}`}>
              <span className="alert-message">{alert.message}</span>
              <button
                className="alert-close"
                onClick={() => dismissAlert(alert.id)}
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Health Summary */}
      {health && (
        <>
          <div className="health-summary">
            <div
              className="health-gauge"
              style={{
                borderColor:
                  health.health_percentage >= 80
                    ? '#10b981'
                    : health.health_percentage >= 50
                      ? '#f59e0b'
                      : '#dc2626',
              }}
            >
              <div className="health-percentage">{health.health_percentage}%</div>
              <div className="health-label">Health</div>
            </div>

            <div className="kpi-cards">
              <div className="kpi-card">
                <div className="kpi-icon">Operations</div>
                <div className="kpi-label">Orchestrator</div>
                <div className="kpi-value">{health.orchestrator_status}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-icon">Coverage</div>
                <div className="kpi-label">Active Services</div>
                <div className="kpi-value">
                  {reachableCount}/{totalCount}
                </div>
              </div>
              <div className="kpi-card">
                <div className="kpi-icon">Latency</div>
                <div className="kpi-label">Avg Response</div>
                <div className="kpi-value">
                  {health.services.length > 0
                    ? Math.round(
                        health.services.reduce((sum, s) => sum + (s.response_time_ms || 0), 0) /
                          health.services.length
                      )
                    : 0}
                  ms
                </div>
              </div>
            </div>
          </div>

          {/* Health Trend Chart */}
          {history.length > 1 && (
            <div className="chart-section">
              <h2>Health trend over the last 20 checks</h2>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="timestamp" stroke="rgba(255,255,255,0.6)" />
                  <YAxis domain={[0, 100]} stroke="rgba(255,255,255,0.6)" />
                  <Tooltip contentStyle={{ backgroundColor: 'rgba(0,0,0,0.8)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px' }} />
                  <Line
                    type="monotone"
                    dataKey="health"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Services Grid */}
          <div className="services-grid">
            <h2>Service status</h2>
            <div className="service-cards">
              {health.services.map((service) => (
                <div
                  key={service.name}
                  className={`service-card ${service.reachable ? 'healthy' : 'unhealthy'}`}
                  style={{
                    borderLeftColor: getServiceCategory(service.name).color,
                  }}
                >
                  <div className="service-header">
                    <div
                      className="service-content"
                      onClick={() =>
                        setSelectedService({
                          name: service.name,
                          reachable: service.reachable,
                          response_time_ms: service.response_time_ms,
                          error: service.error,
                        })
                      }
                      style={{ cursor: 'pointer', flex: 1 }}
                    >
                      <div className="service-icon">{getServiceCategory(service.name).label.slice(0, 1)}</div>
                      <div className="service-name">
                        {getServiceCategory(service.name).label}
                      </div>
                      <div className={`service-status ${service.reachable ? 'up' : 'down'}`}>
                        {service.reachable ? 'Online' : 'Offline'}
                      </div>
                    </div>
                    <button
                      className="service-restart-btn"
                      onClick={() => void handleRestart(service.name)}
                      disabled={restarting === service.name}
                      title="Restart this service"
                    >
                      {restarting === service.name ? '⏳' : '🔄'}
                    </button>
                  </div>
                  {service.response_time_ms && (
                    <div className="service-details">
                      <div className="detail-row">
                        <span>Response time:</span>
                        <span>{service.response_time_ms}ms</span>
                      </div>
                    </div>
                  )}
                  {restartStatus[service.name] && (
                    <div className={`restart-status ${restartStatus[service.name].status}`}>
                      {restartStatus[service.name].message}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Incident Banner */}
          {downServices >= INCIDENT_THRESHOLD && (
            <div className="incident-banner">
              <span className="incident-icon">Alert</span>
              <span className="incident-text">
                {downServices} services are currently unavailable
              </span>
            </div>
          )}

          {/* Data Sources */}
          <div className="datasource-section">
            <h2>Data sources</h2>
            <div className="datasource-grid">
              {[
                { name: 'Real Estate DB', status: 'Available' },
                { name: 'Market Analytics', status: 'Available' },
                { name: 'Tenant Database', status: 'Available' },
                { name: 'Financial Records', status: 'Available' },
                { name: 'Document Library', status: 'Available' },
                { name: 'Communications', status: 'Available' },
              ].map((ds) => (
                <div key={ds.name} className="datasource-item">
                  <div className="ds-icon" aria-hidden="true" />
                  <div className="ds-name">{ds.name}</div>
                  <div className="ds-status">{ds.status}</div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Service Detail Modal */}
      {selectedService && (
        <div className="modal-overlay" onClick={() => setSelectedService(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{getServiceCategory(selectedService.name).label}</h2>
              <button className="modal-close" onClick={() => setSelectedService(null)}>
                ✕
              </button>
            </div>
            <div className="modal-body">
              <div className="detail-group">
                <label>Status</label>
                <div
                  className={`detail-value ${selectedService.reachable ? 'status-ok' : 'status-error'}`}
                >
                  {selectedService.reachable ? 'Online' : 'Offline'}
                </div>
              </div>

              {selectedService.response_time_ms && (
                <div className="detail-group">
                  <label>Response Time</label>
                  <div className="detail-value">{selectedService.response_time_ms}ms</div>
                </div>
              )}

              {selectedService.error && (
                <div className="detail-group">
                  <label>Error</label>
                  <div className="detail-value status-error">{selectedService.error}</div>
                </div>
              )}

              <div className="detail-group">
                <label>Logs</label>
                <div className="detail-logs">
                  <p>Recent activity logs would appear here.</p>
                  <code className="log-sample">
                    {`[2026-05-30T14:32:45Z] Service health check: OK\n[2026-05-30T14:32:40Z] Response time: ${selectedService.response_time_ms || 0}ms`}
                  </code>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="modal-button" onClick={() => setSelectedService(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
// Rebuild trigger - 20260529-230156
