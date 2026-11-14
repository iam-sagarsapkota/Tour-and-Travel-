import { SearchIcon, SlidersHorizontalIcon } from "lucide-react"
import { useState } from "react"
import type { FormEvent } from "react"
import { useSearchParams } from "react-router-dom"

import { CardGridSkeleton } from "@/components/LoadingSkeleton"
import { Pagination } from "@/components/Pagination"
import { EmptyState, ErrorState } from "@/components/States"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useDestinations } from "@/features/destinations/queries"
import { EventCard } from "@/features/events/EventCard"
import { FilterSidebar } from "@/features/events/FilterSidebar"
import {
  EMPTY_FILTERS,
  ORDERINGS,
  activeFilterCount,
  filtersToParams,
  parseFilters,
} from "@/features/events/filters"
import type { EventFilters } from "@/features/events/filters"
import { PAGE_SIZE, useEvents } from "@/features/events/queries"
import { cn } from "@/lib/utils"

export default function EventsPage() {
  const [params, setParams] = useSearchParams()
  const filters = parseFilters(params)
  const [showFilters, setShowFilters] = useState(false)

  const events = useEvents(filters)
  const destinations = useDestinations()

  function update(patch: Partial<EventFilters>) {
    // Any filter change returns to page 1 unless the page itself was requested.
    setParams(filtersToParams({ ...filters, page: 1, ...patch }))
  }

  function onSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const value = String(new FormData(event.currentTarget).get("search") ?? "").trim()
    update({ search: value })
  }

  const total = events.data?.count ?? 0
  const pageCount = Math.ceil(total / PAGE_SIZE)
  const active = activeFilterCount(filters)

  return (
    <div className="mx-auto max-w-6xl px-4 py-10">
      <h1 className="text-3xl font-extrabold text-forest sm:text-4xl">Adventures in Nepal</h1>
      <p className="mt-2 max-w-2xl text-muted-foreground">
        Treks and hikes with scheduled departures. Create a free account to see full itineraries and
        book.
      </p>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* key resets the uncontrolled input when the URL search changes (e.g. Clear all). */}
        <form key={filters.search} role="search" onSubmit={onSearch} className="flex flex-1 gap-2">
          <label htmlFor="event-search" className="sr-only">
            Search adventures
          </label>
          <Input
            id="event-search"
            name="search"
            type="search"
            defaultValue={filters.search}
            placeholder="Search by trek or region"
            className="h-11"
          />
          <Button type="submit" className="h-11 px-4">
            <SearchIcon aria-hidden="true" />
            Search
          </Button>
        </form>
        <div className="flex gap-2">
          <Button
            type="button"
            variant="outline"
            className="h-11 flex-1 px-4 lg:hidden"
            aria-expanded={showFilters}
            aria-controls="event-filters"
            onClick={() => setShowFilters((value) => !value)}
          >
            <SlidersHorizontalIcon aria-hidden="true" />
            Filters{active > 0 ? ` (${active})` : ""}
          </Button>
          <label htmlFor="event-ordering" className="sr-only">
            Sort by
          </label>
          <select
            id="event-ordering"
            className="h-11 flex-1 rounded-lg border border-input bg-card px-3 text-sm"
            value={filters.ordering}
            onChange={(event) => update({ ordering: event.target.value })}
          >
            {ORDERINGS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-8 grid gap-8 lg:grid-cols-[17rem_1fr]">
        <aside id="event-filters" className={cn(!showFilters && "hidden", "lg:block")}>
          <FilterSidebar
            filters={filters}
            destinations={destinations.data?.results ?? []}
            onChange={update}
            onClear={() =>
              setParams(filtersToParams({ ...EMPTY_FILTERS, ordering: filters.ordering }))
            }
          />
        </aside>

        <section aria-labelledby="results-heading" aria-busy={events.isFetching}>
          <h2 id="results-heading" className="mb-4 text-sm font-medium text-muted-foreground">
            <span aria-live="polite">
              {events.isPending
                ? "Loading adventures…"
                : events.isError
                  ? "Adventures"
                  : total === 1
                    ? "1 adventure"
                    : `${total} adventures`}
            </span>
          </h2>

          {events.isPending ? (
            <CardGridSkeleton />
          ) : events.isError ? (
            <ErrorState message={events.error.message} onRetry={() => events.refetch()} />
          ) : events.data.results.length === 0 ? (
            <EmptyState
              title="No adventures match these filters"
              description="Try widening the price or dates, or clear the filters to see everything."
              action={
                active > 0 ? (
                  <Button
                    className="h-10 px-4"
                    onClick={() => setParams(filtersToParams(EMPTY_FILTERS))}
                  >
                    Clear filters
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <>
              <ul className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
                {events.data.results.map((event) => (
                  <li key={event.id}>
                    <EventCard event={event} />
                  </li>
                ))}
              </ul>
              <div className="mt-10">
                <Pagination
                  page={filters.page}
                  pageCount={pageCount}
                  onChange={(page) => update({ page })}
                />
              </div>
            </>
          )}
        </section>
      </div>
    </div>
  )
}
