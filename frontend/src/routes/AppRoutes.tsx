import { lazy, Suspense } from "react"
import { Link, Route, Routes } from "react-router-dom"

import { PageSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { LoginPage, RegisterPage } from "@/features/auth/AuthForms"
import { RequireAuth } from "@/features/auth/RequireAuth"
import { AccountLayout } from "@/layouts/AccountLayout"
import { RootLayout } from "@/layouts/RootLayout"

// Route-level code splitting.
const HomePage = lazy(() => import("@/pages/HomePage"))
const EventsPage = lazy(() => import("@/pages/EventsPage"))
const EventDetailPage = lazy(() => import("@/pages/EventDetailPage"))
const BookingPage = lazy(() => import("@/pages/BookingPage"))
const MyBookingsPage = lazy(() => import("@/pages/dashboard/MyBookingsPage"))
const BookingDetailPage = lazy(() => import("@/pages/dashboard/BookingDetailPage"))
const PaymentReturnPage = lazy(() => import("@/pages/PaymentReturnPage"))
const OverviewPage = lazy(() => import("@/pages/dashboard/OverviewPage"))
const PaymentsPage = lazy(() => import("@/pages/dashboard/PaymentsPage"))
const ProfilePage = lazy(() => import("@/pages/dashboard/ProfilePage"))
const publicAccount = () => import("@/pages/AccountPublicPages")
const ForgotPasswordPage = lazy(() =>
  publicAccount().then((m) => ({ default: m.ForgotPasswordPage })),
)
const ResetPasswordPage = lazy(() =>
  publicAccount().then((m) => ({ default: m.ResetPasswordPage })),
)
const VerifyEmailPage = lazy(() => publicAccount().then((m) => ({ default: m.VerifyEmailPage })))
const ContactPage = lazy(() => publicAccount().then((m) => ({ default: m.ContactPage })))
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
          <Route path="forgot-password" element={<ForgotPasswordPage />} />
          <Route path="reset-password" element={<ResetPasswordPage />} />
          <Route path="verify-email" element={<VerifyEmailPage />} />
          <Route path="contact" element={<ContactPage />} />

          {/* Account required. The API enforces this as well. */}
          <Route element={<RequireAuth />}>
            <Route path="events/:slug" element={<EventDetailPage />} />
            <Route path="events/:slug/book/:departureId" element={<BookingPage />} />
            <Route path="dashboard" element={<AccountLayout />}>
              <Route index element={<OverviewPage />} />
              <Route path="bookings" element={<MyBookingsPage />} />
              <Route path="bookings/:id" element={<BookingDetailPage />} />
              <Route path="payments" element={<PaymentsPage />} />
              <Route path="profile" element={<ProfilePage />} />
            </Route>
            <Route path="payments/:provider/:attemptId/:outcome" element={<PaymentReturnPage />} />
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
