import { CheckCircle2Icon, Clock3Icon, XCircleIcon } from "lucide-react"
import { useMemo } from "react"
import { Link, useParams, useSearchParams } from "react-router-dom"

import { ErrorState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { useVerifyPayment } from "@/features/payments/payments"
import { formatMoney } from "@/lib/format"

/**
 * Where eSewa/Khalti send the traveller back. The URL's own parameters prove
 * nothing; we pass them to our server, which asks the provider directly.
 */
export default function PaymentReturnPage() {
  const { attemptId = "" } = useParams()
  const [search] = useSearchParams()
  const params = useMemo(() => Object.fromEntries(search.entries()), [search])
  const { data, isPending, isError, error, refetch } = useVerifyPayment(attemptId, params)

  if (isPending) {
    return (
      <div role="status" className="mx-auto max-w-xl px-4 py-20 text-center">
        <Clock3Icon className="mx-auto size-12 text-gold-dark" aria-hidden="true" />
        <h1 className="mt-4 text-2xl font-bold text-forest">Checking your payment…</h1>
        <p className="mt-2 text-muted-foreground">
          We're confirming with the payment provider. Please don't close this page.
        </p>
      </div>
    )
  }
  if (isError) {
    return (
      <div className="mx-auto max-w-xl px-4 py-16">
        <ErrorState
          title="We couldn't check this payment yet"
          message={`${error.message} If money left your account, it will be matched to your booking automatically.`}
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const { attempt, payment } = data
  const bookingLink = (
    <Link
      to={`/dashboard/bookings/${payment.booking_id}`}
      className={buttonVariants({ className: "h-11 px-5" })}
    >
      View booking {payment.booking_reference}
    </Link>
  )

  if (attempt.status === "successful") {
    const confirmed = payment.booking_status === "confirmed"
    return (
      <div className="mx-auto max-w-xl px-4 py-16 text-center">
        <CheckCircle2Icon className="mx-auto size-14 text-success" aria-hidden="true" />
        <h1 className="mt-4 text-3xl font-extrabold text-forest">
          {confirmed ? "Payment received - you're booked!" : "Payment received"}
        </h1>
        <p className="mt-2 text-muted-foreground">
          {formatMoney(attempt.amount, attempt.currency)} paid for {payment.adventure}.
          {confirmed
            ? " Your places are confirmed."
            : " We couldn't confirm the places automatically; our team will contact you and refund you if needed."}
        </p>
        {attempt.gateway_transaction_id && (
          <p className="mt-2 text-sm text-muted-foreground">
            Provider reference: {attempt.gateway_transaction_id}
          </p>
        )}
        <div className="mt-6">{bookingLink}</div>
      </div>
    )
  }

  if (attempt.status === "initiated" || attempt.status === "processing") {
    return (
      <div role="status" className="mx-auto max-w-xl px-4 py-16 text-center">
        <Clock3Icon className="mx-auto size-12 text-gold-dark" aria-hidden="true" />
        <h1 className="mt-4 text-2xl font-bold text-forest">Payment still processing</h1>
        <p className="mt-2 text-muted-foreground">
          The provider hasn't finished this payment yet. This page checks again automatically, and
          your booking updates as soon as it completes. Please don't pay a second time.
        </p>
        <div className="mt-6">{bookingLink}</div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-xl px-4 py-16 text-center">
      <XCircleIcon className="mx-auto size-12 text-destructive" aria-hidden="true" />
      <h1 className="mt-4 text-2xl font-bold text-forest">
        {attempt.status === "cancelled" ? "Payment cancelled" : "Payment not completed"}
      </h1>
      <p className="mt-2 text-muted-foreground">
        This payment didn't go through. If your places are still held, you can try again from your
        booking.
      </p>
      <div className="mt-6">{bookingLink}</div>
    </div>
  )
}
