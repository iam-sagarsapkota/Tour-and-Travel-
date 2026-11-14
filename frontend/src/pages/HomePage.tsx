import { ArrowRightIcon, MapIcon, ShieldCheckIcon, UsersIcon } from "lucide-react"
import { Link } from "react-router-dom"

import { HeroHeadline } from "@/components/animations/HeroHeadline"
import { Reveal } from "@/components/animations/Reveal"
import { CardGridSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState, ErrorState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { DestinationCard } from "@/features/destinations/DestinationCard"
import { useDestinations } from "@/features/destinations/queries"
import { EventCard } from "@/features/events/EventCard"
import { useFeaturedEvents } from "@/features/events/queries"
import { cn } from "@/lib/utils"

const PROMISES = [
  {
    icon: MapIcon,
    title: "Routes for every pace",
    text: "From a day on the valley rim to two weeks in the high Himalaya, graded by terrain and altitude.",
  },
  {
    icon: UsersIcon,
    title: "Go solo or bring a group",
    text: "Join a scheduled departure on your own, or reserve places for everyone in one booking.",
  },
  {
    icon: ShieldCheckIcon,
    title: "Clear before you commit",
    text: "Itinerary, inclusions, group size and cancellation terms are shown before you pay.",
  },
]

function SectionHeading({
  title,
  to,
  linkLabel,
}: {
  title: string
  to: string
  linkLabel: string
}) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4">
      <h2 className="text-2xl font-bold text-forest sm:text-3xl">{title}</h2>
      <Link
        to={to}
        className="flex shrink-0 items-center gap-1 text-sm font-semibold text-forest hover:underline"
      >
        {linkLabel}
        <ArrowRightIcon className="size-4" aria-hidden="true" />
      </Link>
    </div>
  )
}

function FeaturedEvents() {
  const { data, isPending, isError, refetch } = useFeaturedEvents()
  if (isPending) return <CardGridSkeleton count={3} />
  if (isError) return <ErrorState onRetry={() => refetch()} />
  if (data.results.length === 0) {
    return (
      <EmptyState
        title="Featured treks are on their way"
        description="Browse all adventures in the meantime."
      />
    )
  }
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
      {data.results.map((event) => (
        <EventCard key={event.id} event={event} spotlight />
      ))}
    </div>
  )
}

function PopularDestinations() {
  const { data, isPending, isError, refetch } = useDestinations()
  if (isPending) return <CardGridSkeleton count={3} />
  if (isError) return <ErrorState onRetry={() => refetch()} />
  if (data.results.length === 0) {
    return <EmptyState title="Destinations are being added" />
  }
  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
      {data.results.slice(0, 4).map((destination) => (
        <DestinationCard key={destination.id} destination={destination} />
      ))}
    </div>
  )
}

export default function HomePage() {
  return (
    <>
      <section className="bg-gradient-to-b from-forest to-forest-light text-offwhite">
        <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:py-28">
          <p className="text-sm font-semibold uppercase tracking-widest text-gold">
            Trekking &amp; hiking in Nepal
          </p>
          <HeroHeadline
            text="Discover Nepal. Find your trail."
            className="mt-4 text-4xl font-extrabold leading-tight sm:text-6xl"
          />
          <p className="mx-auto mt-5 max-w-2xl text-lg text-offwhite/85">
            Compare routes by difficulty, length and price, then reserve your place on a scheduled
            departure.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              to="/events"
              className={cn(
                buttonVariants(),
                "h-12 bg-gold px-6 text-base font-bold text-forest hover:bg-gold/90",
              )}
            >
              Browse adventures
            </Link>
            <Link
              to="/destinations"
              className={cn(
                buttonVariants({ variant: "outline" }),
                "h-12 border-white/40 bg-transparent px-6 text-base text-offwhite hover:bg-white/10 hover:text-offwhite",
              )}
            >
              Explore destinations
            </Link>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14">
        <SectionHeading title="Featured adventures" to="/events" linkLabel="See all" />
        <FeaturedEvents />
      </section>

      <section className="bg-secondary/60">
        <div className="mx-auto max-w-6xl px-4 py-14">
          <Reveal>
            <SectionHeading title="Where to go" to="/destinations" linkLabel="All destinations" />
            <PopularDestinations />
          </Reveal>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-14">
        <Reveal className="grid gap-6 md:grid-cols-3">
          {PROMISES.map(({ icon: Icon, title, text }) => (
            <div key={title} className="rounded-2xl border bg-card p-6">
              <Icon className="size-8 text-gold-dark" aria-hidden="true" />
              <h3 className="mt-4 text-lg font-bold text-forest">{title}</h3>
              <p className="mt-2 text-muted-foreground">{text}</p>
            </div>
          ))}
        </Reveal>
      </section>
    </>
  )
}
