import { ArrowLeftIcon } from "lucide-react"
import { useState } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"

import { PageSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState, ErrorState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { useAuth } from "@/features/auth/AuthContext"
import { BookingForm } from "@/features/bookings/BookingForm"
import { BookingSummary } from "@/features/bookings/BookingSummary"
import { useCreateBooking, useQuote } from "@/features/bookings/queries"
import { useEvent } from "@/features/events/queries"
import { ApiError } from "@/lib/api"

/** Mirrors the server's default per-booking limit; the server enforces the real one. */
const MAX_PER_BOOKING = 20

export default function BookingPage() {
  const { slug = "", departureId = "" } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()
  const event = useEvent(slug)
  const create = useCreateBooking()

  const departure = event.data?.departures.find((item) => item.id === departureId)
  const minimum = event.data && !event.data.solo_friendly ? (departure?.min_participants ?? 1) : 1
  const [count, setCount] = useState<number | null>(null)
  const participantCount = count ?? minimum
  const quote = useQuote(departure?.is_bookable ? departureId : "", participantCount)

  if (event.isPending) return <PageSkeleton />
  if (event.isError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        <ErrorState message={event.error.message} onRetry={() => event.refetch()} />
      </div>
    )
  }

  const back = (
    <Link
      to={`/events/${slug}`}
      className="inline-flex items-center gap-1 text-sm font-medium text-forest hover:underline"
    >
      <ArrowLeftIcon className="size-4" aria-hidden="true" />
      Back to {event.data.title}
    </Link>
  )

  if (!departure || !departure.is_bookable) {
    return (
      <div className="mx-auto max-w-3xl space-y-6 px-4 py-10">
        {back}
        <EmptyState
          title="This departure can't be booked"
          description="It may be full, closed, or no longer scheduled. Choose another date."
          action={
            <Link to={`/events/${slug}`} className={buttonVariants({ className: "h-10 px-4" })}>
              See other dates
            </Link>
          }
        />
      </div>
    )
  }

  const maxParticipants = Math.max(
    minimum,
    Math.min(
      departure.seats_available,
      event.data.max_group_size ?? MAX_PER_BOOKING,
      MAX_PER_BOOKING,
    ),
  )
  const error = create.error instanceof ApiError ? create.error : null
  const fieldErrors = error
    ? {
        participants: error.first("participants"),
        policy_accepted: error.first("policy_accepted"),
      }
    : undefined
  const serverError =
    error && !fieldErrors?.participants && !fieldErrors?.policy_accepted
      ? (error.formError ?? error.message)
      : create.error && !error
        ? "Something went wrong. Please try again."
        : undefined

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-10">
      {back}
      <h1 className="text-3xl font-extrabold text-forest">Book your places</h1>
      <div className="grid gap-8 lg:grid-cols-[1fr_20rem]">
        <BookingForm
          departureId={departure.id}
          minParticipants={minimum}
          maxParticipants={maxParticipants}
          leadName={user?.full_name ?? ""}
          cancellationPolicy={event.data.cancellation_policy}
          submitting={create.isPending}
          serverError={serverError}
          fieldErrors={fieldErrors}
          onCountChange={setCount}
          onSubmit={(input) =>
            create.mutate(input, {
              onSuccess: (booking) => navigate(`/dashboard/bookings/${booking.id}`),
            })
          }
        />
        <aside className="lg:sticky lg:top-24 lg:self-start">
          <BookingSummary
            title={event.data.title}
            startDate={departure.start_date}
            endDate={departure.end_date}
            participantCount={participantCount}
            unitPrice={quote.data?.unit_price}
            total={quote.data?.total_amount}
            currency={quote.data?.currency ?? event.data.currency}
            updating={quote.isFetching}
          />
          {quote.isError && (
            <p role="alert" className="mt-3 text-sm text-destructive">
              We couldn't calculate the price. Check your connection.
            </p>
          )}
        </aside>
      </div>
    </div>
  )
}
