import React, { useState, useEffect } from 'react'

const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'

interface ServiceStatus {
  name: string
  reachable: boolean
  response_time_ms: number
  error?: string
}

interface HealthResponse {
  orchestrator_status: string
  health_percentage: number
  services: ServiceStatus[]
  timestamp: string
}

interface AdminPageProps {
  onBack: () => void
}

const SERVICE_CATEGORIES: Record<string, { label: string; emoji: string; color: string }> = {
  sql: { label: 'SQL Database', emoji: '🗄️', color: '#3b82f6' },
  files: { label: 'File Share', emoji: '📁', color: '#f59e0b' },
  mail: { label: 'Email (O365)', emoji: '📧', color: '#ef4444' },
  onedrive: { label: 'OneDrive', emoji: '☁️', color: '#0ea5e9' },
  memory: { label: 'Memory Store', emoji: '🧠', color: '#8b5cf6' },
  knowledge_base: { label: 'Knowledge Base', emoji: '📚', color: '#10b981' },
  document_generation: { label: 'Document Gen', emoji: '📄', color: '#ec4899' },
  analytics: { label: 'Analytics', emoji: '📊', color: '#f97316' },
  postgresql: { label: 'PostgreSQL', emoji: '🐘', color: '#06b6d4' },
  dashboard: { label: 'Dashboard', emoji: '📈', color: '#14b8a6' },
}

const DATA_SOURCES = [
  { name: 'Real Estate Data', status: 'active', icon: '🏢' },
  { name: 'Market Analytics', status: 'active', icon: '📈' },
  { name: 'Tenant Database', status: 'active', icon: '👥' },
  { name: 'Financial Records', status: 'active', icon: '💰' },
  { name: 'Document Library', status: 'degraded', icon: '📑' },
  { name: 'Communications', status: 'active', icon: '💬' },
]

export const AdminPage: React.FC<AdminPageProps> = ({ onBack }) => {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  async function fetchHealth() {
    try {
      setError('')
      const response = await fetch(`${ORCHESTRATOR_URL}/ready`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      })
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const data = (await response.json()) as HealthResponse
      setHealth(data)
      setLastUpdate(new Date())
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Failed to fetch health status: ${message}`)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    setLoading(true)
    fetchHealth()
  }, [])

  useEffect(() => {
    if (!autoRefresh) return

    const interval = setInterval(() => {
      setLoading(true)
      fetchHealth()
    }, 5000)

    return () => clearInterval(interval)
  }, [autoRefresh])

  const getHealthColor = (percentage: number) => {
    if (percentage >= 80) return '#10b981'
    if (percentage >= 60) return '#f59e0b'
    return '#dc2626'
  }

  const getServiceColor = (service: ServiceStatus) => {
    if (!service.reachable) return '#dc2626'
    if (service.response_time_ms > 1000) return '#f59e0b'
    return '#10b981'
  }

  return (
    <div className="admin-container">
      {/* Header */}
      <div className="admin-header">
        <div className="admin-title">
          <h1>🖥️ System Health Dashboard</h1>
          <p>Real-time orchestrator and service monitoring</p>
        </div>
        <div className="admin-controls">
          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (5s)
          </label>
          <button onClick={fetchHealth} disabled={loading} className="btn-refresh">
            🔄 {loading ? 'Loading...' : 'Refresh'}
          </button>
          <button onClick={onBack} className="btn-back">
            ← Back
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
        </div>
      )}

      {/* Last Update */}
      {lastUpdate && (
        <div className="last-update">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      )}

      {/* Health Summary */}
      {health && (
        <div className="health-summary">
          <div className="health-gauge-container">
            <div className="health-gauge" style={{ borderColor: getHealthColor(health.health_percentage) }}>
              <div className="gauge-text">
                <div className="gauge-number">{health.health_percentage}%</div>
                <div className="gauge-label">Healthy</div>
              </div>
            </div>
          </div>

          <div className="kpi-cards">
            <div className="kpi-card">
              <span className="kpi-icon">📊</span>
              <span className="kpi-label">Orchestrator</span>
              <span className="kpi-value" style={{ color: '#10b981' }}>
                {health.orchestrator_status}
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-icon">✅</span>
              <span className="kpi-label">Active Services</span>
              <span className="kpi-value" style={{ color: '#3b82f6' }}>
                {health.services.filter((s) => s.reachable).length}/{health.services.length}
              </span>
            </div>
            <div className="kpi-card">
              <span className="kpi-icon">⏱️</span>
              <span className="kpi-label">Avg Response</span>
              <span className="kpi-value">
                {health.services.length > 0
                  ? (
                      health.services.reduce((sum, s) => sum + s.response_time_ms, 0) /
                      health.services.length
                    ).toFixed(0)
                  : 0}
                ms
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Service Cards */}
      {health && (
        <div className="service-cards">
          {health.services.map((service) => {
            const config = SERVICE_CATEGORIES[service.name] || {
              label: service.name,
              emoji: '⚙️',
              color: '#6b7280',
            }
            return (
              <div key={service.name} className="service-card" style={{ borderColor: getServiceColor(service) }}>
                <div className="service-header">
                  <span className="service-emoji">{config.emoji}</span>
                  <h3>{config.label}</h3>
                </div>
                <div className="detail-row">
                  <span>Status</span>
                  <span
                    className="status-badge"
                    style={{ backgroundColor: getServiceColor(service) }}
                  >
                    {service.reachable ? '🟢 Online' : '🔴 Offline'}
                  </span>
                </div>
                {service.reachable && (
                  <div className="detail-row">
                    <span>Response Time</span>
                    <span className="response-time">{service.response_time_ms.toFixed(1)}ms</span>
                  </div>
                )}
                {service.error && (
                  <div className="detail-row">
                    <span>Error</span>
                    <span className="error-text">{service.error}</span>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Data Sources Grid */}
      {health && (
        <div className="datasource-section">
          <h2>Data Source Connectivity</h2>
          <div className="datasource-grid">
            {DATA_SOURCES.map((source) => (
              <div key={source.name} className="datasource-card">
                <span className="datasource-icon">{source.icon}</span>
                <span className="datasource-name">{source.name}</span>
                <span
                  className="datasource-status"
                  style={{
                    color: source.status === 'active' ? '#10b981' : '#f59e0b',
                  }}
                >
                  {source.status === 'active' ? '●' : '◐'} {source.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
