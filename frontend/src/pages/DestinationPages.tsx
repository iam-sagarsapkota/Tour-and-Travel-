import { Link, useParams } from "react-router-dom"

import { CoverImage } from "@/components/CoverImage"
import { CardGridSkeleton, PageSkeleton } from "@/components/LoadingSkeleton"
import { EmptyState, ErrorState } from "@/components/States"
import { buttonVariants } from "@/components/ui/button"
import { DestinationCard } from "@/features/destinations/DestinationCard"
import { useDestination, useDestinations } from "@/features/destinations/queries"
import { EventCard } from "@/features/events/EventCard"
import { ApiError } from "@/lib/api"

export function DestinationsPage() {
  const { data, isPending, isError, error, refetch } = useDestinations()
  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-3xl font-extrabold text-forest sm:text-4xl">Destinations</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Nepal's trekking regions, each with its own landscape, season and culture.
      </p>
      <div className="mt-8">
        {isPending ? (
          <CardGridSkeleton />
        ) : isError ? (
          <ErrorState message={error.message} onRetry={() => refetch()} />
        ) : data.results.length === 0 ? (
          <EmptyState title="Destinations are being added" description="Please check back soon." />
        ) : (
          <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {data.results.map((destination) => (
              <li key={destination.id}>
                <DestinationCard destination={destination} />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function InfoBlock({ title, text }: { title: string; text: string }) {
  if (!text) return null
  return (
    <section className="border-t pt-8">
      <h2 className="text-xl font-bold text-forest">{title}</h2>
      <p className="mt-3 max-w-prose whitespace-pre-line leading-relaxed">{text}</p>
    </section>
  )
}

export function DestinationDetailPage() {
  const { slug = "" } = useParams()
  const { data: destination, isPending, isError, error, refetch } = useDestination(slug)

  if (isPending) return <PageSkeleton />
  if (isError) {
    const notFound = error instanceof ApiError && error.status === 404
    return (
      <div className="mx-auto max-w-3xl px-4 py-16">
        {notFound ? (
          <EmptyState
            title="We couldn't find that destination"
            action={
              <Link to="/destinations" className={buttonVariants({ className: "h-10 px-4" })}>
                All destinations
              </Link>
            }
          />
        ) : (
          <ErrorState message={error.message} onRetry={() => refetch()} />
        )}
      </div>
    )
  }

  return (
    <article className="mx-auto max-w-6xl space-y-8 px-4 py-10">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-gold-dark">
          {destination.region}
        </p>
        <h1 className="mt-1 text-3xl font-extrabold text-forest sm:text-4xl">{destination.name}</h1>
        {destination.short_description && (
          <p className="mt-2 max-w-2xl text-lg text-muted-foreground">
            {destination.short_description}
          </p>
        )}
        {destination.best_season && (
          <p className="mt-3 inline-block rounded-full bg-accent px-3 py-1 text-sm font-medium text-accent-foreground">
            Best season: {destination.best_season}
          </p>
        )}
      </header>

      <CoverImage
        src={destination.cover_image}
        alt={destination.name}
        className="aspect-[21/9] w-full rounded-2xl"
        eager
      />

      <InfoBlock title="About" text={destination.description} />
      <InfoBlock title="When to go" text={destination.seasonal_guidance} />
      <InfoBlock title="Highlights" text={destination.attractions} />
      <InfoBlock title="Permits and park fees" text={destination.permit_info} />

      <section className="border-t pt-8">
        <h2 className="text-xl font-bold text-forest">Adventures in {destination.name}</h2>
        <div className="mt-4">
          {destination.events.length === 0 ? (
            <EmptyState
              title="No adventures here yet"
              action={
                <Link to="/events" className={buttonVariants({ className: "h-10 px-4" })}>
                  Browse all adventures
                </Link>
              }
            />
          ) : (
            <ul className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {destination.events.map((event) => (
                <li key={event.id}>
                  <EventCard event={event} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </article>
  )
}
