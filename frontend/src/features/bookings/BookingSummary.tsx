import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

/** Itemised, server-calculated price. Never computes money in the browser. */
export function BookingSummary({
  title,
  startDate,
  endDate,
  participantCount,
  unitPrice,
  total,
  currency,
  updating = false,
  className,
}: {
  title: string
  startDate: string
  endDate: string
  participantCount: number
  unitPrice?: string
  total?: string
  currency: string
  updating?: boolean
  className?: string
}) {
  return (
    <section
      aria-labelledby="summary-heading"
      className={cn("rounded-2xl border bg-card p-5", className)}
    >
      <h2 id="summary-heading" className="text-lg font-bold text-forest">
        Booking summary
      </h2>
      <p className="mt-2 font-semibold">{title}</p>
      <p className="text-sm text-muted-foreground">
        {formatDate(startDate)} - {formatDate(endDate)}
      </p>
      <dl className="mt-4 space-y-2 border-t pt-4 text-sm" aria-busy={updating}>
        <div className="flex justify-between gap-4">
          <dt>Travellers</dt>
          <dd>{participantCount}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt>Price per person</dt>
          <dd>{unitPrice ? formatMoney(unitPrice, currency) : "…"}</dd>
        </div>
        <div className="flex justify-between gap-4 border-t pt-3 text-base font-bold text-forest">
          <dt>Total</dt>
          <dd aria-live="polite">{total ? formatMoney(total, currency) : "Calculating…"}</dd>
        </div>
      </dl>
      <p className="mt-3 text-xs text-muted-foreground">
        Calculated by our server from the current departure price.
      </p>
    </section>
  )
}
