import { lazy, Suspense } from "react"
import { Link, Route, Routes } from "react-router-dom"

import { PageSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { LoginPage, RegisterPage } from "@/features/auth/AuthForms"
import { RequireAuth } from "@/features/auth/RequireAuth"
import { RequireAdmin } from "@/features/admin/RequireAdmin"
import { AccountLayout } from "@/layouts/AccountLayout"
import { AdminLayout } from "@/layouts/AdminLayout"
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
const admin = () => import("@/pages/admin/OperationsPages")
const catalog = () => import("@/pages/admin/CatalogPages")
const AdminDashboardPage = lazy(() => import("@/pages/admin/DashboardPage"))
const AdminBookingsPage = lazy(() => admin().then((m) => ({ default: m.BookingsPage })))
const AdminPaymentsPage = lazy(() => admin().then((m) => ({ default: m.PaymentsPage })))
const AdminUsersPage = lazy(() => admin().then((m) => ({ default: m.UsersPage })))
const AdminInboxPage = lazy(() => admin().then((m) => ({ default: m.InboxPage })))
const AdminAuditPage = lazy(() => admin().then((m) => ({ default: m.AuditPage })))
const AdminAdventuresPage = lazy(() => catalog().then((m) => ({ default: m.AdventuresPage })))
const AdminAdventureFormPage = lazy(() => catalog().then((m) => ({ default: m.AdventureFormPage })))
const AdminDeparturesPage = lazy(() => catalog().then((m) => ({ default: m.DeparturesPage })))
const AdminSettingsPage = lazy(() => catalog().then((m) => ({ default: m.SettingsPage })))
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

          {/* Admin area. Every /api/v1/admin endpoint checks the role on the server too. */}
          <Route element={<RequireAdmin />}>
            <Route path="admin" element={<AdminLayout />}>
              <Route index element={<AdminDashboardPage />} />
              <Route path="bookings" element={<AdminBookingsPage />} />
              <Route path="payments" element={<AdminPaymentsPage />} />
              <Route path="departures" element={<AdminDeparturesPage />} />
              <Route path="adventures" element={<AdminAdventuresPage />} />
              <Route path="adventures/:id" element={<AdminAdventureFormPage />} />
              <Route path="users" element={<AdminUsersPage />} />
              <Route path="inbox" element={<AdminInboxPage />} />
              <Route path="audit" element={<AdminAuditPage />} />
              <Route path="settings" element={<AdminSettingsPage />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </Suspense>
  )
}
