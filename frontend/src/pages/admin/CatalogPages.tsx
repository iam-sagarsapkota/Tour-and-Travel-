import { useState } from "react"
import type { FormEvent } from "react"
import { Link, useNavigate, useParams } from "react-router-dom"
import { toast } from "sonner"

import { Field, FormError } from "@/components/forms"
import type { Errors } from "@/components/forms"
import { ErrorState } from "@/components/States"
import { Button, buttonVariants } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { adminApi, useAdminAction, useAdminGet, useAdminList } from "@/features/admin/api"
import {
  Cell,
  ConfirmAction,
  FilterBar,
  ListState,
  PAGE_SIZE,
  PageHeader,
  SearchBox,
  SelectFilter,
  StatusPill,
  Table,
  errorText,
} from "@/features/admin/ui"
import { DIFFICULTIES, ACTIVITY_TYPES } from "@/features/events/filters"
import { ApiError } from "@/lib/api"
import { formatDate, formatMoney } from "@/lib/format"
import type { AdminAdventure, AdminDeparture, Paginated } from "@/types/api"

import { useFilters } from "./OperationsPages"

const SELECT = "h-11 w-full rounded-lg border border-input bg-card px-3 text-sm"

function fieldErrors(error: unknown): Errors {
  if (!(error instanceof ApiError)) return error ? { form: "Something went wrong." } : {}
  const errors: Errors = {}
  for (const [name, messages] of Object.entries(error.fieldErrors)) errors[name] = messages[0]
  errors.form =
    errors.non_field_errors ??
    errors.detail ??
    (Object.keys(errors).length ? undefined : error.message)
  return errors
}

