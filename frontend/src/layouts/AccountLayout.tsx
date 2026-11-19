import { NavLink, Outlet } from "react-router-dom"

import { cn } from "@/lib/utils"

const TABS = [
  { to: "/dashboard", label: "Overview", end: true },
  { to: "/dashboard/bookings", label: "Bookings", end: false },
  { to: "/dashboard/payments", label: "Payments", end: false },
  { to: "/dashboard/profile", label: "Profile & security", end: false },
]

/** Shared navigation for the traveller's account pages. */
export function AccountLayout() {
  return (
    <div>
      <div className="border-b bg-card">
        <nav aria-label="Account" className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-4">
          {TABS.map((tab) => (
            <NavLink
              key={tab.to}
              to={tab.to}
              end={tab.end}
              className={({ isActive }) =>
                cn(
                  "-mb-px flex min-h-12 shrink-0 items-center border-b-2 px-3 text-sm font-semibold",
                  isActive
                    ? "border-gold-dark text-forest"
                    : "border-transparent text-muted-foreground hover:text-forest",
                )
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>
      </div>
      <Outlet />
    </div>
  )
}
