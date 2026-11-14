import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"

export function PriceDisplay({
  amount,
  currency,
  prefix = "From",
  suffix = "per person",
  className,
}: {
  amount: string
  currency: string
  prefix?: string | null
  suffix?: string | null
  className?: string
}) {
  return (
    <p className={cn("text-sm text-muted-foreground", className)}>
      {prefix && <span>{prefix} </span>}
      <span className="font-heading text-lg font-bold text-forest">
        {formatMoney(amount, currency)}
      </span>
      {suffix && <span> {suffix}</span>}
    </p>
  )
}
