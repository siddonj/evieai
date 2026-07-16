import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { getOrchestratorUrl } from './apiBase'

export type User = {
  id: string
  email: string
  role: 'admin' | 'user'
}

const API_BASE = getOrchestratorUrl()

const SESSION_KEY = 'evieai_session'

function loadSession(): { token: string; user: User } | null {
  const raw = localStorage.getItem(SESSION_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function saveSession(token: string, user: User) {
  localStorage.setItem(SESSION_KEY, JSON.stringify({ token, user }))
}

function clearSession() {
  localStorage.removeItem(SESSION_KEY)
}

type AuthCtx = {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<string | null>
  logout: () => void
  register: (email: string, password: string, role?: 'admin' | 'user') => Promise<string | null>
  isAdmin: boolean
  isLoading: boolean
}

const AuthContext = createContext<AuthCtx | null>(null)

export function isDemoLoginBypassEnabled(options?: {
  hostname?: string
  isDev?: boolean
  enableEnvFlag?: boolean
}): boolean {
  const hostname = (options?.hostname || '').toLowerCase()
  const isDemoHost = hostname === 'demo.resiq.co' || hostname.endsWith('.resiq.co')
  return Boolean(options?.isDev || options?.enableEnvFlag || isDemoHost)
}

const DEMO_LOGIN_BYPASS = isDemoLoginBypassEnabled({
  hostname: typeof window !== 'undefined' ? window.location.hostname : '',
  isDev: import.meta.env.DEV,
  enableEnvFlag: import.meta.env.VITE_ENABLE_DEMO_LOGIN_BYPASS === 'true',
})
// Demo-host bypass signs in against the real API so the session carries a
// valid JWT; a fabricated token gets 401s from any endpoint that validates it.
const DEMO_LOGIN_EMAIL = import.meta.env.VITE_DEMO_LOGIN_EMAIL || 'admin@evieai.local'
const DEMO_LOGIN_PASSWORD = import.meta.env.VITE_DEMO_LOGIN_PASSWORD || 'admin'

function isTokenUsable(token: string): boolean {
  const parts = token.split('.')
  if (parts.length !== 3) return false
  try {
    const payload = JSON.parse(atob(parts[1].replace(/-/g, '+').replace(/_/g, '/'))) as { exp?: unknown }
    return typeof payload.exp !== 'number' || payload.exp * 1000 > Date.now() + 60_000
  } catch {
    return false
  }
}

function normalizeApiError(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim().length > 0) return detail

  if (Array.isArray(detail)) {
    const first = detail[0]
    if (first && typeof first === 'object' && 'msg' in first) {
      const msg = (first as { msg?: unknown }).msg
      if (typeof msg === 'string' && msg.trim().length > 0) return msg
    }
  }

  if (detail && typeof detail === 'object' && 'msg' in detail) {
    const msg = (detail as { msg?: unknown }).msg
    if (typeof msg === 'string' && msg.trim().length > 0) return msg
  }

  return fallback
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<{ token: string; user: User } | null>(() => {
    const stored = loadSession()
    if (stored && isTokenUsable(stored.token)) return stored
    clearSession()
    return null
  })
  const [isLoading, setIsLoading] = useState(false)

  const user = session?.user || null
  const token = session?.token || null
  const isAdmin = user?.role === 'admin'

  const login = useCallback(async (email: string, password: string): Promise<string | null> => {
    setIsLoading(true)
    try {
      const resp = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await resp.json()
      if (!resp.ok) {
        return normalizeApiError(data?.detail, 'Login failed')
      }
      saveSession(data.access_token, data.user)
      setSession({ token: data.access_token, user: data.user })
      return null
    } catch (e) {
      return 'Network error'
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(() => {
    clearSession()
    setSession(null)
  }, [])

  useEffect(() => {
    if (DEMO_LOGIN_BYPASS && !session) {
      void login(DEMO_LOGIN_EMAIL, DEMO_LOGIN_PASSWORD)
    }
  }, [session, login])

  const register = useCallback(
    async (email: string, password: string, role: 'admin' | 'user' = 'user'): Promise<string | null> => {
      setIsLoading(true)
      try {
        const resp = await fetch(`${API_BASE}/auth/register`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password, role }),
        })
        const data = await resp.json()
        if (!resp.ok) {
          return normalizeApiError(data?.detail, 'Registration failed')
        }
        saveSession(data.access_token, data.user)
        setSession({ token: data.access_token, user: data.user })
        return null
      } catch (e) {
        return 'Network error'
      } finally {
        setIsLoading(false)
      }
    },
    []
  )

  return (
    <AuthContext.Provider value={{ user, token, login, logout, register, isAdmin, isLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthCtx {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function useAuthHeader(): string | undefined {
  const ctx = useContext(AuthContext)
  if (!ctx) return undefined
  return ctx.token ? `Bearer ${ctx.token}` : undefined
}
