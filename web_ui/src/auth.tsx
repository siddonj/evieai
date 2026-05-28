import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export type User = {
  id: string
  email: string
  role: 'admin' | 'user'
}

const API_BASE = import.meta.env.VITE_ORCHESTRATOR_URL || 'http://localhost:8000'

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

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<{ token: string; user: User } | null>(() => loadSession())
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
        return data.detail || 'Login failed'
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
          return data.detail || 'Registration failed'
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