function SelectField({
  label,
  name,
  defaultValue,
  options,
  error,
}: {
  label: string
  name: string
  defaultValue?: string
  options: { value: string; label: string }[]
  error?: string
}) {
  const id = `field-${name}`
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <select
        id={id}
        name={name}
        defaultValue={defaultValue}
        className={SELECT}
        aria-invalid={error ? true : undefined}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

function TextArea({
  label,
  name,
  defaultValue,
  hint,
  error,
  rows = 3,
}: {
  label: string
  name: string
  defaultValue?: string
  hint?: string
  error?: string
  rows?: number
}) {
  const id = `field-${name}`
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <textarea
        id={id}
        name={name}
        rows={rows}
        defaultValue={defaultValue}
        aria-invalid={error ? true : undefined}
        className="w-full rounded-lg border border-input bg-card px-3 py-2 text-sm"
      />
      {hint && !error && <p className="text-sm text-muted-foreground">{hint}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}

function useOptions(resource: "destinations" | "categories") {
  return useAdminGet<Paginated<{ id: string; name: string; status?: string }>>(
    `${resource}/?page_size=100`,
  )
}

// --- Adventures --------------------------------------------------------------------

function AdventureActions({ adventure }: { adventure: AdminAdventure }) {
  const act = useAdminAction((action: string) =>
    adminApi.post(`adventures/${adventure.id}/${action}/`),
  )
  return (
    <div className="flex flex-wrap gap-2">
      <Link
        to={`/admin/adventures/${adventure.id}`}
        className={buttonVariants({ variant: "outline", className: "h-9 px-3" })}
      >
        Edit
      </Link>
      {adventure.status !== "published" && (
        <Button className="h-9 px-3" disabled={act.isPending} onClick={() => act.mutate("publish")}>
          Publish
        </Button>
      )}
      {adventure.status === "published" && (
        <Button
          variant="outline"
          className="h-9 px-3"
          disabled={act.isPending}
          onClick={() => act.mutate("unpublish")}
        >
          Unpublish
        </Button>
      )}
      {adventure.status !== "archived" && (
        <ConfirmAction
          label="Archive"
          question="Archive this adventure? It disappears from the public site."
          confirmLabel="Archive"
          destructive
          pending={act.isPending}
          onConfirm={() => act.mutate("archive")}
        />
      )}
      {act.isError && (
        <p role="alert" className="w-full text-xs text-destructive">
          {errorText(act.error)}
        </p>
      )}
    </div>
  )
}

export function AdventuresPage() {
  const f = useFilters()
  const query = useAdminList<AdminAdventure>("adventures", {
    search: f.get("search") || undefined,
    status: f.get("status") || undefined,
    page: f.page,
    page_size: PAGE_SIZE,
  })
  return (
    <div>
      <PageHeader
        title="Adventures"
        description="Draft, publish and archive treks. Archived adventures stay linked to their bookings."
        actions={
          <Link to="/admin/adventures/new" className={buttonVariants({ className: "h-10 px-4" })}>
            New adventure
          </Link>
        }
      />
      <FilterBar>
        <SearchBox
          label="Title or destination"
          value={f.get("search")}
          onSearch={(v) => f.set("search", v)}
        />
        <SelectFilter
          label="Status"
          value={f.get("status")}
          onChange={(v) => f.set("status", v)}
          options={[
            { value: "", label: "All" },
            { value: "draft", label: "Draft" },
            { value: "published", label: "Published" },
            { value: "archived", label: "Archived" },
          ]}
        />
      </FilterBar>
      <ListState query={query} empty="No adventures match." page={f.page} onPage={f.setPage}>
        {(rows) => (
          <Table
            caption="Adventures"
            head={["Adventure", "Difficulty", "Length", "Base price", "Status", "Actions"]}
          >
            {rows.map((a) => (
              <tr key={a.id}>
                <Cell>
                  <span className="font-semibold">{a.title}</span>
                  {a.is_featured && <p className="text-xs text-gold-dark">Featured</p>}
                </Cell>
                <Cell className="capitalize">{a.difficulty}</Cell>
                <Cell>{a.duration_days} days</Cell>
                <Cell className="tabular-nums">{formatMoney(a.base_price, a.currency)}</Cell>
                <Cell>
                  <StatusPill status={a.status} />
                </Cell>
                <Cell>
                  <AdventureActions adventure={a} />
                </Cell>
              </tr>
            ))}
          </Table>
        )}
      </ListState>
    </div>
  )
}

const lines = (value: string) =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)

export function AdventureFormPage() {
  const { id } = useParams()
  const isNew = !id || id === "new"
  const navigate = useNavigate()
  const existing = useAdminGet<AdminAdventure>(`adventures/${id}/`, !isNew)
  const destinations = useOptions("destinations")
  const categories = useOptions("categories")
  const [errors, setErrors] = useState<Errors>({})
  const save = useAdminAction((body: Record<string, unknown>) =>
    isNew
      ? adminApi.post<AdminAdventure>("adventures/", body)
      : adminApi.patch<AdminAdventure>(`adventures/${id}/`, body),
  )

  if ((!isNew && existing.isPending) || destinations.isPending || categories.isPending) {
    return (
      <p role="status" className="py-16 text-center text-muted-foreground">
        Loading…
      </p>
    )
  }
  const loadError = existing.error ?? destinations.error ?? categories.error
  if (loadError) return <ErrorState message={errorText(loadError)} />
  const a = existing.data

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const value = (name: string) => String(data.get(name) ?? "").trim()
    const body = {
      title: value("title"),
      destination: value("destination"),
      category: value("category") || null,
      activity_type: value("activity_type"),
      difficulty: value("difficulty"),
      duration_days: Number(value("duration_days")),
      base_price: value("base_price"),
      min_participants: Number(value("min_participants") || 1),
      max_group_size: value("max_group_size") ? Number(value("max_group_size")) : null,
      solo_friendly: data.get("solo_friendly") === "on",
      is_featured: data.get("is_featured") === "on",
      summary: value("summary"),
      description: value("description"),
      meeting_point: value("meeting_point"),
      cancellation_policy: value("cancellation_policy"),
      inclusions: lines(value("inclusions")),
      exclusions: lines(value("exclusions")),
    } as Record<string, unknown>
    // Only send the itinerary when it was edited: this form edits titles only, and
    // re-sending unchanged days would erase their descriptions.
    const days = lines(value("itinerary"))
    const original = a?.itinerary.map((day) => day.title) ?? []
    if (isNew || days.join("\n") !== original.join("\n")) {
      body.itinerary = days.map((title, index) => ({ day_number: index + 1, title }))
    }
    const local: Errors = {}
    if (!body.title) local.title = "Enter a title."
    if (!((body.duration_days as number) >= 1)) local.duration_days = "At least 1 day."
    if (!(Number(body.base_price) > 0)) local.base_price = "Enter a price above zero."
    setErrors(local)
    if (Object.keys(local).length) return
    try {
      const saved = await save.mutateAsync(body)
      toast.success(isNew ? "Adventure created as a draft" : "Adventure saved")
      navigate(isNew ? `/admin/adventures/${saved.id}` : "/admin/adventures")
    } catch (error) {
      setErrors(fieldErrors(error))
    }
  }

  return (
    <div className="max-w-4xl">
      <PageHeader
        title={isNew ? "New adventure" : `Edit: ${a?.title}`}
        description={
          isNew
            ? "Saved as a draft. Publish it from the list when it's ready."
            : `Status: ${a?.status}`
        }
      />
      <form onSubmit={submit} noValidate className="space-y-6 rounded-2xl border bg-card p-6">
        <FormError message={errors.form} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Title" name="title" defaultValue={a?.title} error={errors.title} />
          <SelectField
            label="Destination"
            name="destination"
            defaultValue={a?.destination}
            error={errors.destination}
            options={destinations.data!.results.map((d) => ({
              value: d.id,
              label: `${d.name}${d.status && d.status !== "published" ? ` (${d.status})` : ""}`,
            }))}
          />
          <SelectField
            label="Category"
            name="category"
            defaultValue={a?.category ?? ""}
            options={[
              { value: "", label: "None" },
              ...categories.data!.results.map((c) => ({ value: c.id, label: c.name })),
            ]}
          />
          <SelectField
            label="Type"
            name="activity_type"
            defaultValue={a?.activity_type ?? "trekking"}
            options={ACTIVITY_TYPES}
          />
          <SelectField
            label="Difficulty"
            name="difficulty"
            defaultValue={a?.difficulty ?? "moderate"}
            error={errors.difficulty}
            options={DIFFICULTIES}
          />
          <Field
            label="Duration (days)"
            name="duration_days"
            type="number"
            min={1}
            defaultValue={a?.duration_days ?? 1}
            error={errors.duration_days}
          />
          <Field
            label="Base price per person (NPR)"
            name="base_price"
            inputMode="decimal"
            defaultValue={a?.base_price}
            error={errors.base_price}
          />
          <Field
            label="Minimum participants"
            name="min_participants"
            type="number"
            min={1}
            defaultValue={a?.min_participants ?? 1}
            error={errors.min_participants}
          />
          <Field
            label="Maximum group size (optional)"
            name="max_group_size"
            type="number"
            min={1}
            defaultValue={a?.max_group_size ?? ""}
            error={errors.max_group_size}
          />
          <Field label="Meeting point" name="meeting_point" defaultValue={a?.meeting_point} />
        </div>
        <div className="flex flex-wrap gap-6 text-sm">
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="checkbox"
              name="solo_friendly"
              defaultChecked={a?.solo_friendly ?? true}
              className="size-5 accent-forest"
            />
            Solo travellers can book
          </label>
          <label className="flex min-h-11 items-center gap-2">
            <input
              type="checkbox"
              name="is_featured"
              defaultChecked={a?.is_featured ?? false}
              className="size-5 accent-forest"
            />
            Feature on the homepage
          </label>
        </div>
        <TextArea
          label="Summary (shown on cards)"
          name="summary"
          defaultValue={a?.summary}
          rows={2}
          error={errors.summary}
        />
        <TextArea label="Description" name="description" defaultValue={a?.description} rows={5} />
        <div className="grid gap-4 sm:grid-cols-2">
          <TextArea
            label="Included"
            name="inclusions"
            defaultValue={a?.inclusions.join("\n")}
            hint="One item per line."
            error={errors.inclusions}
          />
          <TextArea
            label="Not included"
            name="exclusions"
            defaultValue={a?.exclusions.join("\n")}
            hint="One item per line."
            error={errors.exclusions}
          />
        </div>
        <TextArea
          label="Itinerary"
          name="itinerary"
          rows={6}
          defaultValue={a?.itinerary.map((day) => day.title).join("\n")}
          hint="One day per line, in order. Editing this list replaces the days (and their details)."
          error={errors.itinerary}
        />
        <TextArea
          label="Cancellation policy"
          name="cancellation_policy"
          defaultValue={a?.cancellation_policy}
          rows={3}
        />
        <div className="flex gap-3">
          <Button type="submit" className="h-11 px-6" disabled={save.isPending}>
            {save.isPending ? "Saving…" : isNew ? "Create draft" : "Save changes"}
          </Button>
          <Link
            to="/admin/adventures"
            className={buttonVariants({ variant: "outline", className: "h-11 px-6" })}
          >
            Cancel
          </Link>
        </div>
      </form>
      <p className="mt-4 text-sm text-muted-foreground">
        Photos, destinations and categories are managed in{" "}
        <a className="text-forest underline" href="/django-admin/" target="_blank" rel="noreferrer">
          Django admin
        </a>{" "}
        for now.
      </p>
    </div>
  )
}

