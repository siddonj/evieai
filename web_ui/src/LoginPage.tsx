import { useState } from 'react'
import { useAuth } from './auth'

export function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password.')
      return
    }
    const ok = login(username.trim(), password.trim())
    if (!ok) {
      setError('Invalid username or password.')
    }
  }

  return (
    <div className="login-page">
      <div className="bg-grid" aria-hidden="true" />
      <div className="login-card">
        <div className="login-brand">
          <p className="eyebrow">AI-Powered Agentic Q&A</p>
          <h1>Workspace Intelligence Console</h1>
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-field">
            <label htmlFor="username">Username</label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              autoFocus
            />
          </div>
          <div className="login-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-btn">Sign In</button>
        </form>
        <div className="login-hint">
          Default admin: <strong>admin</strong> / <strong>admin</strong>
        </div>
      </div>
    </div>
  )
}
