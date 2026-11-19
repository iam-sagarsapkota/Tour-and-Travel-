import { lazy, Suspense } from "react"
import { Link, Route, Routes } from "react-router-dom"

import { PageSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { LoginPage, RegisterPage } from "@/features/auth/AuthForms"
import { RequireAuth } from "@/features/auth/RequireAuth"
import { RootLayout } from "@/layouts/RootLayout"

// Route-level code splitting.
const HomePage = lazy(() => import("@/pages/HomePage"))
const EventsPage = lazy(() => import("@/pages/EventsPage"))
const EventDetailPage = lazy(() => import("@/pages/EventDetailPage"))
const BookingPage = lazy(() => import("@/pages/BookingPage"))
const MyBookingsPage = lazy(() => import("@/pages/dashboard/MyBookingsPage"))
const BookingDetailPage = lazy(() => import("@/pages/dashboard/BookingDetailPage"))
const DestinationsPage = lazy(() =>
  import("@/pages/DestinationPages").then((module) => ({ default: module.DestinationsPage })),
)
const DestinationDetailPage = lazy(() =>
  import("@/pages/DestinationPages").then((module) => ({ default: module.DestinationDetailPage })),
)

function NotFoundPage() {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16">
      <EmptyState
        title="Page not found"
        description="The trail ends here. Head back to the adventures."
        action={
          <Link to="/events" className={buttonVariants({ className: "h-10 px-4" })}>
            Browse adventures
          </Link>
        }
      />
    </div>
  )
}

export function AppRoutes() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <Routes>
        <Route element={<RootLayout />}>
          <Route index element={<HomePage />} />
          <Route path="events" element={<EventsPage />} />
          <Route path="destinations" element={<DestinationsPage />} />
          <Route path="destinations/:slug" element={<DestinationDetailPage />} />
          <Route path="login" element={<LoginPage />} />
          <Route path="register" element={<RegisterPage />} />

          {/* Account required. The API enforces this as well. */}
          <Route element={<RequireAuth />}>
            <Route path="events/:slug" element={<EventDetailPage />} />
            <Route path="events/:slug/book/:departureId" element={<BookingPage />} />
            <Route path="dashboard/bookings" element={<MyBookingsPage />} />
            <Route path="dashboard/bookings/:id" element={<BookingDetailPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