// --- Departures --------------------------------------------------------------------

function DepartureRow({ departure }: { departure: AdminDeparture }) {
  const update = useAdminAction((status: string) =>
    adminApi.patch(`departures/${departure.id}/`, { status }),
  )
  return (
    <tr>
      <Cell>
        <span className="font-semibold">{departure.adventure_title}</span>
        <p className="text-muted-foreground">
          {formatDate(departure.start_date)} - {formatDate(departure.end_date)}
        </p>
      </Cell>
      <Cell className="tabular-nums">
        {departure.seats_reserved} / {departure.capacity}
        <p className="text-xs text-muted-foreground">
          {departure.min_participants
            ? `minimum ${departure.min_participants}`
            : "adventure minimum"}
        </p>
      </Cell>
      <Cell className="tabular-nums">{formatMoney(departure.price, "NPR")}</Cell>
      <Cell>
        <StatusPill status={departure.status} />
        {departure.needs_decision && (
          <p className="mt-1 text-xs font-semibold text-warning">
            Below minimum: decide to run, move or cancel
          </p>
        )}
      </Cell>
      <Cell className="space-y-2">
        <div className="flex flex-wrap gap-2">
          {departure.status === "open" && (
            <Button
              variant="outline"
              className="h-9 px-3"
              disabled={update.isPending}
              onClick={() => update.mutate("closed")}
            >
              Close bookings
            </Button>
          )}
          {departure.status === "closed" && (
            <Button
              variant="outline"
              className="h-9 px-3"
              disabled={update.isPending}
              onClick={() => update.mutate("open")}
            >
              Reopen
            </Button>
          )}
          {departure.status !== "cancelled" && departure.status !== "completed" && (
            <ConfirmAction
              label="Cancel departure"
              question="Cancel this departure? Booked travellers are emailed; refunds are handled separately."
              confirmLabel="Cancel departure"
              destructive
              pending={update.isPending}
              onConfirm={() => update.mutate("cancelled")}
            />
          )}
        </div>
        {update.isError && (
          <p role="alert" className="text-xs text-destructive">
            {errorText(update.error)}
          </p>
        )}
      </Cell>
    </tr>
  )
}

