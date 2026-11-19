import { useId, useState } from "react"

/**
 * Single-series charts for the admin dashboard, following the dataviz rules:
 * one brand hue (forest green), bars <= 24px with 4px rounded data-ends and a
 * square baseline, hairline solid gridlines, text in text colours (never the
 * series colour), a per-bar hover/focus tooltip, and a table view so no value
 * depends on hovering. One series means no legend: the title names it.
 */

const SERIES = "var(--forest)"
const GRID = "var(--border)"

export interface Datum {
  label: string // axis label, e.g. "Nov"
  fullLabel: string // tooltip / table label, e.g. "November 2026"
  value: number
  display: string // formatted value, e.g. "NPR 1,20,000"
}

function niceMax(max: number, integer: boolean): number {
  // Counts get whole-number ticks: at least 0..4 so each step is >= 1.
  if (integer) return Math.max(4, Math.ceil(niceMax(max, false) / 4) * 4)
  if (max <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(max))
  for (const step of [1, 2, 2.5, 5, 10]) {
    if (step * magnitude >= max) return step * magnitude
  }
  return 10 * magnitude
}

function compact(value: number): string {
  if (value >= 1e7) return `${+(value / 1e6).toFixed(1)}M`
  if (value >= 1e4) return `${+(value / 1e3).toFixed(1)}K`
  return value.toLocaleString("en-US")
}

/** Rounded top, square bottom (data-end vs baseline). */
function columnPath(x: number, y: number, width: number, height: number) {
  const r = Math.min(4, width / 2, height)
  if (height <= 0) return ""
  return `M${x},${y + height} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height} Z`
}

