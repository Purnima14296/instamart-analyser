import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { DEMO_TOKENS, getStoredRole, setAuth } from '../api/client'
import type { RoleName } from '../types/api'

interface AuthContextValue {
  role: RoleName
  canReview: boolean
  canRunJobs: boolean
  setRole: (role: RoleName) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [role, setRoleState] = useState<RoleName>(getStoredRole())

  const value = useMemo<AuthContextValue>(
    () => ({
      role,
      canReview: role === 'reviewer' || role === 'admin',
      canRunJobs: role === 'admin',
      setRole: (next: RoleName) => {
        setAuth(next, DEMO_TOKENS[next])
        setRoleState(next)
      },
    }),
    [role],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function RoleGate({
  allow,
  children,
  fallback,
}: {
  allow: 'viewer' | 'reviewer' | 'admin'
  children: ReactNode
  fallback?: ReactNode
}) {
  const { role } = useAuth()
  const rank = { viewer: 1, reviewer: 2, admin: 3 }
  if (rank[role] < rank[allow]) {
    return <>{fallback ?? <p className="muted small">Requires {allow} role or higher.</p>}</>
  }
  return <>{children}</>
}
