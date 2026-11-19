import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { Paginated } from "@/types/api"

type Query = Record<string, string | number | boolean | undefined>

/** Paginated admin list. Keeps the previous page on screen while the next loads. */
export function useAdminList<T>(resource: string, query: Query) {
  return useQuery({
    queryKey: ["admin", resource, query],
    queryFn: ({ signal }) => api<Paginated<T>>(`/admin/${resource}/`, { query, signal }),
    placeholderData: keepPreviousData,
  })
}

export function useAdminGet<T>(path: string, enabled = true) {
  return useQuery({
    queryKey: ["admin", path],
    queryFn: ({ signal }) => api<T>(`/admin/${path}`, { signal }),
    enabled,
  })
}

/** Any admin write. Refreshes every admin query afterwards so lists and dashboard agree. */
export function useAdminAction<TInput = unknown, TResult = unknown>(
  run: (input: TInput) => Promise<TResult>,
) {
  const client = useQueryClient()
  return useMutation({
    mutationFn: run,
    onSuccess: () => client.invalidateQueries({ queryKey: ["admin"] }),
  })
}

export const adminApi = {
  post: <T>(path: string, body?: unknown) =>
    api<T>(`/admin/${path}`, { method: "POST", body: body ?? {} }),
  patch: <T>(path: string, body: unknown) => api<T>(`/admin/${path}`, { method: "PATCH", body }),
  remove: (path: string) => api<void>(`/admin/${path}`, { method: "DELETE" }),
}
