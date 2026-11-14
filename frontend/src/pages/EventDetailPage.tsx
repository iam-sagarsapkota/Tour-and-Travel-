import { CheckIcon, MapPinIcon, XIcon } from "lucide-react"
import type { ReactNode } from "react"
import { Link, useParams } from "react-router-dom"

import { CoverImage } from "@/components/CoverImage"
import { DifficultyBadge } from "@/components/DifficultyBadge"
import { PageSkeleton } from "@/components/LoadingSkeleton"
import { PriceDisplay } from "@/components/PriceDisplay"
import { EmptyState, ErrorState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { EventCard } from "@/features/events/EventCard"
import { useEvent } from "@/features/events/queries"
import { ApiError } from "@/lib/api"
import { formatDate, formatDuration, formatMoney } from "@/lib/format"
import type { Departure, EventDetail } from "@/types/api"

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-t pt-8">
      <h2 className="text-xl font-bold text-forest">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function Prose({ text }: { text: string }) {
  return <p className="max-w-prose whitespace-pre-line leading-relaxed">{text}</p>
}

function Facts({ event }: { event: EventDetail }) {
  const facts: [string, string | null][] = [
    ["Duration", formatDuration(event.duration_days)],
    ["Distance", event.distance_km ? `${Number(event.distance_km)} km` : null],
    ["Highest point", event.max_elevation_m ? `${event.max_elevation_m.toLocaleString()} m` : null],
    ["Starts", event.start_point || null],
    ["Ends", event.end_point || null],
    [
      "Group size",
      event.max_group_size
        ? `${event.min_participants}-${event.max_group_size} people`
        : `From ${event.min_participants}`,
    ],
    ["Solo travellers", event.solo_friendly ? "Welcome" : "Groups only"],
    ["Organiser", event.organizer || null],
  ]
  return (
    <dl className="grid grid-cols-2 gap-4 rounded-2xl border bg-card p-5 sm:grid-cols-4">
      {facts
        .filter(([, value]) => value)
        .map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {label}
            </dt>
            <dd className="mt-0.5 font-semibold text-slate">{value}</dd>
          </div>
        ))}
    </dl>
  )
}

function ItemList({ items, included }: { items: string[]; included: boolean }) {
  const Icon = included ? CheckIcon : XIcon
  return (
    <ul className="space-y-2">
      {items.map((item) => (
        <li key={item} className="flex gap-2">
          <Icon
            className={
              included
                ? "mt-0.5 size-5 shrink-0 text-success"
                : "mt-0.5 size-5 shrink-0 text-muted-foreground"
            }
            aria-hidden="true"
          />
          {item}
        </li>
      ))}
    </ul>
  )
}

function DepartureRow({ departure, currency }: { departure: Departure; currency: string }) {
  const seats = departure.seats_available
  const status = departure.is_bookable
    ? seats === 1
      ? "1 seat left"
      : `${seats} seats left`
    : seats === 0
      ? "Sold out"
      : "Booking closed"
  return (
    <li className="flex flex-col gap-2 rounded-xl border bg-card p-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <p className="font-semibold text-slate">
          {formatDate(departure.start_date)} - {formatDate(departure.end_date)}
        </p>
        <p className="text-sm text-muted-foreground">
          Minimum {departure.min_participants} to run · up to {departure.capacity} trekkers
        </p>
      </div>
      <div className="sm:text-right">
        <p className="font-heading font-bold text-forest">
          {formatMoney(departure.price, currency)}{" "}
          <span className="text-sm font-normal text-muted-foreground">per person</span>
        </p>
        <p
          className={
            departure.is_bookable
              ? "text-sm font-medium text-success"
              : "text-sm text-muted-foreground"
          }
        >
          {status}
        </p>
      </div>
    </li>
  )
}

const TEXT_SECTIONS: [string, keyof EventDetail][] = [
  ["Accommodation", "accommodation"],
  ["Meals", "meals"],
  ["Transport", "transportation"],
  ["Equipment", "equipment"],
  ["Safety", "safety_guidance"],
  ["Meeting point", "meeting_point"],
]

