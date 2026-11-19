import { Link, useSearchParams } from "react-router-dom"

import { CardGridSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState, ErrorState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { BookingStatusBadge } from "@/features/bookings/BookingStatusBadge"
import { useMyBookings } from "@/features/bookings/queries"
import type { BookingScope } from "@/features/bookings/queries"
import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

const TABS: { value: BookingScope; label: string; empty: string }[] = [
  { value: "upcoming", label: "Upcoming", empty: "No upcoming trips yet." },
  { value: "past", label: "Past", empty: "Completed trips will appear here." },
  { value: "cancelled", label: "Cancelled", empty: "No cancelled or expired bookings." },
]

export default function MyBookingsPage() {
  const [params, setParams] = useSearchParams()
  const scope = (TABS.find((tab) => tab.value === params.get("tab"))?.value ??
    "upcoming") as BookingScope
  const { data, isPending, isError, error, refetch } = useMyBookings(scope)
  const tab = TABS.find((item) => item.value === scope)!

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-extrabold text-forest">My bookings</h1>

      <nav aria-label="Booking lists" className="mt-6 flex gap-2 border-b">
        {TABS.map((item) => (
          <button
            key={item.value}
            type="button"
            aria-current={item.value === scope ? "page" : undefined}
            onClick={() => setParams(item.value === "upcoming" ? {} : { tab: item.value })}
            className={cn(
              "-mb-px min-h-11 border-b-2 px-3 text-sm font-semibold",
              item.value === scope
                ? "border-gold-dark text-forest"
                : "border-transparent text-muted-foreground hover:text-forest",
            )}
          >
            {item.label}
          </button>
        ))}
      </nav>

      <div className="mt-6">
        {isPending ? (
          <CardGridSkeleton count={2} />
        ) : isError ? (
          <ErrorState message={error.message} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState
            title={tab.empty}
            action={
              <Link to="/events" className={buttonVariants({ className: "h-10 px-4" })}>
                Find an adventure
              </Link>
            }
          />
        ) : (
          <ul className="space-y-4">
            {data.results.map((booking) => (
              <li
                key={booking.id}
                className="relative flex flex-col gap-2 rounded-2xl border bg-card p-5 focus-within:shadow-md hover:shadow-md sm:flex-row sm:items-center sm:justify-between"
              >
                <div>
                  <p className="text-xs font-semibold tracking-wide text-muted-foreground">
                    {booking.reference}
                  </p>
                  <h2 className="font-bold text-forest">
                    <Link
                      to={`/dashboard/bookings/${booking.id}`}
                      className="after:absolute after:inset-0 after:rounded-2xl"
                    >
                      {booking.adventure.title}
                    </Link>
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {formatDate(booking.departure.start_date)} ·{" "}
                    {booking.participant_count === 1
                      ? "1 traveller"
                      : `${booking.participant_count} travellers`}
                  </p>
                </div>
                <div className="flex items-center gap-3 sm:flex-col sm:items-end">
                  <BookingStatusBadge status={booking.status} />
                  <p className="font-heading font-bold text-forest">
                    {formatMoney(booking.total_amount, booking.currency)}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
