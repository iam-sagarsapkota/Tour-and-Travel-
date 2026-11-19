import { ArrowLeftIcon } from "lucide-react"
import { useState } from "react"
import { Link, useParams } from "react-router-dom"
import { toast } from "sonner"

import { PageSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState, ErrorState } from "@/components/States"
import { Button, buttonVariants } from "@/components/ui/button"
import { BookingStatusBadge } from "@/features/bookings/BookingStatusBadge"
import { useBooking, useCancelBooking } from "@/features/bookings/queries"
import { ApiError } from "@/lib/api"
import { formatDate, formatMoney } from "@/lib/format"
import type { Booking } from "@/types/api"

function formatTime(iso: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    day: "numeric",
    month: "short",
  }).format(new Date(iso))
}

function StatusNotice({ booking }: { booking: Booking }) {
  if (booking.status === "pending" && booking.expires_at) {
    return (
      <div className="rounded-xl border border-warning/40 bg-amber-50 p-4 text-sm text-amber-950">
        <p className="font-semibold">
          Your places are held until {formatTime(booking.expires_at)}.
        </p>
        <p className="mt-1">
          Online payment with eSewa, Khalti and card is being added in the next release. If the hold
          lapses before payment, the places return to sale and this booking expires.
        </p>
      </div>
    )
  }
  if (booking.status === "confirmed") {
    return (
      <p className="rounded-xl bg-emerald-50 p-4 text-sm font-medium text-emerald-950">
        Your booking is confirmed. We look forward to trekking with you.
      </p>
    )
  }
  if (booking.status === "expired") {
    return (
      <p className="rounded-xl bg-muted p-4 text-sm">
        This hold expired before payment, so the places were released.
      </p>
    )
  }
  return (
    <p className="rounded-xl bg-muted p-4 text-sm">
      This booking was cancelled
      {booking.cancelled_at ? ` on ${formatTime(booking.cancelled_at)}` : ""}.
      {booking.cancellation_reason && ` Reason: ${booking.cancellation_reason}`}
    </p>
  )
}

function CancelControl({ booking }: { booking: Booking }) {
  const cancel = useCancelBooking()
  const [confirming, setConfirming] = useState(false)

  if (!booking.can_cancel) {
    return booking.status === "confirmed" ? (
      <p className="text-sm text-muted-foreground">
        To cancel a paid booking, please contact us. Online refunds are coming soon.
      </p>
    ) : null
  }
  if (!confirming) {
    return (
      <Button variant="outline" className="h-11 px-4" onClick={() => setConfirming(true)}>
        Cancel booking
      </Button>
    )
  }
  return (
    <div role="group" aria-labelledby="cancel-question" className="rounded-xl border p-4">
      <p id="cancel-question" className="font-semibold">
        Cancel booking {booking.reference}?
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        Your places will be released to other travellers. This can't be undone.
      </p>
      {cancel.isError && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {cancel.error instanceof ApiError ? cancel.error.message : "Something went wrong."}
        </p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          variant="destructive"
          className="h-11 px-4"
          disabled={cancel.isPending}
          onClick={() =>
            cancel.mutate(booking.id, {
              onSuccess: () => {
                setConfirming(false)
                toast.success("Booking cancelled")
              },
            })
          }
        >
          {cancel.isPending ? "Cancelling…" : "Yes, cancel it"}
        </Button>
        <Button variant="outline" className="h-11 px-4" onClick={() => setConfirming(false)}>
          Keep booking
        </Button>
      </div>
    </div>
  )
}

export default function BookingDetailPage() {
  const { id = "" } = useParams()
  const { data: booking, isPending, isError, error, refetch } = useBooking(id)

  if (isPending) return <PageSkeleton />
  if (isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        {error instanceof ApiError && error.status === 404 ? (
          <EmptyState
            title="Booking not found"
            action={
              <Link to="/dashboard/bookings" className={buttonVariants({ className: "h-10 px-4" })}>
                My bookings
              </Link>
            }
          />
        ) : (
          <ErrorState message={error.message} onRetry={() => refetch()} />
        )}
      </div>
    )
  }

  return (
    <article className="mx-auto max-w-3xl space-y-6 px-4 py-10">
      <Link
        to="/dashboard/bookings"
        className="inline-flex items-center gap-1 text-sm font-medium text-forest hover:underline"
      >
        <ArrowLeftIcon className="size-4" aria-hidden="true" />
        My bookings
      </Link>

      <header>
        <p className="text-sm font-semibold tracking-wide text-muted-foreground">
          Booking {booking.reference}
        </p>
        <h1 className="mt-1 text-3xl font-extrabold text-forest">{booking.adventure.title}</h1>
        <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
          <BookingStatusBadge status={booking.status} />
          <span>
            {formatDate(booking.departure.start_date)} - {formatDate(booking.departure.end_date)}
          </span>
          <span>{booking.adventure.destination}</span>
        </div>
      </header>

      <StatusNotice booking={booking} />

      <section aria-labelledby="price-heading" className="rounded-2xl border bg-card p-5">
        <h2 id="price-heading" className="text-lg font-bold text-forest">
          Price
        </h2>
        <dl className="mt-3 space-y-2 text-sm">
          <div className="flex justify-between">
            <dt>
              {booking.participant_count} × {formatMoney(booking.unit_price, booking.currency)}
            </dt>
            <dd>{formatMoney(booking.total_amount, booking.currency)}</dd>
          </div>
          <div className="flex justify-between border-t pt-2 text-base font-bold text-forest">
            <dt>Total</dt>
            <dd>{formatMoney(booking.total_amount, booking.currency)}</dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="travellers-heading" className="rounded-2xl border bg-card p-5">
        <h2 id="travellers-heading" className="text-lg font-bold text-forest">
          Travellers
        </h2>
        <ul className="mt-3 divide-y">
          {booking.participants.map((person, index) => (
            <li key={index} className="flex justify-between py-2 text-sm">
              <span className="font-medium">{person.full_name}</span>
              <span className="text-muted-foreground">
                {[person.is_lead && "Lead", person.nationality].filter(Boolean).join(" · ")}
              </span>
            </li>
          ))}
        </ul>
      </section>

      {booking.adventure.cancellation_policy && (
        <section className="rounded-2xl border bg-card p-5">
          <h2 className="text-lg font-bold text-forest">Cancellation policy</h2>
          <p className="mt-2 whitespace-pre-line text-sm">
            {booking.adventure.cancellation_policy}
          </p>
        </section>
      )}

      <div className="flex flex-wrap items-center gap-3">
        <CancelControl booking={booking} />
        <Link
          to={`/events/${booking.adventure.slug}`}
          className={buttonVariants({ variant: "ghost", className: "h-11 px-4" })}
        >
          View trip details
        </Link>
      </div>
    </article>
  )
}
