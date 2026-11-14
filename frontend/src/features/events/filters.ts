import type { ActivityType, Difficulty } from "@/types/api"

export const DIFFICULTIES: { value: Difficulty; label: string }[] = [
  { value: "easy", label: "Easy" },
  { value: "moderate", label: "Moderate" },
  { value: "difficult", label: "Difficult" },
  { value: "extreme", label: "Extreme" },
]

export const ACTIVITY_TYPES: { value: ActivityType; label: string }[] = [
  { value: "trekking", label: "Trekking" },
  { value: "hiking", label: "Hiking" },
  { value: "other", label: "Other adventure" },
]

export const DURATIONS = [
  { value: "", label: "Any length", min: "", max: "" },
  { value: "1-3", label: "1-3 days", min: "1", max: "3" },
  { value: "4-7", label: "4-7 days", min: "4", max: "7" },
  { value: "8-14", label: "8-14 days", min: "8", max: "14" },
  { value: "15-", label: "15+ days", min: "15", max: "" },
] as const

export const ORDERINGS = [
  { value: "", label: "Recommended" },
  { value: "price", label: "Price: low to high" },
  { value: "-price", label: "Price: high to low" },
  { value: "date", label: "Soonest departure" },
  { value: "-popularity", label: "Most popular" },
  { value: "duration", label: "Shortest first" },
] as const

/** Listing state. It lives in the URL so results can be shared and survive reloads. */
export interface EventFilters {
  search: string
  difficulty: Difficulty[]
  activity_type: string
  destination: string
  category: string
  duration: string
  price_max: string
  departure_from: string
  available: boolean
  ordering: string
  page: number
}

export const EMPTY_FILTERS: EventFilters = {
  search: "",
  difficulty: [],
  activity_type: "",
  destination: "",
  category: "",
  duration: "",
  price_max: "",
  departure_from: "",
  available: false,
  ordering: "",
  page: 1,
}

const DIFFICULTY_VALUES = new Set<string>(DIFFICULTIES.map((item) => item.value))

export function parseFilters(params: URLSearchParams): EventFilters {
  const get = (key: string) => params.get(key) ?? ""
  const page = Number.parseInt(get("page"), 10)
  return {
    search: get("search"),
    difficulty: get("difficulty")
      .split(",")
      .filter((value): value is Difficulty => DIFFICULTY_VALUES.has(value)),
    activity_type: ACTIVITY_TYPES.some((item) => item.value === get("activity_type"))
      ? get("activity_type")
      : "",
    destination: get("destination"),
    category: get("category"),
    duration: DURATIONS.some((item) => item.value === get("duration")) ? get("duration") : "",
    price_max: /^\d+$/.test(get("price_max")) ? get("price_max") : "",
    departure_from: /^\d{4}-\d{2}-\d{2}$/.test(get("departure_from")) ? get("departure_from") : "",
    available: get("available") === "true",
    ordering: ORDERINGS.some((item) => item.value === get("ordering")) ? get("ordering") : "",
    page: Number.isFinite(page) && page > 0 ? page : 1,
  }
}

/** URL form: only non-default values, so a clean listing has a clean URL. */
export function filtersToParams(filters: EventFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.search) params.set("search", filters.search)
  if (filters.difficulty.length) params.set("difficulty", filters.difficulty.join(","))
  if (filters.activity_type) params.set("activity_type", filters.activity_type)
  if (filters.destination) params.set("destination", filters.destination)
  if (filters.category) params.set("category", filters.category)
  if (filters.duration) params.set("duration", filters.duration)
  if (filters.price_max) params.set("price_max", filters.price_max)
  if (filters.departure_from) params.set("departure_from", filters.departure_from)
  if (filters.available) params.set("available", "true")
  if (filters.ordering) params.set("ordering", filters.ordering)
  if (filters.page > 1) params.set("page", String(filters.page))
  return params
}

/** Query sent to GET /events/ (the duration preset becomes a min/max pair). */
export function filtersToQuery(filters: EventFilters): Record<string, string | number | undefined> {
  const duration = DURATIONS.find((item) => item.value === filters.duration)
  return {
    search: filters.search || undefined,
    difficulty: filters.difficulty.join(",") || undefined,
    activity_type: filters.activity_type || undefined,
    destination: filters.destination || undefined,
    category: filters.category || undefined,
    duration_min: duration?.min || undefined,
    duration_max: duration?.max || undefined,
    price_max: filters.price_max || undefined,
    departure_from: filters.departure_from || undefined,
    available: filters.available ? "true" : undefined,
    ordering: filters.ordering || undefined,
    page: filters.page > 1 ? filters.page : undefined,
  }
}

export function activeFilterCount(filters: EventFilters): number {
  return (
    filters.difficulty.length +
    [
      filters.search,
      filters.activity_type,
      filters.destination,
      filters.category,
      filters.duration,
      filters.price_max,
      filters.departure_from,
    ].filter(Boolean).length +
    (filters.available ? 1 : 0)
  )
}
