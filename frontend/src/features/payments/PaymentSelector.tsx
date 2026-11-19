import { useState } from "react"
import type { FormEvent } from "react"

import { Button } from "@/components/ui/button"
import { ApiError } from "@/lib/api"
import { formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { PaymentProvider } from "@/types/api"

/**
 * Choose eSewa or Khalti and continue to the provider. No animation here (PRD 10.1):
 * payment controls stay plain and predictable.
 */
export function PaymentSelector({
  providers,
  amount,
  currency,
  submitting,
  error,
  onPay,
}: {
  providers: PaymentProvider[]
  amount: string
  currency: string
  submitting: boolean
  error: unknown
  onPay: (provider: string) => void
}) {
  const [selected, setSelected] = useState(providers[0]?.code ?? "")

  if (providers.length === 0) {
    return (
      <p className="rounded-xl bg-muted p-4 text-sm">
        Online payment is not available right now. Please contact us to pay for this booking.
      </p>
    )
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (selected) onPay(selected)
  }

  const chosen = providers.find((provider) => provider.code === selected)
  const message =
    error instanceof ApiError
      ? (error.first("provider") ?? error.message)
      : error
        ? "Something went wrong. Please try again."
        : undefined

  return (
    <form onSubmit={submit} className="space-y-4" aria-label="Payment">
      <fieldset>
        <legend className="text-lg font-bold text-forest">Pay with</legend>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {providers.map((provider) => (
            <label
              key={provider.code}
              className={cn(
                "flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border bg-card px-4 font-semibold",
                selected === provider.code && "border-forest ring-2 ring-forest/30",
              )}
            >
              <input
                type="radio"
                name="provider"
                value={provider.code}
                className="size-5 accent-forest"
                checked={selected === provider.code}
                onChange={() => setSelected(provider.code)}
              />
              {provider.name}
            </label>
          ))}
        </div>
      </fieldset>
      {message && (
        <p role="alert" className="rounded-lg bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {message}
        </p>
      )}
      <Button
        type="submit"
        className="h-12 w-full text-base sm:w-auto sm:px-8"
        disabled={submitting}
      >
        {submitting
          ? "Connecting to the provider…"
          : `Pay ${formatMoney(amount, currency)}${chosen ? ` with ${chosen.name}` : ""}`}
      </Button>
      <p className="text-xs text-muted-foreground">
        You'll be taken to {chosen?.name ?? "the provider"} to pay securely, then brought back here.
        We never see your wallet credentials.
      </p>
    </form>
  )
}
