import { CircleAlertIcon, CompassIcon } from "lucide-react"
import type { ReactNode } from "react"

import { Button } from "@/components/ui/button"

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed bg-card px-6 py-14 text-center">
      <CompassIcon className="size-10 text-muted-foreground" aria-hidden="true" />
      <h2 className="mt-4 text-lg font-semibold">{title}</h2>
      {description && <p className="mt-1 max-w-md text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  )
}

export function ErrorState({
  title = "We couldn't load this",
  message,
  onRetry,
}: {
  title?: string
  message?: string
  onRetry?: () => void
}) {
  return (
    <div
      role="alert"
      className="flex flex-col items-center rounded-2xl border border-destructive/30 bg-destructive/5 px-6 py-14 text-center"
    >
      <CircleAlertIcon className="size-10 text-destructive" aria-hidden="true" />
      <h2 className="mt-4 text-lg font-semibold">{title}</h2>
      <p className="mt-1 max-w-md text-muted-foreground">
        {message ?? "Check your connection and try again."}
      </p>
      {onRetry && (
        <Button variant="outline" className="mt-5 h-10 px-4" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
