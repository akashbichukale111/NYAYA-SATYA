import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { setUserId, endpoints } from './api'

interface SessionUser {
  id: string
  name: string
  email: string
  role: string
}

interface SessionContextValue {
  user: SessionUser | null
  signIn: (name: string, email: string, role: string) => Promise<void>
  signOut: () => void
}

const SessionContext = createContext<SessionContextValue | null>(null)

const STORAGE_KEY = 'rde_session_user'

export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY)
      return raw ? (JSON.parse(raw) as SessionUser) : null
    } catch {
      return null
    }
  })

  useEffect(() => {
    setUserId(user?.id ?? null)
  }, [user])

  const signIn = async (name: string, email: string, role: string) => {
    const created = await endpoints.createUser(name, email, role)
    setUser(created)
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(created))
  }

  const signOut = () => {
    setUser(null)
    window.localStorage.removeItem(STORAGE_KEY)
  }

  return <SessionContext.Provider value={{ user, signIn, signOut }}>{children}</SessionContext.Provider>
}

export function useSession() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSession must be used within SessionProvider')
  return ctx
}
