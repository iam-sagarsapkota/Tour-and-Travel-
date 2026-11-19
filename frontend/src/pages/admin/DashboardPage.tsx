import { AlertTriangleIcon } from "lucide-react"
import { useState } from "react"
import { Link } from "react-router-dom"

import { ErrorState } from "@/components/States"
import { useAdminGet } from "@/features/admin/api"
import { BarList, ColumnChart } from "@/features/admin/charts"
import type { Datum } from "@/features/admin/charts"
import {
  Cell,
  FilterBar,
  PageHeader,
  SelectFilter,
  StatusPill,
  Table,
  errorText,
} from "@/features/admin/ui"
import { formatDate, formatMoney } from "@/lib/format"
import { cn } from "@/lib/utils"
import type { AdminDashboard } from "@/types/api"

const RANGES = [
  { value: "3", label: "Last 3 months" },
  { value: "6", label: "Last 6 months" },
  { value: "12", label: "Last 12 months" },
  { value: "24", label: "Last 24 months" },
]

function percent(value: number | null) {
  return value === null ? "-" : `${Math.round(value * 1000) / 10}%`
}

function monthLabels(month: string) {
  const [year, m] = month.split("-").map(Number)
  const date = new Date(Date.UTC(year, m - 1, 1))
  return {
    label: new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" }).format(date),
    fullLabel: new Intl.DateTimeFormat("en-GB", {
      month: "long",
      year: "numeric",
      timeZone: "UTC",
    }).format(date),
  }
}

function Kpi({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded-2xl border bg-card p-4">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 font-heading text-2xl font-extrabold text-forest">{value}</p>
      {note && <p className="mt-0.5 text-xs text-muted-foreground">{note}</p>}
    </div>
  )
}

function AlertList({
  title,
  empty,
  children,
  count,
}: {
  title: string
  empty: string
  count: number
  children: React.ReactNode
}) {
  return (
    <section className="rounded-2xl border bg-card p-5" aria-label={title}>
      <h2 className="flex items-center gap-2 font-bold text-forest">
        {count > 0 && <AlertTriangleIcon className="size-4 text-warning" aria-hidden="true" />}
        {title}
        <span className="text-sm font-normal text-muted-foreground">({count})</span>
      </h2>
      {count === 0 ? (
        <p className="mt-3 text-sm text-muted-foreground">{empty}</p>
      ) : (
        <ul className="mt-3 divide-y text-sm">{children}</ul>
      )}
    </section>
  )
}

