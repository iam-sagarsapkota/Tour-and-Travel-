import { useState } from "react"
import type { ReactNode } from "react"

import { Pagination } from "@/components/Pagination"
import { EmptyState, ErrorState } from "@/components/States"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { ApiError } from "@/lib/api"
import { cn } from "@/lib/utils"

export const PAGE_SIZE = 12

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string
  description?: string
  actions?: ReactNode
}) {
  return (
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="text-2xl font-extrabold text-forest sm:text-3xl">{title}</h1>
        {description && <p className="mt-1 text-muted-foreground">{description}</p>}
      </div>
      {actions}
    </div>
  )
}

/** One left-aligned row of filters above the content they scope. */
export function FilterBar({ children }: { children: ReactNode }) {
  return (
    <div role="group" aria-label="Filters" className="mb-4 flex flex-wrap items-end gap-3">
      {children}
    </div>
  )
}

export function SearchBox({
  value,
  onSearch,
  label,
}: {
  value: string
  onSearch: (value: string) => void
  label: string
}) {
  return (
    <form
      role="search"
      className="flex gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSearch(String(new FormData(event.currentTarget).get("q") ?? "").trim())
      }}
    >
      <label className="sr-only" htmlFor={`search-${label}`}>
        {label}
      </label>
      <Input
        id={`search-${label}`}
        name="q"
        defaultValue={value}
        placeholder={label}
        className="h-10 w-64"
        type="search"
      />
      <Button type="submit" variant="outline" className="h-10 px-4">
        Search
      </Button>
    </form>
  )
}

export function SelectFilter({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  const id = `filter-${label.replace(/\W+/g, "-").toLowerCase()}`
  return (
    <div className="flex flex-col gap-1">
      <label htmlFor={id} className="text-xs font-semibold text-muted-foreground">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 rounded-lg border border-input bg-card px-3 text-sm"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  )
}

const PILL: Record<string, string> = {
  good: "bg-emerald-100 text-emerald-900",
  warn: "bg-amber-100 text-amber-900",
  bad: "bg-red-100 text-red-900",
  info: "bg-sky-100 text-sky-900",
  muted: "bg-muted text-muted-foreground",
}

const TONE: Record<string, keyof typeof PILL> = {
  confirmed: "good",
  successful: "good",
  published: "good",
  open: "good",
  active: "good",
  pending: "warn",
  processing: "warn",
  initiated: "warn",
  draft: "info",
  closed: "info",
  failed: "bad",
  cancelled: "muted",
  expired: "muted",
  archived: "muted",
  completed: "muted",
  inactive: "muted",
  refunded: "info",
  partially_refunded: "info",
}

/** Status shown as text, colour only reinforces it. */
export function StatusPill({ status, label }: { status: string; label?: string }) {
  return (
    <span
      className={cn(
        "inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold",
        PILL[TONE[status] ?? "muted"],
      )}
    >
      {label ?? status.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase())}
    </span>
  )
}

export function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    const first = Object.values(error.fieldErrors)[0]?.[0]
    return first ?? error.message
  }
  return error ? "Something went wrong. Please try again." : ""
}

/**
 * A destructive or important action that needs a second, explicit step.
 * With `requireNote`, the admin must explain the action (it is audited and may be shown
 * to the traveller).
 */
export function ConfirmAction({
  label,
  question,
  confirmLabel,
  onConfirm,
  pending,
  error,
  destructive = false,
  requireNote,
}: {
  label: string
  question: string
  confirmLabel: string
  onConfirm: (note: string) => void
  pending: boolean
  error?: unknown
  destructive?: boolean
  requireNote?: string
}) {
  const [open, setOpen] = useState(false)
  const [note, setNote] = useState("")
  if (!open) {
    return (
      <Button
        variant={destructive ? "outline" : "default"}
        className="h-9 px-3"
        onClick={() => setOpen(true)}
      >
        {label}
      </Button>
    )
  }
  const blocked = Boolean(requireNote) && !note.trim()
  return (
    <div
      role="group"
      aria-label={question}
      className="w-full space-y-2 rounded-xl border bg-card p-3 text-sm sm:w-80"
    >
      <p className="font-semibold">{question}</p>
      {requireNote && (
        <div className="space-y-1">
          <label className="text-xs font-semibold text-muted-foreground" htmlFor={`note-${label}`}>
            {requireNote}
          </label>
          <textarea
            id={`note-${label}`}
            rows={2}
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="w-full rounded-lg border border-input bg-card px-2 py-1"
          />
        </div>
      )}
      {error ? (
        <p role="alert" className="text-destructive">
          {errorText(error)}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={destructive ? "destructive" : "default"}
          className="h-9 px-3"
          disabled={pending || blocked}
          onClick={() => onConfirm(note.trim())}
        >
          {pending ? "Working…" : confirmLabel}
        </Button>
        <Button variant="outline" className="h-9 px-3" onClick={() => setOpen(false)}>
          Cancel
        </Button>
      </div>
    </div>
  )
}

/** Loading / error / empty / table + pagination, the same everywhere in the admin. */
export function ListState<T>({
  query,
  empty,
  page,
  onPage,
  children,
}: {
  query: {
    data?: { count: number; results: T[] }
    isPending: boolean
    isError: boolean
    error: unknown
    refetch: () => unknown
    isPlaceholderData?: boolean
  }
  empty: string
  page: number
  onPage: (page: number) => void
  children: (rows: T[]) => ReactNode
}) {
  if (query.isPending)
    return (
      <p role="status" className="py-10 text-center text-muted-foreground">
        Loading…
      </p>
    )
  if (query.isError)
    return <ErrorState message={errorText(query.error)} onRetry={() => query.refetch()} />
  if (!query.data || query.data.results.length === 0) return <EmptyState title={empty} />
  return (
    <div className={cn("space-y-6", query.isPlaceholderData && "opacity-60 transition-opacity")}>
      <p className="text-sm text-muted-foreground" aria-live="polite">
        {query.data.count} {query.data.count === 1 ? "result" : "results"}
      </p>
      {children(query.data.results)}
      <Pagination
        page={page}
        pageCount={Math.ceil(query.data.count / PAGE_SIZE)}
        onChange={onPage}
      />
    </div>
  )
}

export function Table({
  caption,
  head,
  children,
}: {
  caption: string
  head: string[]
  children: ReactNode
}) {
  return (
    <div className="overflow-x-auto rounded-2xl border bg-card">
      <table className="w-full min-w-[48rem] text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead className="border-b bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
          <tr>
            {head.map((label) => (
              <th key={label} scope="col" className="px-4 py-3 font-semibold">
                {label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y align-top">{children}</tbody>
      </table>
    </div>
  )
}

export function Cell({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={cn("px-4 py-3", className)}>{children}</td>
}

export function formatDateTime(iso: string | null) {
  if (!iso) return "-"
  return new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeStyle: "short" }).format(
    new Date(iso),
  )
}
