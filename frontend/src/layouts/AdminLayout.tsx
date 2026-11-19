import { NavLink, Outlet } from "react-router-dom"

import { cn } from "@/lib/utils"

const SECTIONS = [
  { to: "/admin", label: "Dashboard", end: true },
  { to: "/admin/bookings", label: "Bookings" },
  { to: "/admin/payments", label: "Payments" },
  { to: "/admin/departures", label: "Departures" },
  { to: "/admin/adventures", label: "Adventures" },
  { to: "/admin/users", label: "Users" },
  { to: "/admin/inbox", label: "Inbox" },
  { to: "/admin/audit", label: "Audit log" },
  { to: "/admin/settings", label: "Settings" },
]

export function AdminLayout() {
  return (
    <div className="bg-background">
      <div className="border-b bg-card">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-4">
          <span className="shrink-0 rounded bg-forest px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-offwhite">
            Admin
          </span>
          <nav aria-label="Admin" className="flex gap-1 overflow-x-auto">
            {SECTIONS.map((section) => (
              <NavLink
                key={section.to}
                to={section.to}
                end={section.end}
                className={({ isActive }) =>
                  cn(
                    "-mb-px flex min-h-12 shrink-0 items-center border-b-2 px-3 text-sm font-semibold",
                    isActive
                      ? "border-gold-dark text-forest"
                      : "border-transparent text-muted-foreground hover:text-forest",
                  )
                }
              >
                {section.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
      <div className="mx-auto max-w-6xl px-4 py-8">
        <Outlet />
      </div>
    </div>
  )
}
