import { Link } from "react-router-dom"

import { CardGridSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState, ErrorState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { useDashboard } from "@/features/account/queries"
import { useAuth } from "@/features/auth/AuthContext"
import { BookingStatusBadge } from "@/features/bookings/BookingStatusBadge"
import { EventCard } from "@/features/events/EventCard"
import { formatDate, formatMoney } from "@/lib/format"
import type { Booking } from "@/types/api"

function StatTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border bg-card p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 font-heading text-3xl font-extrabold text-forest">{value}</p>
    </div>
  )
}

function TripRow({ booking, action }: { booking: Booking; action?: React.ReactNode }) {
  return (
    <li className="flex flex-col gap-3 rounded-xl border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="font-semibold text-forest">
          <Link to={`/dashboard/bookings/${booking.id}`} className="hover:underline">
            {booking.adventure.title}
          </Link>
        </p>
        <p className="text-sm text-muted-foreground">
          {formatDate(booking.departure.start_date)} · {booking.reference} ·{" "}
          {formatMoney(booking.total_amount, booking.currency)}
        </p>
      </div>
      <div className="flex items-center gap-3">
        <BookingStatusBadge status={booking.status} />
        {action}
      </div>
    </li>
  )
}

export default function OverviewPage() {
  const { user } = useAuth()
  const { data, isPending, isError, error, refetch } = useDashboard()

  return (
    <div className="mx-auto max-w-6xl space-y-10 px-4 py-10">
      <h1 className="text-3xl font-extrabold text-forest">
        Namaste{user ? `, ${user.full_name.split(" ")[0]}` : ""}
      </h1>

      {isPending ? (
        <CardGridSkeleton count={3} />
      ) : isError ? (
        <ErrorState message={error.message} onRetry={() => refetch()} />
      ) : (
        <>
          <section aria-label="Summary" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Upcoming trips" value={String(data.counts.upcoming)} />
            <StatTile label="Completed adventures" value={String(data.counts.completed)} />
            <StatTile label="Bookings made" value={String(data.counts.total)} />
            <StatTile label="Total paid" value={formatMoney(data.total_spent, data.currency)} />
          </section>

          {data.pending_payment.length > 0 && (
            <section aria-labelledby="pending-heading">
              <h2 id="pending-heading" className="text-xl font-bold text-forest">
                Waiting for payment
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Your places are held for a short time. Pay to confirm them.
              </p>
              <ul className="mt-4 space-y-3">
                {data.pending_payment.map((booking) => (
                  <TripRow
                    key={booking.id}
                    booking={booking}
                    action={
                      <Link
                        to={`/dashboard/bookings/${booking.id}`}
                        className={buttonVariants({ className: "h-10 px-4" })}
                      >
                        Pay now
                      </Link>
                    }
                  />
                ))}
              </ul>
            </section>
          )}

          <section aria-labelledby="upcoming-heading">
            <div className="flex items-end justify-between">
              <h2 id="upcoming-heading" className="text-xl font-bold text-forest">
                Upcoming trips
              </h2>
              <Link
                to="/dashboard/bookings"
                className="text-sm font-semibold text-forest hover:underline"
              >
                All bookings
              </Link>
            </div>
            <div className="mt-4">
              {data.upcoming.length === 0 ? (
                <EmptyState
                  title="No trips planned yet"
                  action={
                    <Link to="/events" className={buttonVariants({ className: "h-10 px-4" })}>
                      Find an adventure
                    </Link>
                  }
                />
              ) : (
                <ul className="space-y-3">
                  {data.upcoming.map((booking) => (
                    <TripRow key={booking.id} booking={booking} />
                  ))}
                </ul>
              )}
            </div>
          </section>

          {data.recommendations.length > 0 && (
            <section aria-labelledby="recommended-heading">
              <h2 id="recommended-heading" className="text-xl font-bold text-forest">
                You might also like
              </h2>
              <ul className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {data.recommendations.map((event) => (
                  <li key={event.id}>
                    <EventCard event={event} />
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </div>
  )
}
