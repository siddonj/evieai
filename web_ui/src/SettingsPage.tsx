import { useState, useEffect } from 'react'
import { useAuth, type User } from './auth'

const ORCHESTRATOR_URL = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'

type McpServer = {
  key: string
  name: string
  enabled: boolean
  url: string
  has_admin_data: boolean
}

type Tab = 'users' | 'data_sources'

export function SettingsPage() {
  const { users, addUser, removeUser, logout, user: currentUser } = useAuth()
  const [tab, setTab] = useState<Tab>('users')

  // ─── Users State ────────────────────────────────────────────────────
  const [newUsername, setNewUsername] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newRole, setNewRole] = useState<'admin' | 'user'>('user')
  const [userMessage, setUserMessage] = useState('')

  // ─── Data Sources State ─────────────────────────────────────────────
  const [servers, setServers] = useState<McpServer[]>([])
  const [serverLoading, setServerLoading] = useState(false)
  const [dataPreview, setDataPreview] = useState<Record<string, any>>({})
  const [previewLoading, setPreviewLoading] = useState<string | null>(null)
  const [addDataService, setAddDataService] = useState('knowledge_base')
  const [addDataJson, setAddDataJson] = useState('')
  const [addDataMessage, setAddDataMessage] = useState('')

  // Load MCP config on mount
  useEffect(() => {
    loadMcpConfig()
  }, [])

  async function loadMcpConfig() {
    setServerLoading(true)
    try {
      const res = await fetch(`${ORCHESTRATOR_URL}/admin/mcp-config`)
      if (res.ok) {
        const data = await res.json()
        setServers(data.servers || [])
      }
    } catch {
      setUserMessage('Failed to load MCP configuration.')
    } finally {
      setServerLoading(false)
    }
  }

  async function toggleMcp(key: string, enabled: boolean) {
    try {
      const res = await fetch(`${ORCHESTRATOR_URL}/admin/mcp-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, enabled }),
      })
      if (res.ok) {
        setServers((prev) => prev.map((s) => (s.key === key ? { ...s, enabled } : s)))
      }
    } catch {
      setUserMessage(`Failed to toggle ${key}.`)
    }
  }

  async function previewData(service: string) {
    setPreviewLoading(service)
    try {
      const res = await fetch(`${ORCHESTRATOR_URL}/admin/mcp-data/${service}`)
      if (res.ok) {
        const data = await res.json()
        setDataPreview((prev) => ({ ...prev, [service]: data }))
      } else {
        setDataPreview((prev) => ({ ...prev, [service]: { error: 'Failed to load data' } }))
      }
    } catch {
      setDataPreview((prev) => ({ ...prev, [service]: { error: 'Network error' } }))
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
      const res = await fetch(`${ORCHESTRATOR_URL}/admin/mcp-data/${addDataService}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const result = await res.json()
      if (result.error) {
        setAddDataMessage(`Error: ${result.error}`)
      } else {
        setAddDataMessage(`Success: ${result.action} ${result.id || result.category || result.user_id || ''}`)
        setAddDataJson('')
        // Refresh preview if open
        if (dataPreview[addDataService]) {
          previewData(addDataService)
        }
      }
    } catch {
      setAddDataMessage('Failed to send data to MCP server.')
    }
  }

  // ─── User Handlers ──────────────────────────────────────────────────
  function handleAddUser(e: React.FormEvent) {
    e.preventDefault()
    setUserMessage('')
    if (!newUsername.trim() || !newPassword.trim()) {
      setUserMessage('Username and password are required.')
      return
    }
    const ok = addUser(newUsername.trim(), newPassword.trim(), newRole)
    if (ok) {
      setUserMessage(`User ${newUsername} added.`)
      setNewUsername('')
      setNewPassword('')
      setNewRole('user')
    } else {
      setUserMessage(`User ${newUsername} already exists.`)
    }
  }

  function handleRemoveUser(username: string) {
    setUserMessage('')
    const ok = removeUser(username)
    if (ok) setUserMessage(`User ${username} removed.`)
  }

  return (
    <div className="page">
      <div className="bg-grid" aria-hidden="true" />
      <header className="hero settings-hero">
        <p className="eyebrow">Settings</p>
        <h1>Admin Console</h1>
        <p className="subtitle">
          Manage users, data sources, and MCP server configurations.
        </p>
      </header>

      <main className="settings-shell">
        {/* Tab Navigation */}
        <div className="settings-tabs">
          <button className={`settings-tab ${tab === 'users' ? 'active' : ''}`} onClick={() => setTab('users')}>
            👤 Users
          </button>
          <button className={`settings-tab ${tab === 'data_sources' ? 'active' : ''}`} onClick={() => setTab('data_sources')}>
            🗃️ Data Sources
          </button>
        </div>

        {tab === 'users' && (
          <>
            <section className="settings-section">
              <h2>Add New User</h2>
              <form className="settings-form" onSubmit={handleAddUser}>
                <div className="settings-row">
                  <div className="settings-field">
                    <label>Username</label>
                    <input type="text" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} placeholder="Username" />
                  </div>
                  <div className="settings-field">
                    <label>Password</label>
                    <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="Password" />
                  </div>
                  <div className="settings-field">
                    <label>Role</label>
                    <select value={newRole} onChange={(e) => setNewRole(e.target.value as 'admin' | 'user')}>
                      <option value="user">User</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                </div>
                <button type="submit">Add User</button>
              </form>
              {userMessage && <div className="settings-message">{userMessage}</div>}
            </section>

            <section className="settings-section">
              <h2>Existing Users</h2>
              <table className="users-table">
                <thead>
                  <tr><th>Username</th><th>Role</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {users.map((u: User) => (
                    <tr key={u.username} className={u.username === currentUser?.username ? 'current' : ''}>
                      <td>
                        {u.username}
                        {u.username === currentUser?.username && <span className="you-badge"> you</span>}
                      </td>
                      <td><span className={`role-badge role-${u.role}`}>{u.role}</span></td>
                      <td>
                        {u.username !== 'admin' && (
                          <button className="btn-remove" onClick={() => handleRemoveUser(u.username)}>Remove</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </>
        )}

        {tab === 'data_sources' && (
          <>
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

        <section className="settings-footer">
          <button className="btn-logout" onClick={logout}>Sign Out</button>
        </section>
      </main>
    </div>
  )
}

function getPlaceholder(service: string): string {
  switch (service) {
    case 'knowledge_base':
      return JSON.stringify({
        document: {
          id: "sop-009",
          type: "SOP",
          category: "IT Security",
          title: "Cloud Access Security Broker Policy",
          version: "1.0",
          effective_date: "2026-05-01",
          owner: "CISO",
          status: "Active",
          summary: "All cloud service access must go through the approved CASB.",
          key_points: ["CASB required for all SaaS", "DLP policies enforced at egress"],
          related: ["sop-001", "sop-002"]
        }
      }, null, 2)
    case 'memory':
      return JSON.stringify({
        user_id: "new-user",
        context: {
          user_id: "new-user",
          profile: { name: "Sam Taylor", role: "Product Manager", department: "Product" },
          preferences: { data_focus: ["roadmap", "user_feedback", "metrics"] },
          recent_topics: ["Q3 roadmap planning"],
          bookmarks: []
        }
      }, null, 2)
    case 'document_generation':
      return JSON.stringify({
        document: {
          id: "doc-005",
          type: "product_roadmap",
          title: "Q3 2026 Product Roadmap",
          generated_at: "2026-05-06T10:00:00Z",
          status: "Generated",
          pages: 3,
          word_count: 1200,
          sections: [{ heading: "Overview", content: "...", key_metrics: [] }],
          action_items: [],
          tags: ["product", "roadmap"]
        }
      }, null, 2)
    case 'analytics':
      return JSON.stringify({
        category: "product",
        data: {
          category: "Product Metrics",
          kpi_cards: [{ name: "NPS", value: "72", change: "+4", period: "QoQ", status: "positive", target: "70", target_status: "exceeded" }],
          trends: [],
          insights: ["NPS at all-time high"]
        }
      }, null, 2)
    default:
      return '{"document": {...}}'
  }
}
