import { useState } from 'react'
import { useAuth } from './auth'

export function LoginPage() {
  const { login, register, isLoading } = useAuth()
  const isDevDemo = import.meta.env.DEV && import.meta.env.VITE_DISABLE_DEV_LOGIN_BYPASS !== 'true'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [mode, setMode] = useState<'login' | 'register'>('login')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!email.trim() || !password.trim()) {
      setError('Please enter both email and password.')
      return
    }
    const fn = mode === 'login' ? login : register
    const err = await fn(email.trim(), password.trim())
    if (err) {
      setError(err)
    }
  }

  return (
    <div className="login-page">
      <div className="bg-grid" aria-hidden="true" />
      <div className="login-card">
        <div className="login-brand">
          <div className="evie-brand evie-brand-compact">
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
          <p className="eyebrow">Private Workspace</p>
          <h1>Intelligence Workspace</h1>
          {isDevDemo && <div className="mode-badge">Demo mode</div>}
        </div>
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="login-field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              autoFocus
              required
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
              required
            />
          </div>
          {error && <div className="login-error">{error}</div>}
          <button type="submit" className="login-btn" disabled={isLoading}>
            {isLoading ? 'Please wait...' : mode === 'login' ? 'Sign In' : 'Create Account'}
          </button>
        </form>
        <div className="login-hint">
          {mode === 'login' ? (
            <span>
              No account?{' '}
              <button className="link-btn" onClick={() => setMode('register')}>
                Register
              </button>
            </span>
          ) : (
            <span>
              Already have an account?{' '}
              <button className="link-btn" onClick={() => setMode('login')}>
                Sign In
              </button>
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
