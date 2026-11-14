import { keepPreviousData, useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { Category, EventCard, EventDetail, Paginated } from "@/types/api"

import { filtersToQuery } from "./filters"
import type { EventFilters } from "./filters"

export const PAGE_SIZE = 12

export function useEvents(filters: EventFilters) {
  const query = filtersToQuery(filters)
  return useQuery({
    queryKey: ["events", query],
    queryFn: ({ signal }) => api<Paginated<EventCard>>("/events/", { query, auth: false, signal }),
    placeholderData: keepPreviousData,
  })
}

export function useFeaturedEvents() {
  return useQuery({
    queryKey: ["events", "featured"],
    queryFn: ({ signal }) =>
      api<Paginated<EventCard>>("/events/", {
        query: { featured: "true", page_size: 3 },
        auth: false,
        signal,
      }),
  })
}

export function useEvent(slug: string) {
  return useQuery({
    queryKey: ["event", slug],
    queryFn: ({ signal }) => api<EventDetail>(`/events/${encodeURIComponent(slug)}/`, { signal }),
  })
}

export function useCategories() {
  return useQuery({
    queryKey: ["categories"],
    queryFn: ({ signal }) => api<Category[]>("/categories/", { auth: false, signal }),
    staleTime: 10 * 60 * 1000,
  })
}
