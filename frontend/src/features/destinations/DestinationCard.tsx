import { Link } from "react-router-dom"

import { CoverImage } from "@/components/CoverImage"
import type { Destination } from "@/types/api"

export function DestinationCard({ destination }: { destination: Destination }) {
  const count = destination.event_count
  return (
    <article className="group relative overflow-hidden rounded-2xl border bg-card shadow-sm transition-shadow hover:shadow-md focus-within:shadow-md">
      <CoverImage
        src={destination.cover_image}
        alt={destination.name}
        className="aspect-[16/10] w-full"
      />
      <div className="space-y-1.5 p-4">
        <p className="text-xs font-semibold uppercase tracking-wide text-gold-dark">
          {destination.region}
        </p>
        <h3 className="text-lg font-bold text-forest">
          <Link
            to={`/destinations/${destination.slug}`}
            className="after:absolute after:inset-0 after:rounded-2xl"
          >
            {destination.name}
          </Link>
        </h3>
        {destination.short_description && (
          <p className="text-sm text-muted-foreground">{destination.short_description}</p>
        )}
        <p className="pt-1 text-sm font-medium text-slate">
          {count === 1 ? "1 adventure" : `${count} adventures`}
        </p>
      </div>
    </article>
  )
}