export default function DashboardPage() {
  const [months, setMonths] = useState("12")
  const { data, isPending, isError, error, refetch, isFetching } = useAdminGet<AdminDashboard>(
    `dashboard/?months=${months}`,
  )

  return (
    <div>
      <PageHeader
        title="Dashboard"
        description="Bookings, verified revenue and what needs attention."
      />
      <FilterBar>
        <SelectFilter label="Period" value={months} options={RANGES} onChange={setMonths} />
      </FilterBar>

      {isPending ? (
        <p role="status" className="py-16 text-center text-muted-foreground">
          Loading dashboard…
        </p>
      ) : isError ? (
        <ErrorState message={errorText(error)} onRetry={() => refetch()} />
      ) : (
        <div className={cn("space-y-6", isFetching && "opacity-60 transition-opacity")}>
          <section aria-label="Key figures" className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Kpi
              label="Verified revenue"
              value={formatMoney(data.kpis.verified_revenue, data.kpis.currency)}
              note="Payments confirmed by eSewa/Khalti"
            />
            <Kpi
              label="Bookings"
              value={data.kpis.bookings.toLocaleString()}
              note={`${data.kpis.confirmed_bookings} confirmed`}
            />
            <Kpi
              label="Booking conversion"
              value={percent(data.kpis.booking_conversion)}
              note="Confirmed of decided bookings"
            />
            <Kpi
              label="Payment success rate"
              value={percent(data.kpis.payment_success_rate)}
              note="Successful of settled attempts"
            />
            <Kpi
              label="Upcoming departures"
              value={data.kpis.upcoming_departures.toLocaleString()}
            />
            <Kpi
              label="Published adventures"
              value={data.kpis.published_adventures.toLocaleString()}
            />
            <Kpi
              label="Active users"
              value={data.kpis.active_users.toLocaleString()}
              note="Signed in during the last 30 days"
            />
          </section>

          <div className="grid gap-6 lg:grid-cols-2">
            <ColumnChart
              title="Confirmed bookings per month"
              subtitle="By confirmation date, Nepal time"
              valueLabel="Bookings"
              integer
              emptyText="No confirmed bookings in this period yet."
              data={data.monthly.map<Datum>((row) => ({
                ...monthLabels(row.month),
                value: row.bookings,
                display: row.bookings.toLocaleString(),
              }))}
            />
            <ColumnChart
              title="Verified revenue per month"
              subtitle={`${data.kpis.currency}, by payment date, Nepal time`}
              valueLabel="Revenue"
              emptyText="No verified payments in this period yet."
              data={data.monthly.map<Datum>((row) => ({
                ...monthLabels(row.month),
                value: Number(row.revenue),
                display: formatMoney(row.revenue, data.kpis.currency),
              }))}
            />
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <BarList
              title="Destination popularity"
              subtitle="Travellers on confirmed bookings"
              valueLabel="Travellers"
              data={data.destination_popularity.map((row) => ({
                label: row.name,
                fullLabel: row.name,
                value: row.travellers,
                display: row.travellers.toLocaleString(),
              }))}
            />
            <section className="rounded-2xl border bg-card p-5" aria-labelledby="perf-heading">
              <h2 id="perf-heading" className="font-bold text-forest">
                Top adventures by revenue
              </h2>
              {data.event_performance.length === 0 ? (
                <p className="mt-3 text-sm text-muted-foreground">No confirmed bookings yet.</p>
              ) : (
                <table className="mt-3 w-full text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th scope="col" className="py-1.5">
                        Adventure
                      </th>
                      <th scope="col" className="py-1.5 text-right">
                        Bookings
                      </th>
                      <th scope="col" className="py-1.5 text-right">
                        Travellers
                      </th>
                      <th scope="col" className="py-1.5 text-right">
                        Revenue
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y tabular-nums">
                    {data.event_performance.map((row) => (
                      <tr key={row.slug}>
                        <td className="py-1.5">{row.title}</td>
                        <td className="py-1.5 text-right">{row.bookings}</td>
                        <td className="py-1.5 text-right">{row.travellers}</td>
                        <td className="py-1.5 text-right font-medium">
                          {formatMoney(row.revenue, "NPR")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <AlertList
              title="Payments needing attention"
              empty="Nothing to review."
              count={data.payments_needing_attention.length}
            >
              {data.payments_needing_attention.map((p) => (
                <li key={p.id} className="flex items-center justify-between gap-2 py-2">
                  <Link
                    to={`/admin/payments?attention=true&search=${p.reference}`}
                    className="font-semibold text-forest hover:underline"
                  >
                    {p.reference}
                  </Link>
                  <span>{formatMoney(p.amount, p.currency)}</span>
                </li>
              ))}
            </AlertList>
            <AlertList
              title="Below minimum after cutoff"
              empty="Every closed departure met its minimum."
              count={data.departures_needing_decision.length}
            >
              {data.departures_needing_decision.map((d) => (
                <li key={d.id} className="py-2">
                  <Link
                    to="/admin/departures?decision=true"
                    className="font-semibold text-forest hover:underline"
                  >
                    {d.adventure}
                  </Link>
                  <p className="text-muted-foreground">
                    {formatDate(d.start_date)} · {d.seats_reserved} of minimum {d.minimum}
                  </p>
                </li>
              ))}
            </AlertList>
            <AlertList
              title="Nearly full (80%+)"
              empty="No departure is close to capacity."
              count={data.capacity_alerts.length}
            >
              {data.capacity_alerts.map((d) => (
                <li key={d.id} className="py-2">
                  <p className="font-semibold">{d.adventure}</p>
                  <p className="text-muted-foreground">
                    {formatDate(d.start_date)} · {d.seats_reserved}/{d.capacity} seats
                  </p>
                </li>
              ))}
            </AlertList>
          </div>

          <section aria-labelledby="recent-heading">
            <h2 id="recent-heading" className="mb-3 font-bold text-forest">
              Recent bookings
            </h2>
            <Table
              caption="Recent bookings"
              head={["Reference", "Traveller", "Adventure", "Total", "Status", "Created"]}
            >
              {data.recent_bookings.map((b) => (
                <tr key={b.id}>
                  <Cell>
                    <Link
                      to={`/admin/bookings?search=${b.reference}`}
                      className="font-semibold text-forest hover:underline"
                    >
                      {b.reference}
                    </Link>
                  </Cell>
                  <Cell>{b.traveller}</Cell>
                  <Cell>{b.adventure}</Cell>
                  <Cell className="tabular-nums">{formatMoney(b.total_amount, b.currency)}</Cell>
                  <Cell>
                    <StatusPill status={b.status} />
                  </Cell>
                  <Cell>
                    {new Intl.DateTimeFormat("en-GB", { dateStyle: "medium" }).format(
                      new Date(b.created_at),
                    )}
                  </Cell>
                </tr>
              ))}
            </Table>
          </section>
        </div>
      )}
    </div>
  )
}
