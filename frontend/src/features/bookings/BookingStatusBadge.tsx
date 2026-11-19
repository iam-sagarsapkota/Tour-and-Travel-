import { cn } from "@/lib/utils"
import type { BookingStatus } from "@/types/api"

const STYLES: Record<BookingStatus, { label: string; className: string }> = {
  pending: { label: "Awaiting payment", className: "bg-amber-100 text-amber-900" },
  confirmed: { label: "Confirmed", className: "bg-emerald-100 text-emerald-900" },
  cancelled: { label: "Cancelled", className: "bg-muted text-muted-foreground" },
  expired: { label: "Expired", className: "bg-muted text-muted-foreground" },
}

export function BookingStatusBadge({ status }: { status: BookingStatus }) {
  const style = STYLES[status]
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        style.className,
      )}
    >
      {style.label}
    </span>
  )
}
