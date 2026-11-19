import { Link } from "react-router-dom"

import { CardGridSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState, ErrorState } from "@/components/States"
import { usePaymentHistory } from "@/features/account/queries"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { PaymentStatus } from "@/types/api"

const STATUS: Record<PaymentStatus, { label: string; className: string }> = {
  pending: { label: "Not paid", className: "bg-muted text-muted-foreground" },
  processing: { label: "Processing", className: "bg-amber-100 text-amber-900" },
  successful: { label: "Paid", className: "bg-emerald-100 text-emerald-900" },
  failed: { label: "Failed", className: "bg-red-100 text-red-900" },
  cancelled: { label: "Cancelled", className: "bg-muted text-muted-foreground" },
  refunded: { label: "Refunded", className: "bg-sky-100 text-sky-900" },
  partially_refunded: { label: "Partly refunded", className: "bg-sky-100 text-sky-900" },
}

function formatDateTime(iso: string) {
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  )
}

export default function PaymentsPage() {
  const { data, isPending, isError, error, refetch } = usePaymentHistory()

  return (
    <div className="mx-auto max-w-4xl px-4 py-10">
      <h1 className="text-3xl font-extrabold text-forest">Payments</h1>
      <p className="mt-1 text-muted-foreground">
        Every payment you started, with the provider's reference. A confirmed booking's email is
        your receipt.
      </p>
      <div className="mt-6">
        {isPending ? (
          <CardGridSkeleton count={2} />
        ) : isError ? (
          <ErrorState message={error.message} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState title="No payments yet" />
        ) : (
          <div className="overflow-x-auto rounded-2xl border bg-card">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <caption className="sr-only">Your payments</caption>
              <thead className="border-b bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                <tr>
                  <th scope="col" className="px-4 py-3">
                    Booking
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Date
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Method
                  </th>
                  <th scope="col" className="px-4 py-3 text-right">
                    Amount
                  </th>
                  <th scope="col" className="px-4 py-3">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {data.results.map((payment) => {
                  const status = STATUS[payment.status]
                  const latest = payment.attempts[0]
                  return (
                    <tr key={payment.id}>
                      <td className="px-4 py-3">
                        <Link
                          to={`/dashboard/bookings/${payment.booking_id}`}
                          className="font-semibold text-forest hover:underline"
                        >
                          {payment.booking_reference}
                        </Link>
                        <p className="text-muted-foreground">{payment.adventure}</p>
                      </td>
                      <td className="px-4 py-3">
                        {formatDateTime(payment.paid_at ?? payment.created_at)}
                      </td>
                      <td className="px-4 py-3 capitalize">
                        {payment.provider || latest?.provider || "-"}
                        {payment.gateway_reference && (
                          <p className="text-xs normal-case text-muted-foreground">
                            Ref {payment.gateway_reference}
                          </p>
                        )}
                      </td>
                      <td className="px-4 py-3 text-right font-semibold">
                        {formatMoney(payment.amount, payment.currency)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            "inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold",
                            status.className,
                          )}
                        >
                          {status.label}
                        </span>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
