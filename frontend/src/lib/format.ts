/** Format a decimal string from the API as money, e.g. "NPR 38,000". */
export function formatMoney(amount: string, currency: string): string {
  const value = Number(amount)
  if (!Number.isFinite(value)) return `${currency} ${amount}`
  const hasCents = !Number.isInteger(value)
  const number = new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: hasCents ? 2 : 0,
    maximumFractionDigits: 2,
  }).format(value)
  return `${currency} ${number}`
}

/** Format an ISO date (YYYY-MM-DD) without shifting it across time zones. */
export function formatDate(isoDate: string, options?: Intl.DateTimeFormatOptions): string {
  const [year, month, day] = isoDate.split("-").map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  return new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
    ...options,
  }).format(date)
}

export function formatDuration(days: number): string {
  return days === 1 ? "1 day" : `${days} days`
}