function NewDepartureForm({ onDone }: { onDone: () => void }) {
  const adventures = useAdminList<AdminAdventure>("adventures", {
    page_size: 100,
    status: "published",
  })
  const [errors, setErrors] = useState<Errors>({})
  const create = useAdminAction((body: Record<string, unknown>) =>
    adminApi.post("departures/", body),
  )

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const value = (name: string) => String(data.get(name) ?? "").trim()
    const body: Record<string, unknown> = {
      adventure: value("adventure"),
      start_date: value("start_date"),
      capacity: Number(value("capacity")),
    }
    if (value("min_participants")) body.min_participants = Number(value("min_participants"))
    if (value("price_override")) body.price_override = value("price_override")
    const local: Errors = {}
    if (!body.adventure) local.adventure = "Choose an adventure."
    if (!body.start_date) local.start_date = "Choose a start date."
    if (!((body.capacity as number) >= 1)) local.capacity = "At least 1 seat."
    setErrors(local)
    if (Object.keys(local).length) return
    try {
      await create.mutateAsync(body)
      toast.success("Departure scheduled")
      onDone()
    } catch (error) {
      setErrors(fieldErrors(error))
    }
  }

  return (
    <form onSubmit={submit} noValidate className="mb-6 space-y-4 rounded-2xl border bg-card p-5">
      <h2 className="font-bold text-forest">Schedule a departure</h2>
      <FormError message={errors.form} />
      <div className="grid gap-4 sm:grid-cols-3">
        <SelectField
          label="Adventure (published)"
          name="adventure"
          error={errors.adventure}
          options={[
            { value: "", label: "Choose…" },
            ...(adventures.data?.results ?? []).map((a) => ({ value: a.id, label: a.title })),
          ]}
        />
        <Field
          label="Start date"
          name="start_date"
          type="date"
          error={errors.start_date}
          hint="End date follows the adventure length."
        />
        <Field
          label="Capacity"
          name="capacity"
          type="number"
          min={1}
          defaultValue={12}
          error={errors.capacity}
        />
        <Field
          label="Minimum to run (optional)"
          name="min_participants"
          type="number"
          min={1}
          error={errors.min_participants}
        />
        <Field
          label="Price per person (optional)"
          name="price_override"
          inputMode="decimal"
          hint="Empty uses the base price."
          error={errors.price_override}
        />
      </div>
      <p className="text-sm text-muted-foreground">
        Bookings close 3 days before the start (Nepal time) unless changed in Django admin.
      </p>
      <div className="flex gap-3">
        <Button type="submit" className="h-10 px-5" disabled={create.isPending}>
          {create.isPending ? "Scheduling…" : "Schedule"}
        </Button>
        <Button type="button" variant="outline" className="h-10 px-5" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  )
}