export default function EventDetailPage() {
  const { slug = "" } = useParams()
  const { data: event, isPending, isError, error, refetch } = useEvent(slug)

  if (isPending) return <PageSkeleton />
  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        {notFound ? (
          <EmptyState
            title="This adventure isn't available"
            description="It may have been removed or is not open yet."
            action={
              <Link to="/events" className={buttonVariants({ className: "h-10 px-4" })}>
                Browse adventures
              </Link>
            }
          />
        ) : (
          <ErrorState message={error.message} onRetry={() => refetch()} />
        )}
      </div>
    )
  }

  const details = TEXT_SECTIONS.filter(([, key]) => event[key])

  return (
    <article className="mx-auto max-w-6xl space-y-8 px-4 py-10">
      <header>
        <p className="flex items-center gap-1 text-sm text-muted-foreground">
          <MapPinIcon className="size-4" aria-hidden="true" />
          <Link to={`/destinations/${event.destination.slug}`} className="hover:underline">
            {event.destination.name}
          </Link>
          <span aria-hidden="true">·</span>
          {event.destination.region}
        </p>
        <h1 className="mt-2 text-3xl font-extrabold text-forest sm:text-4xl">{event.title}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-3">
          <DifficultyBadge difficulty={event.difficulty} />
          {event.category && (
            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold text-forest">
              {event.category.name}
            </span>
          )}
          <PriceDisplay amount={event.starting_price} currency={event.currency} />
        </div>
      </header>

      <CoverImage
        src={event.cover_image}
        alt={`${event.title}, ${event.destination.name}`}
        className="aspect-[21/9] w-full rounded-2xl"
        eager
      />

      <Facts event={event} />

      {(event.description || event.summary) && (
        <Section title="Overview">
          <Prose text={event.description || event.summary} />
        </Section>
      )}

      {event.images.length > 0 && (
        <Section title="Gallery">
          <ul className="grid grid-cols-2 gap-3 md:grid-cols-3">
            {event.images.map((image) => (
              <li key={image.id}>
                <CoverImage
                  src={image.image}
                  alt={image.alt_text || `${event.title} photo`}
                  className="aspect-[4/3] w-full rounded-xl"
                />
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title="Departures">
        {event.departures.length === 0 ? (
          <p className="text-muted-foreground">No departures are scheduled yet.</p>
        ) : (
          <>
            <ul className="space-y-3">
              {event.departures.map((departure) => (
                <DepartureRow key={departure.id} departure={departure} currency={event.currency} />
              ))}
            </ul>
            <p className="mt-4 rounded-lg bg-accent px-4 py-3 text-sm text-accent-foreground">
              Online booking is not open yet. It arrives with the next release.
            </p>
          </>
        )}
      </Section>

      {event.itinerary.length > 0 && (
        <Section title="Itinerary">
          <ol className="space-y-4">
            {event.itinerary.map((day) => (
              <li key={day.day_number} className="flex gap-4">
                <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-forest font-heading text-sm font-bold text-offwhite">
                  <span className="sr-only">Day </span>
                  {day.day_number}
                </span>
                <div>
                  <h3 className="font-semibold text-slate">{day.title}</h3>
                  {day.description && (
                    <p className="mt-1 text-muted-foreground">{day.description}</p>
                  )}
                  {(day.overnight_location || day.altitude_m) && (
                    <p className="mt-1 text-sm text-muted-foreground">
                      {[
                        day.overnight_location && `Overnight: ${day.overnight_location}`,
                        day.altitude_m && `${day.altitude_m.toLocaleString()} m`,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ol>
        </Section>
      )}

      {event.route_summary && (
        <Section title="Route">
          <Prose text={event.route_summary} />
          {event.route_map_url && (
            <a
              href={event.route_map_url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-3 inline-block font-medium text-forest underline"
            >
              Open route map (new tab)
            </a>
          )}
        </Section>
      )}

      {(event.inclusions.length > 0 || event.exclusions.length > 0) && (
        <Section title="What's included">
          <div className="grid gap-8 md:grid-cols-2">
            {event.inclusions.length > 0 && (
              <div>
                <h3 className="mb-3 font-semibold">Included</h3>
                <ItemList items={event.inclusions} included />
              </div>
            )}
            {event.exclusions.length > 0 && (
              <div>
                <h3 className="mb-3 font-semibold">Not included</h3>
                <ItemList items={event.exclusions} included={false} />
              </div>
            )}
          </div>
        </Section>
      )}

      {details.length > 0 && (
        <Section title="Good to know">
          <dl className="grid gap-6 md:grid-cols-2">
            {details.map(([label, key]) => (
              <div key={key}>
                <dt className="font-semibold">{label}</dt>
                <dd className="mt-1 whitespace-pre-line text-muted-foreground">
                  {String(event[key])}
                </dd>
              </div>
            ))}
          </dl>
        </Section>
      )}

      {event.cancellation_policy && (
        <Section title="Cancellation policy">
          <Prose text={event.cancellation_policy} />
        </Section>
      )}

      {event.related.length > 0 && (
        <Section title="Related adventures">
          <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {event.related.map((related) => (
              <li key={related.id}>
                <EventCard event={related} />
              </li>
            ))}
          </ul>
        </Section>
      )}
    </article>
  )
}
