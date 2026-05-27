import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

export type User = {
  username: string
  password: string
  role: 'admin' | 'user'
}

const DEFAULT_USERS: User[] = [
  { username: 'admin', password: 'admin', role: 'admin' },
]

const STORAGE_KEY = 'aiagent_users'
const SESSION_KEY = 'aiagent_session'

function loadUsers(): User[] {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw) {
    try {
      return JSON.parse(raw)
    } catch {
      return DEFAULT_USERS
    }
  }
  return DEFAULT_USERS
}

function saveUsers(users: User[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(users))
}

function loadSession(): string | null {
  return localStorage.getItem(SESSION_KEY)
}

function saveSession(username: string | null) {
  if (username) localStorage.setItem(SESSION_KEY, username)
  else localStorage.removeItem(SESSION_KEY)
}

type AuthCtx = {
  user: User | null
  users: User[]
  login: (username: string, password: string) => boolean
  logout: () => void
  addUser: (username: string, password: string, role: 'admin' | 'user') => boolean
  removeUser: (username: string) => boolean
  isAdmin: boolean
}

const AuthContext = createContext<AuthCtx | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>(() => loadUsers())
  const [session, setSession] = useState<string | null>(() => loadSession())

  const user = session ? users.find((u) => u.username === session) || null : null
  const isAdmin = user?.role === 'admin'

  const login = useCallback((username: string, password: string): boolean => {
    const found = users.find((u) => u.username === username && u.password === password)
    if (found) {
      setSession(found.username)
      saveSession(found.username)
      return true
    }
    return false
  }, [users])

  const logout = useCallback(() => {
    setSession(null)
    saveSession(null)
  }, [])

  const addUser = useCallback((username: string, password: string, role: 'admin' | 'user'): boolean => {
    if (users.some((u) => u.username === username)) return false
    const next = [...users, { username, password, role }]
    setUsers(next)
    saveUsers(next)
    return true
  }, [users])

  const removeUser = useCallback((username: string): boolean => {
    if (username === 'admin') return false // protect default admin
    const next = users.filter((u) => u.username !== username)
    if (next.length === users.length) return false
    setUsers(next)
    saveUsers(next)
    if (session === username) {
      setSession(null)
      saveSession(null)
    }
    return true
  }, [users, session])

  return (
    <AuthContext.Provider value={{ user: user || null, users, login, logout, addUser, removeUser, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthCtx {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
