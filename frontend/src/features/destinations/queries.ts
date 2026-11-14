import { useQuery } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { Destination, DestinationDetail, Paginated } from "@/types/api"

export function useDestinations() {
  return useQuery({
    queryKey: ["destinations"],
    queryFn: ({ signal }) =>
      api<Paginated<Destination>>("/destinations/", {
        query: { page_size: 100 },
        auth: false,
        signal,
      }),
    staleTime: 10 * 60 * 1000,
  })
}

export function useDestination(slug: string) {
  return useQuery({
    queryKey: ["destination", slug],
    queryFn: ({ signal }) =>
      api<DestinationDetail>(`/destinations/${encodeURIComponent(slug)}/`, {
        auth: false,
        signal,
      }),
  })
}
