import { MenuIcon, MountainIcon, XIcon } from "lucide-react"
import { useEffect, useState } from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom"

import { Button, buttonVariants } from "@/components/ui/button"
import { Toaster } from "@/components/ui/sonner"
import { useAuth } from "@/features/auth/AuthContext"
import { cn } from "@/lib/utils"

const YEAR = new Date().getFullYear()

const NAV = [
  { to: "/events", label: "Adventures" },
  { to: "/destinations", label: "Destinations" },
]

function navClass({ isActive }: { isActive: boolean }) {
  return cn(
    "rounded-lg px-3 py-2 text-sm font-medium text-offwhite/85 hover:bg-white/10 hover:text-offwhite",
    isActive && "bg-white/10 text-offwhite",
  )
}

function Navbar() {
  const { user, status, logout } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)

  async function onLogout() {
    await logout()
    navigate("/")
  }

  const account =
    status === "authenticated" && user ? (
      <>
        <span className="px-3 text-sm text-offwhite/85">Hi, {user.full_name.split(" ")[0]}</span>
        <Button
          variant="outline"
          className="h-10 border-white/30 bg-transparent px-4 text-offwhite hover:bg-white/10 hover:text-offwhite"
          onClick={onLogout}
        >
          Log out
        </Button>
      </>
    ) : status === "guest" ? (
      <>
        <NavLink to="/login" className={navClass}>
          Log in
        </NavLink>
        <Link
          to="/register"
          className={cn(
            buttonVariants(),
            "h-10 bg-gold px-4 font-semibold text-forest hover:bg-gold/90",
          )}
        >
          Sign up
        </Link>
      </>
    ) : null

  return (
    <header className="sticky top-0 z-40 bg-forest text-offwhite shadow-sm">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:rounded-lg focus:bg-gold focus:px-3 focus:py-2 focus:text-forest"
      >
        Skip to content
      </a>
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4">
        <Link to="/" className="flex items-center gap-2 font-heading text-lg font-extrabold">
          <MountainIcon className="size-6 text-gold" aria-hidden="true" />
          Himalaya Trails
        </Link>

        <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} className={navClass}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="hidden items-center gap-2 md:flex">{account}</div>

        <button
          type="button"
          className="flex size-11 items-center justify-center rounded-lg hover:bg-white/10 md:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <XIcon aria-hidden="true" /> : <MenuIcon aria-hidden="true" />}
          <span className="sr-only">{open ? "Close menu" : "Open menu"}</span>
        </button>
      </div>

      {open && (
        // Any link or button chosen inside the menu closes it.
        <div
          id="mobile-menu"
          className="border-t border-white/10 px-4 pb-4 pt-2 md:hidden"
          onClick={() => setOpen(false)}
        >
          <nav aria-label="Main" className="flex flex-col gap-1">
            {NAV.map((item) => (
              <NavLink key={item.to} to={item.to} className={navClass}>
                {item.label}
              </NavLink>
            ))}
          </nav>
          <div className="mt-3 flex flex-col gap-2 border-t border-white/10 pt-3">{account}</div>
        </div>
      )}
    </header>
  )
}

function Footer() {
  return (
    <footer className="mt-16 bg-forest text-offwhite/85">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-3">
        <div>
          <p className="flex items-center gap-2 font-heading text-lg font-extrabold text-offwhite">
            <MountainIcon className="size-5 text-gold" aria-hidden="true" />
            Himalaya Trails
          </p>
          <p className="mt-2 text-sm">Discover Nepal. Find Your Trail. Book Your Adventure.</p>
        </div>
        <nav aria-label="Footer" className="text-sm">
          <p className="font-semibold text-offwhite">Explore</p>
          <ul className="mt-2 space-y-1.5">
            {NAV.map((item) => (
              <li key={item.to}>
                <Link to={item.to} className="hover:text-gold hover:underline">
                  {item.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <p className="text-sm">
          Trek information on this site is a guide only. Always confirm permits, weather and route
          conditions with official sources before you travel.
        </p>
      </div>
      <p className="border-t border-white/10 py-4 text-center text-xs">© {YEAR} Himalaya Trails</p>
    </footer>
  )
}

export function RootLayout() {
  const { pathname } = useLocation()
  useEffect(() => window.scrollTo(0, 0), [pathname])

  return (
    <div className="flex min-h-dvh flex-col">
      <Navbar />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <Toaster />
    </div>
  )
}
