import { Navigate, Outlet, useLocation } from "react-router-dom"

import { PageSkeleton } from "@/components/LoadingSkeleton"
import { authRedirect } from "@/lib/safeNext"

import { useAuth } from "./AuthContext"

/**
 * Route guard for pages that need an account (e.g. event detail).
 * Guests are sent to registration with a return path. This is a usability
 * control only: the API enforces authentication on its own.
 */
export function RequireAuth() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === "loading") return <PageSkeleton />
  if (status === "guest") {
    const next = `${location.pathname}${location.search}`
    return <Navigate to={authRedirect("/register", next)} replace />
  }
  return <Outlet />
}
