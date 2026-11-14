import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react"
import type { ReactNode } from "react"

import { api, refreshSession, setSessionExpiredHandler } from "@/lib/api"
import { tokenStore } from "@/lib/tokens"
import type { AuthResponse, User } from "@/types/api"

export interface RegisterInput {
  full_name: string
  email?: string
  phone?: string
  password: string
  password_confirm: string
}

type Status = "loading" | "authenticated" | "guest"

interface AuthContextValue {
  user: User | null
  status: Status
  login: (identifier: string, password: string) => Promise<User>
  register: (input: RegisterInput) => Promise<User>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [status, setStatus] = useState<Status>("loading")

  const signOutLocally = useCallback(() => {
    tokenStore.clear()
    setUser(null)
    setStatus("guest")
  }, [])

  // Restore the session after a reload using the stored refresh token.
  useEffect(() => {
    let cancelled = false
    setSessionExpiredHandler(signOutLocally)
    ;(async () => {
      if (!tokenStore.getRefresh() || !(await refreshSession())) {
        if (!cancelled) setStatus("guest")
        return
      }
      try {
        const me = await api<User>("/auth/me/")
        if (!cancelled) {
          setUser(me)
          setStatus("authenticated")
        }
      } catch {
        if (!cancelled) signOutLocally()
      }
    })()
    return () => {
      cancelled = true
    }
  }, [signOutLocally])

  const accept = useCallback((response: AuthResponse) => {
    tokenStore.set(response.tokens)
    setUser(response.user)
    setStatus("authenticated")
    return response.user
  }, [])

  const login = useCallback(
    async (identifier: string, password: string) =>
      accept(
        await api<AuthResponse>("/auth/login/", {
          method: "POST",
          body: { identifier, password },
          auth: false,
        }),
      ),
    [accept],
  )

  const register = useCallback(
    async (input: RegisterInput) =>
      accept(
        await api<AuthResponse>("/auth/register/", { method: "POST", body: input, auth: false }),
      ),
    [accept],
  )

  const logout = useCallback(async () => {
    const refresh = tokenStore.getRefresh()
    try {
      if (refresh) await api("/auth/logout/", { method: "POST", body: { refresh } })
    } catch {
      // Server-side revocation failed (e.g. offline); still end the local session.
    } finally {
      signOutLocally()
    }
  }, [signOutLocally])

  const value = useMemo(
    () => ({ user, status, login, register, logout }),
    [user, status, login, register, logout],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error("useAuth must be used inside <AuthProvider>")
  return context
}

/** Test helper: provide a fixed auth state without touching the network. */
export function StaticAuthProvider({
  children,
  value,
}: {
  children: ReactNode
  value: Partial<AuthContextValue>
}) {
  const full: AuthContextValue = {
    user: null,
    status: "guest",
    login: async () => {
      throw new Error("not implemented")
    },
    register: async () => {
      throw new Error("not implemented")
    },
    logout: async () => {},
    ...value,
  }
  return <AuthContext.Provider value={full}>{children}</AuthContext.Provider>
}