function TableView({
  title,
  data,
  valueLabel,
}: {
  title: string
  data: Datum[]
  valueLabel: string
}) {
  return (
    <table className="w-full text-left text-sm">
      <caption className="sr-only">{title}</caption>
      <thead className="text-xs uppercase tracking-wide text-muted-foreground">
        <tr>
          <th scope="col" className="py-1.5">
            Period
          </th>
          <th scope="col" className="py-1.5 text-right">
            {valueLabel}
          </th>
        </tr>
      </thead>
      <tbody className="divide-y tabular-nums">
        {data.map((d) => (
          <tr key={d.fullLabel}>
            <td className="py-1.5">{d.fullLabel}</td>
            <td className="py-1.5 text-right font-medium">{d.display}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function ChartCard({
  title,
  subtitle,
  data,
  valueLabel,
  children,
}: {
  title: string
  subtitle?: string
  data: Datum[]
  valueLabel: string
  children: React.ReactNode
}) {
  const [asTable, setAsTable] = useState(false)
  return (
    <figure className="rounded-2xl border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <figcaption>
          <p className="font-bold text-forest">{title}</p>
          {subtitle && <p className="text-sm text-muted-foreground">{subtitle}</p>}
        </figcaption>
        <button
          type="button"
          className="min-h-9 shrink-0 rounded-lg px-2 text-sm font-medium text-forest underline-offset-2 hover:underline"
          aria-pressed={asTable}
          onClick={() => setAsTable((value) => !value)}
        >
          {asTable ? "Show chart" : "Show table"}
        </button>
      </div>
      <div className="mt-4">
        {asTable ? <TableView title={title} data={data} valueLabel={valueLabel} /> : children}
      </div>
    </figure>
  )
}

/** Vertical columns over time (e.g. bookings per month). */
export function ColumnChart({
  title,
  subtitle,
  data,
  valueLabel,
  integer = false,
  emptyText = "Nothing in this period yet.",
}: {
  title: string
  subtitle?: string
  data: Datum[]
  valueLabel: string
  /** Whole-number data (counts): no fractional axis ticks. */
  integer?: boolean
  emptyText?: string
}) {
  const [active, setActive] = useState<number | null>(null)
  const id = useId()
  const width = 640
  const height = 220
  const pad = { top: 12, right: 8, bottom: 26, left: 48 }
  const plotW = width - pad.left - pad.right
  const plotH = height - pad.top - pad.bottom
  const max = niceMax(Math.max(0, ...data.map((d) => d.value)), integer)
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * max)
  const band = plotW / Math.max(1, data.length)
  const barW = Math.min(24, band * 0.6)
  const hovered = active === null ? null : data[active]

  if (data.every((d) => d.value === 0)) {
    return (
      <ChartCard title={title} subtitle={subtitle} data={data} valueLabel={valueLabel}>
        <p className="py-16 text-center text-sm text-muted-foreground">{emptyText}</p>
      </ChartCard>
    )
  }

  return (
    <ChartCard title={title} subtitle={subtitle} data={data} valueLabel={valueLabel}>
      <div className="relative">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="h-auto w-full"
          role="img"
          aria-labelledby={`${id}-desc`}
        >
          <desc id={`${id}-desc`}>
            {title}: {data.map((d) => `${d.fullLabel} ${d.display}`).join(", ")}
          </desc>
          {ticks.map((tick) => {
            const y = pad.top + plotH - (tick / max) * plotH
            return (
              <g key={tick}>
                <line
                  x1={pad.left}
                  x2={width - pad.right}
                  y1={y}
                  y2={y}
                  stroke={GRID}
                  strokeWidth={1}
                />
                <text
                  x={pad.left - 8}
                  y={y + 4}
                  textAnchor="end"
                  className="fill-muted-foreground text-[11px] tabular-nums"
                >
                  {compact(tick)}
                </text>
              </g>
            )
          })}
          {data.map((d, i) => {
            const h = (d.value / max) * plotH
            const x = pad.left + band * i + (band - barW) / 2
            const y = pad.top + plotH - h
            return (
              <g key={d.fullLabel}>
                <path
                  d={columnPath(x, y, barW, h)}
                  fill={SERIES}
                  opacity={active === null || active === i ? 1 : 0.55}
                />
                {/* Hit target: the whole band, taller and wider than the mark. */}
                <rect
                  x={pad.left + band * i}
                  y={pad.top}
                  width={band}
                  height={plotH}
                  fill="transparent"
                  tabIndex={0}
                  role="img"
                  aria-label={`${d.fullLabel}: ${d.display}`}
                  onPointerEnter={() => setActive(i)}
                  onPointerLeave={() => setActive(null)}
                  onFocus={() => setActive(i)}
                  onBlur={() => setActive(null)}
                  className="cursor-default outline-none focus-visible:stroke-[var(--ring)] focus-visible:stroke-2"
                />
                <text
                  x={pad.left + band * i + band / 2}
                  y={height - 8}
                  textAnchor="middle"
                  className="fill-muted-foreground text-[11px]"
                >
                  {d.label}
                </text>
              </g>
            )
          })}
        </svg>
        {hovered && active !== null && (
          <div
            role="status"
            className="pointer-events-none absolute -translate-x-1/2 rounded-lg border bg-card px-3 py-2 text-xs shadow-md"
            style={{ left: `${((pad.left + band * active + band / 2) / width) * 100}%`, top: 0 }}
          >
            <p className="text-sm font-bold text-foreground">{hovered.display}</p>
            <p className="text-muted-foreground">{hovered.fullLabel}</p>
          </div>
        )}
      </div>
    </ChartCard>
  )
}

/** Horizontal bars for ranked categories (e.g. travellers per destination). */
export function BarList({
  title,
  subtitle,
  data,
  valueLabel,
}: {
  title: string
  subtitle?: string
  data: Datum[]
  valueLabel: string
}) {
  const max = Math.max(1, ...data.map((d) => d.value))
  return (
    <ChartCard title={title} subtitle={subtitle} data={data} valueLabel={valueLabel}>
      {data.length === 0 ? (
        <p className="py-6 text-center text-sm text-muted-foreground">No confirmed bookings yet.</p>
      ) : (
        <ul className="space-y-3">
          {data.map((d) => (
            <li
              key={d.fullLabel}
              className="grid grid-cols-[minmax(6rem,10rem)_1fr_auto] items-center gap-3 text-sm"
            >
              <span className="truncate text-foreground" title={d.fullLabel}>
                {d.label}
              </span>
              <span className="h-4" aria-hidden="true">
                <span
                  className="block h-4 rounded-r-[4px]"
                  style={{ width: `${Math.max(2, (d.value / max) * 100)}%`, background: SERIES }}
                />
              </span>
              <span className="text-right font-semibold tabular-nums">{d.display}</span>
            </li>
          ))}
        </ul>
      )}
    </ChartCard>
  )
}
