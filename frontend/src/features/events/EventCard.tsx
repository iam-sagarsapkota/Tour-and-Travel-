import { CalendarDaysIcon, ClockIcon, MapPinIcon } from "lucide-react"
import { Link } from "react-router-dom"

import SpotlightCard from "@/components/animations/reactbits/SpotlightCard"
import { CoverImage } from "@/components/CoverImage"
import { DifficultyBadge } from "@/components/DifficultyBadge"
import { PriceDisplay } from "@/components/PriceDisplay"
import { formatDate, formatDuration } from "@/lib/format"
import type { EventCard as EventCardData } from "@/types/api"

function availabilityText(event: EventCardData): string {
  const next = event.next_departure
  if (!next) return "No dates open for booking"
  const seats = next.seats_available
  return seats === 1 ? "1 seat left" : `${seats} seats left`
}

function CardBody({ event }: { event: EventCardData }) {
  const next = event.next_departure
  return (
    <>
      <div className="relative">
        <CoverImage
          src={event.cover_image}
          alt={`${event.title}, ${event.destination.name}`}
          className="aspect-[4/3] w-full"
        />
        {event.is_featured && (
          <span className="absolute left-3 top-3 rounded-full bg-gold px-2.5 py-0.5 text-xs font-bold text-forest">
            Featured
          </span>
        )}
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="flex items-center gap-1 text-sm text-muted-foreground">
            <MapPinIcon className="size-4 shrink-0" aria-hidden="true" />
            {event.destination.name}
          </p>
          <DifficultyBadge difficulty={event.difficulty} />
        </div>
        <h3 className="text-lg font-bold leading-snug text-forest">
          {/* The stretched link makes the whole card one target with one accessible name. */}
          <Link
            to={`/events/${event.slug}`}
            className="after:absolute after:inset-0 after:z-10 after:rounded-2xl"
          >
            {event.title}
          </Link>
        </h3>
        <ul className="space-y-1 text-sm text-muted-foreground">
          <li className="flex items-center gap-1.5">
            <ClockIcon className="size-4 shrink-0" aria-hidden="true" />
            {formatDuration(event.duration_days)}
          </li>
          <li className="flex items-center gap-1.5">
            <CalendarDaysIcon className="size-4 shrink-0" aria-hidden="true" />
            {next ? `Next departure ${formatDate(next.start_date)}` : "Dates to be announced"}
          </li>
        </ul>
        <div className="mt-auto flex items-end justify-between gap-2 pt-2">
          <PriceDisplay amount={event.starting_price} currency={event.currency} suffix={null} />
          <p
            className={
              event.has_availability
                ? "text-sm font-medium text-success"
                : "text-sm text-muted-foreground"
            }
          >
            {availabilityText(event)}
          </p>
        </div>
      </div>
    </>
  )
}

const CARD_CLASS =
  "group relative flex h-full flex-col overflow-hidden rounded-2xl border bg-card shadow-sm transition-shadow hover:shadow-md focus-within:shadow-md"

/**
 * Event summary card. `spotlight` wraps it in React Bits "Spotlight Card" and is
 * meant for the short featured row only, not for long listings.
 */
export function EventCard({
  event,
  spotlight = false,
}: {
  event: EventCardData
  spotlight?: boolean
}) {
  if (spotlight) {
    return (
      <SpotlightCard
        theme="light"
        spotlightColor="#E8A34A"
        intensity={0.35}
        className="flex h-full flex-col rounded-2xl! p-0!"
      >
        <article className="relative flex h-full flex-col">
          <CardBody event={event} />
        </article>
      </SpotlightCard>
    )
  }
  return (
    <article className={CARD_CLASS}>
      <CardBody event={event} />
    </article>
  )
}
