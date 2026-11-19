import { useState } from "react"
import { useSearchParams } from "react-router-dom"

import { Button } from "@/components/ui/button"
import { adminApi, useAdminAction, useAdminList } from "@/features/admin/api"
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
  formatDateTime,
} from "@/features/admin/ui"
import { formatDate, formatMoney } from "@/lib/format"
import type { AdminBooking, AdminPayment, AdminUser, AuditEntry, ContactInquiry } from "@/types/api"

/** Filters and page number kept in the URL, so views can be linked and reloaded. */
export function useFilters(defaults: Record<string, string> = {}) {
  const [params, setParams] = useSearchParams()
  const get = (key: string) => params.get(key) ?? defaults[key] ?? ""
  const page = Math.max(1, Number(params.get("page") ?? 1) || 1)
  function set(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    if (key !== "page") next.delete("page")
    setParams(next)
  }
  return { get, set, page, setPage: (p: number) => set("page", p > 1 ? String(p) : "") }
}

// --- Bookings --------------------------------------------------------------------

function BookingRow({ booking }: { booking: AdminBooking }) {
  const [open, setOpen] = useState(false)
  const cancel = useAdminAction((reason: string) =>
    adminApi.post(`bookings/${booking.id}/cancel/`, { reason }),
  )
  const canCancel = booking.status === "pending" || booking.status === "confirmed"
  return (
    <>
      <tr>
        <Cell>
          <button
            type="button"
            className="font-semibold text-forest hover:underline"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {booking.reference}
          </button>
        </Cell>
        <Cell>
          {booking.user.full_name}
          <p className="text-muted-foreground">{booking.user.email ?? booking.user.phone}</p>
        </Cell>
        <Cell>
          {booking.adventure.title}
          <p className="text-muted-foreground">{formatDate(booking.departure.start_date)}</p>
        </Cell>
        <Cell className="tabular-nums">
          {booking.participant_count} × {formatMoney(booking.unit_price, booking.currency)}
          <p className="font-semibold">{formatMoney(booking.total_amount, booking.currency)}</p>
        </Cell>
        <Cell>
          <StatusPill status={booking.status} />
          {booking.payment && (
            <p className="mt-1 text-xs text-muted-foreground">Payment: {booking.payment.status}</p>
          )}
        </Cell>
        <Cell>
          {canCancel && (
            <ConfirmAction
              label="Cancel"
              question={`Cancel ${booking.reference}?`}
              confirmLabel="Cancel booking"
              requireNote="Reason (sent to the traveller)"
              destructive
              pending={cancel.isPending}
              error={cancel.error}
              onConfirm={(note) => cancel.mutate(note)}
            />
          )}
        </Cell>
      </tr>
      {open && (
        <tr className="bg-secondary/30">
          <td colSpan={6} className="px-4 py-3">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <p className="font-semibold">Travellers</p>
                <ul className="mt-1 text-sm">
                  {booking.participants.map((p, i) => (
                    <li key={i}>
                      {p.full_name}
                      {p.nationality && ` · ${p.nationality}`}
                      {p.is_lead && " · lead"}
                    </li>
                  ))}
                </ul>
                {booking.cancellation_reason && (
                  <p className="mt-2 text-sm">Cancellation reason: {booking.cancellation_reason}</p>
                )}
              </div>
              <div>
                <p className="font-semibold">History</p>
                <ol className="mt-1 space-y-1 text-sm">
                  {booking.history.map((h, i) => (
                    <li key={i}>
                      {formatDateTime(h.created_at)}: {h.from_status || "new"} → {h.to_status}
                      {h.actor ? ` by ${h.actor}` : " (automatic)"}
                      {h.note && ` - ${h.note}`}
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  )
}

export function BookingsPage() {
  const f = useFilters()
  const query = useAdminList<AdminBooking>("bookings", {
    search: f.get("search") || undefined,
    status: f.get("status") || undefined,
    page: f.page,
    page_size: PAGE_SIZE,
  })
  return (
    <div>
      <PageHeader
        title="Bookings"
        description="Totals and history are read-only. Cancelling releases seats and emails the traveller."
      />
      <FilterBar>
        <SearchBox
          label="Reference, name, email or phone"
          value={f.get("search")}
          onSearch={(v) => f.set("search", v)}
        />
        <SelectFilter
          label="Status"
          value={f.get("status")}
          onChange={(v) => f.set("status", v)}
          options={[
            { value: "", label: "All" },
            { value: "pending", label: "Pending payment" },
            { value: "confirmed", label: "Confirmed" },
            { value: "cancelled", label: "Cancelled" },
            { value: "expired", label: "Expired" },
          ]}
        />
      </FilterBar>
      <ListState query={query} empty="No bookings match." page={f.page} onPage={f.setPage}>
        {(rows) => (
          <Table
            caption="Bookings"
            head={["Reference", "Traveller", "Trip", "Price", "Status", "Actions"]}
          >
            {rows.map((b) => (
              <BookingRow key={b.id} booking={b} />
            ))}
          </Table>
        )}
      </ListState>
    </div>
  )
}

// --- Payments --------------------------------------------------------------------

function PaymentRow({ payment }: { payment: AdminPayment }) {
  const [open, setOpen] = useState(false)
  const reconcile = useAdminAction(() => adminApi.post(`payments/${payment.id}/reconcile/`))
  const resolve = useAdminAction((note: string) =>
    adminApi.post(`payments/${payment.id}/resolve/`, { note }),
  )
  return (
    <>
      <tr>
        <Cell>
          <button
            type="button"
            className="font-semibold text-forest hover:underline"
            aria-expanded={open}
            onClick={() => setOpen((v) => !v)}
          >
            {payment.booking_reference}
          </button>
          <p className="text-muted-foreground">{payment.adventure}</p>
        </Cell>
        <Cell>
          {payment.traveller}
          <p className="text-muted-foreground">{payment.traveller_contact}</p>
        </Cell>
        <Cell className="tabular-nums font-semibold">
          {formatMoney(payment.amount, payment.currency)}
        </Cell>
        <Cell>
          <StatusPill status={payment.status} />
          <p className="mt-1 text-xs capitalize text-muted-foreground">
            {payment.provider || payment.attempts[0]?.provider}
            {payment.gateway_reference && ` · ${payment.gateway_reference}`}
          </p>
        </Cell>
        <Cell>
          {payment.needs_attention ? (
            <p className="max-w-xs whitespace-pre-line text-sm text-destructive">
              {payment.attention_reason}
            </p>
          ) : (
            <span className="text-muted-foreground">-</span>
          )}
        </Cell>
        <Cell className="space-y-2">
          <Button
            variant="outline"
            className="h-9 px-3"
            disabled={reconcile.isPending}
            onClick={() => reconcile.mutate(undefined)}
          >
            {reconcile.isPending ? "Checking…" : "Re-check with provider"}
          </Button>
          {payment.needs_attention && (
            <ConfirmAction
              label="Resolve"
              question="Mark this as resolved?"
              confirmLabel="Resolve"
              requireNote="What did you do? (e.g. refunded in eSewa portal)"
              pending={resolve.isPending}
              error={resolve.error}
              onConfirm={(note) => resolve.mutate(note)}
            />
          )}
        </Cell>
      </tr>
      {open && (
        <tr className="bg-secondary/30">
          <td colSpan={6} className="px-4 py-3">
            <p className="font-semibold">Attempts</p>
            <ul className="mt-1 space-y-1 text-sm">
              {payment.attempts.map((a) => (
                <li key={a.id}>
                  {a.reference} · {a.provider} · {formatMoney(a.amount, a.currency)} · {a.status}
                  {a.gateway_status && ` (${a.gateway_status})`} · {formatDateTime(a.created_at)}
                </li>
              ))}
            </ul>
            <p className="mt-3 font-semibold">Provider log</p>
            <ol className="mt-1 space-y-1 text-sm">
              {payment.logs.map((log, i) => (
                <li key={i}>
                  {formatDateTime(log.created_at)} · {log.attempt} · {log.kind}: {log.message}
                </li>
              ))}
            </ol>
          </td>
        </tr>
      )}
    </>
  )
}

export function PaymentsPage() {
  const f = useFilters()
  const query = useAdminList<AdminPayment>("payments", {
    search: f.get("search") || undefined,
    status: f.get("status") || undefined,
    needs_attention: f.get("attention") || undefined,
    page: f.page,
    page_size: PAGE_SIZE,
  })
  return (
    <div>
      <PageHeader
        title="Payments"
        description="Verified with eSewa/Khalti server to server. Amounts and history cannot be edited."
      />
      <FilterBar>
        <SearchBox
          label="Booking or payment reference"
          value={f.get("search")}
          onSearch={(v) => f.set("search", v)}
        />
        <SelectFilter
          label="Status"
          value={f.get("status")}
          onChange={(v) => f.set("status", v)}
          options={[
            { value: "", label: "All" },
            { value: "pending", label: "Pending" },
            { value: "processing", label: "Processing" },
            { value: "successful", label: "Successful" },
            { value: "failed", label: "Failed" },
            { value: "cancelled", label: "Cancelled" },
            { value: "refunded", label: "Refunded" },
          ]}
        />
        <SelectFilter
          label="Needs attention"
          value={f.get("attention")}
          onChange={(v) => f.set("attention", v)}
          options={[
            { value: "", label: "Any" },
            { value: "true", label: "Needs attention" },
          ]}
        />
      </FilterBar>
      <ListState query={query} empty="No payments match." page={f.page} onPage={f.setPage}>
        {(rows) => (
          <Table
            caption="Payments"
            head={["Booking", "Traveller", "Amount", "Status", "Attention", "Actions"]}
          >
            {rows.map((p) => (
              <PaymentRow key={p.id} payment={p} />
            ))}
          </Table>
        )}
      </ListState>
    </div>
  )
}

// --- Users -----------------------------------------------------------------------

function UserRow({ user }: { user: AdminUser }) {
  const deactivate = useAdminAction(() => adminApi.remove(`users/${user.id}/`))
  const reactivate = useAdminAction(() => adminApi.patch(`users/${user.id}/`, { is_active: true }))
  return (
    <tr>
      <Cell>
        <span className="font-semibold">{user.full_name}</span>
        <p className="text-muted-foreground">{user.email ?? user.phone}</p>
      </Cell>
      <Cell>
        <StatusPill status={user.role} label={user.role.replace("_", " ")} />
      </Cell>
      <Cell>
        <StatusPill status={user.is_active ? "active" : "inactive"} />
      </Cell>
      <Cell>{user.email ? (user.email_verified ? "Verified" : "Not verified") : "-"}</Cell>
      <Cell>{formatDateTime(user.last_login)}</Cell>
      <Cell>
        {user.is_active ? (
          <ConfirmAction
            label="Deactivate"
            question={`Deactivate ${user.full_name}? They will be signed out everywhere.`}
            confirmLabel="Deactivate"
            destructive
            pending={deactivate.isPending}
            error={deactivate.error}
            onConfirm={() => deactivate.mutate(undefined)}
          />
        ) : (
          <Button
            variant="outline"
            className="h-9 px-3"
            disabled={reactivate.isPending}
            onClick={() => reactivate.mutate(undefined)}
          >
            Reactivate
          </Button>
        )}
        {(deactivate.isError || reactivate.isError) && !deactivate.isPending && (
          <p role="alert" className="mt-1 text-xs text-destructive">
            Only a super admin can change admin accounts.
          </p>
        )}
      </Cell>
    </tr>
  )
}

export function UsersPage() {
  const f = useFilters()
  const query = useAdminList<AdminUser>("users", {
    search: f.get("search") || undefined,
    role: f.get("role") || undefined,
    is_active: f.get("active") || undefined,
    page: f.page,
    page_size: PAGE_SIZE,
  })
  return (
    <div>
      <PageHeader
        title="Users"
        description="Passwords are never shown. Accounts are deactivated, not deleted."
      />
      <FilterBar>
        <SearchBox
          label="Name, email or phone"
          value={f.get("search")}
          onSearch={(v) => f.set("search", v)}
        />
        <SelectFilter
          label="Role"
          value={f.get("role")}
          onChange={(v) => f.set("role", v)}
          options={[
            { value: "", label: "All" },
            { value: "user", label: "Travellers" },
            { value: "admin", label: "Admins" },
            { value: "super_admin", label: "Super admins" },
          ]}
        />
        <SelectFilter
          label="Status"
          value={f.get("active")}
          onChange={(v) => f.set("active", v)}
          options={[
            { value: "", label: "All" },
            { value: "true", label: "Active" },
            { value: "false", label: "Deactivated" },
          ]}
        />
      </FilterBar>
      <ListState query={query} empty="No users match." page={f.page} onPage={f.setPage}>
        {(rows) => (
          <Table
            caption="Users"
            head={["User", "Role", "Status", "Email", "Last login", "Actions"]}
          >
            {rows.map((u) => (
              <UserRow key={u.id} user={u} />
            ))}
          </Table>
        )}
      </ListState>
    </div>
  )
}

// --- Inbox -----------------------------------------------------------------------

function InquiryRow({ inquiry }: { inquiry: ContactInquiry }) {
  const handle = useAdminAction(() => adminApi.post(`contact-inquiries/${inquiry.id}/handle/`))
  return (
    <tr>
      <Cell>
        <span className="font-semibold">{inquiry.subject}</span>
        <p className="mt-1 max-w-xl whitespace-pre-line text-muted-foreground">{inquiry.message}</p>
      </Cell>
      <Cell>
        {inquiry.name}
        <p>
          <a className="text-forest underline" href={`mailto:${inquiry.email}`}>
            {inquiry.email}
          </a>
        </p>
        {inquiry.phone && <p className="text-muted-foreground">{inquiry.phone}</p>}
      </Cell>
      <Cell>{formatDateTime(inquiry.created_at)}</Cell>
      <Cell>
        {inquiry.handled ? (
          <span className="text-muted-foreground">Handled by {inquiry.handled_by}</span>
        ) : (
          <Button
            className="h-9 px-3"
            disabled={handle.isPending}
            onClick={() => handle.mutate(undefined)}
          >
            Mark handled
          </Button>
        )}
      </Cell>
    </tr>
  )
}

export function InboxPage() {
  const f = useFilters({ handled: "false" })
  const query = useAdminList<ContactInquiry>("contact-inquiries", {
    handled: f.get("handled") === "all" ? undefined : f.get("handled") || undefined,
    page: f.page,
    page_size: PAGE_SIZE,
  })
  return (
    <div>
      <PageHeader title="Inbox" description="Messages from the contact form." />
      <FilterBar>
        <SelectFilter
          label="Show"
          value={f.get("handled")}
          onChange={(v) => f.set("handled", v || "all")}
          options={[
            { value: "false", label: "Open" },
            { value: "true", label: "Handled" },
            { value: "all", label: "All" },
          ]}
        />
      </FilterBar>
      <ListState query={query} empty="No messages." page={f.page} onPage={f.setPage}>
        {(rows) => (
          <Table caption="Contact messages" head={["Message", "From", "Received", "Status"]}>
            {rows.map((i) => (
              <InquiryRow key={i.id} inquiry={i} />
            ))}
          </Table>
        )}
      </ListState>
    </div>
  )
}

// --- Audit log -------------------------------------------------------------------

export function AuditPage() {
  const f = useFilters()
  const query = useAdminList<AuditEntry>("audit-logs", {
    search: f.get("search") || undefined,
    action: f.get("action") || undefined,
    page: f.page,
    page_size: PAGE_SIZE,
  })
  return (
    <div>
      <PageHeader
        title="Audit log"
        description="Every admin change to catalog, users, bookings and payments. Read-only."
      />
      <FilterBar>
        <SearchBox
          label="Search records"
          value={f.get("search")}
          onSearch={(v) => f.set("search", v)}
        />
        <SelectFilter
          label="Action"
          value={f.get("action")}
          onChange={(v) => f.set("action", v)}
          options={[
            "",
            "create",
            "update",
            "publish",
            "unpublish",
            "archive",
            "cancel",
            "deactivate",
            "reconcile",
            "resolve",
            "handle",
            "delete",
          ].map((v) => ({
            value: v,
            label: v ? v[0].toUpperCase() + v.slice(1) : "All",
          }))}
        />
      </FilterBar>
      <ListState query={query} empty="No entries." page={f.page} onPage={f.setPage}>
        {(rows) => (
          <Table caption="Audit log" head={["When", "Who", "Action", "Record", "Changes"]}>
            {rows.map((entry) => (
              <tr key={entry.id}>
                <Cell>{formatDateTime(entry.created_at)}</Cell>
                <Cell>
                  {entry.actor ?? "System"}
                  {entry.ip_address && (
                    <p className="text-xs text-muted-foreground">{entry.ip_address}</p>
                  )}
                </Cell>
                <Cell>
                  <StatusPill status="info" label={entry.action} />
                </Cell>
                <Cell>
                  {entry.object_repr}
                  <p className="text-xs text-muted-foreground">{entry.object_type}</p>
                </Cell>
                <Cell>
                  <ul className="space-y-0.5 text-xs">
                    {Object.entries(entry.changes).map(([field, [before, after]]) => (
                      <li key={field}>
                        <span className="font-semibold">{field}</span>: {String(before ?? "-")} →{" "}
                        {String(after ?? "-")}
                      </li>
                    ))}
                    {entry.note && <li>Note: {entry.note}</li>}
                  </ul>
                </Cell>
              </tr>
            ))}
          </Table>
        )}
      </ListState>
    </div>
  )
}