export function DeparturesPage() {
  const f = useFilters()
  const [adding, setAdding] = useState(false)
  const today = new Date().toISOString().slice(0, 10)
  const query = useAdminList<AdminDeparture>("departures", {
    status: f.get("status") || undefined,
    needs_decision: f.get("decision") || undefined,
    start_date__gte: f.get("past") === "true" ? undefined : today,
    ordering: "start_date",
    page: f.page,
    page_size: PAGE_SIZE,
  })
  return (
    <div>
      <PageHeader
        title="Departures"
        description="Scheduled dates, capacity and status. Changing dates or cancelling emails booked travellers."
        actions={
          !adding && (
            <Button className="h-10 px-4" onClick={() => setAdding(true)}>
              Schedule departure
            </Button>
          )
        }
      />
      {adding && <NewDepartureForm onDone={() => setAdding(false)} />}
      <FilterBar>
        <SelectFilter
          label="Status"
          value={f.get("status")}
          onChange={(v) => f.set("status", v)}
          options={[
            { value: "", label: "All" },
            { value: "open", label: "Open" },
            { value: "closed", label: "Closed" },
            { value: "cancelled", label: "Cancelled" },
          ]}
        />
        <SelectFilter
          label="Minimum"
          value={f.get("decision")}
          onChange={(v) => f.set("decision", v)}
          options={[
            { value: "", label: "Any" },
            { value: "true", label: "Needs a decision" },
          ]}
        />
        <SelectFilter
          label="Dates"
          value={f.get("past")}
          onChange={(v) => f.set("past", v)}
          options={[
            { value: "", label: "Upcoming" },
            { value: "true", label: "Include past" },
          ]}
        />
      </FilterBar>
      <ListState query={query} empty="No departures match." page={f.page} onPage={f.setPage}>
        {(rows) => (
          <Table caption="Departures" head={["Departure", "Seats", "Price", "Status", "Actions"]}>
            {rows.map((d) => (
              <DepartureRow key={d.id} departure={d} />
            ))}
          </Table>
        )}
      </ListState>
    </div>
  )
}

// --- Settings ----------------------------------------------------------------------

export function SettingsPage() {
  const settings = useAdminGet<{
    site_name: string
    support_email: string
    support_phone: string
    announcement: string
    announcement_active: boolean
  }>("site-settings/")
  const [errors, setErrors] = useState<Errors>({})
  const save = useAdminAction((body: Record<string, unknown>) =>
    adminApi.patch("site-settings/", body),
  )

  if (settings.isPending)
    return (
      <p role="status" className="py-16 text-center text-muted-foreground">
        Loading…
      </p>
    )
  if (settings.isError)
    return <ErrorState message={errorText(settings.error)} onRetry={() => settings.refetch()} />
  const s = settings.data

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const data = new FormData(event.currentTarget)
    const value = (name: string) => String(data.get(name) ?? "").trim()
    try {
      await save.mutateAsync({
        site_name: value("site_name"),
        support_email: value("support_email"),
        support_phone: value("support_phone"),
        announcement: value("announcement"),
        announcement_active: data.get("announcement_active") === "on",
      })
      setErrors({})
      toast.success("Settings saved")
    } catch (error) {
      setErrors(fieldErrors(error))
    }
  }

  return (
    <div className="max-w-2xl">
      <PageHeader
        title="Settings"
        description="Site-wide contact details and the announcement banner."
      />
      <form onSubmit={submit} noValidate className="space-y-4 rounded-2xl border bg-card p-6">
        <FormError message={errors.form} />
        <Field
          label="Site name"
          name="site_name"
          defaultValue={s.site_name}
          error={errors.site_name}
        />
        <Field
          label="Support email (shown in emails and on Contact)"
          name="support_email"
          type="email"
          defaultValue={s.support_email}
          error={errors.support_email}
        />
        <Field
          label="Support phone"
          name="support_phone"
          type="tel"
          defaultValue={s.support_phone}
          error={errors.support_phone}
        />
        <TextArea
          label="Announcement"
          name="announcement"
          defaultValue={s.announcement}
          rows={2}
          hint="Short notice shown above the navigation, e.g. monsoon trail closures."
          error={errors.announcement}
        />
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input
            type="checkbox"
            name="announcement_active"
            defaultChecked={s.announcement_active}
            className="size-5 accent-forest"
          />
          Show the announcement
        </label>
        <Button type="submit" className="h-11 px-6" disabled={save.isPending}>
          {save.isPending ? "Saving…" : "Save settings"}
        </Button>
      </form>
    </div>
  )
}
