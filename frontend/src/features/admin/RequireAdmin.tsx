import { Navigate, Outlet, useLocation } from "react-router-dom"

import { PageSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState } from "@/components/States"
import { useAuth } from "@/features/auth/AuthContext"
import { authRedirect } from "@/lib/safeNext"

/**
 * Admin area guard. A convenience only: every /admin API endpoint checks the
 * role on the server and answers 403 regardless of what the browser shows.
 */
export function RequireAdmin() {
  const { status, user } = useAuth()
  const location = useLocation()

  if (status === "loading") return <PageSkeleton />
  if (status === "guest") {
    return (
      <Navigate to={authRedirect("/login", `${location.pathname}${location.search}`)} replace />
    )
  }
  if (user?.role !== "admin" && user?.role !== "super_admin") {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <EmptyState
          title="Admins only"
          description="Your account doesn't have access to the admin area."
        />
      </div>
    )
  }
  return <Outlet />
}
