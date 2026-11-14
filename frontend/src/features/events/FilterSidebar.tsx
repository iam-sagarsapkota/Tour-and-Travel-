import { useId } from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import type { Destination, Difficulty } from "@/types/api"

import { ACTIVITY_TYPES, DIFFICULTIES, DURATIONS, activeFilterCount } from "./filters"
import type { EventFilters } from "./filters"

const SELECT_CLASS =
  "h-10 w-full rounded-lg border border-input bg-card px-3 text-sm text-foreground"

export function FilterSidebar({
  filters,
  destinations,
  onChange,
  onClear,
}: {
  filters: EventFilters
  destinations: Pick<Destination, "slug" | "name">[]
  /** Receives only the fields that changed. */
  onChange: (patch: Partial<EventFilters>) => void
  onClear: () => void
}) {
  const id = useId()
  const active = activeFilterCount(filters)

  function toggleDifficulty(value: Difficulty, checked: boolean) {
    const next = checked
      ? [...filters.difficulty, value]
      : filters.difficulty.filter((item) => item !== value)
    onChange({ difficulty: next })
  }

  return (
    <form
      aria-label="Filter adventures"
      className="space-y-6 rounded-2xl border bg-card p-5"
      onSubmit={(event) => event.preventDefault()}
    >
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-forest">Filters</h2>
        <Button
          type="button"
          variant="ghost"
          className="h-9 px-2 text-sm"
          onClick={onClear}
          disabled={active === 0}
        >
          Clear all{active > 0 ? ` (${active})` : ""}
        </Button>
      </div>

      <fieldset>
        <legend className="text-sm font-semibold">Difficulty</legend>
        <div className="mt-2 space-y-1">
          {DIFFICULTIES.map((item) => (
            <label
              key={item.value}
              className="flex min-h-9 cursor-pointer items-center gap-2 text-sm"
            >
              <input
                type="checkbox"
                className="size-4 accent-forest"
                checked={filters.difficulty.includes(item.value)}
                onChange={(event) => toggleDifficulty(item.value, event.target.checked)}
              />
              {item.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="space-y-1.5">
        <Label htmlFor={`${id}-type`}>Type</Label>
        <select
          id={`${id}-type`}
          className={SELECT_CLASS}
          value={filters.activity_type}
          onChange={(event) => onChange({ activity_type: event.target.value })}
        >
          <option value="">Any type</option>
          {ACTIVITY_TYPES.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`${id}-destination`}>Destination</Label>
        <select
          id={`${id}-destination`}
          className={SELECT_CLASS}
          value={filters.destination}
          onChange={(event) => onChange({ destination: event.target.value })}
        >
          <option value="">All destinations</option>
          {destinations.map((destination) => (
            <option key={destination.slug} value={destination.slug}>
              {destination.name}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`${id}-duration`}>Duration</Label>
        <select
          id={`${id}-duration`}
          className={SELECT_CLASS}
          value={filters.duration}
          onChange={(event) => onChange({ duration: event.target.value })}
        >
          {DURATIONS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`${id}-price`}>Maximum price (NPR)</Label>
        <Input
          id={`${id}-price`}
          className="h-10"
          type="number"
          inputMode="numeric"
          min={0}
          step={1000}
          placeholder="No limit"
          value={filters.price_max}
          onChange={(event) => onChange({ price_max: event.target.value.replace(/\D/g, "") })}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor={`${id}-from`}>Departing on or after</Label>
        <Input
          id={`${id}-from`}
          className="h-10"
          type="date"
          value={filters.departure_from}
          onChange={(event) => onChange({ departure_from: event.target.value })}
        />
      </div>

      <label className="flex min-h-9 cursor-pointer items-center gap-2 text-sm font-medium">
        <input
          type="checkbox"
          className="size-4 accent-forest"
          checked={filters.available}
          onChange={(event) => onChange({ available: event.target.checked })}
        />
        Only show trips with open dates
      </label>
    </form>
  )
}
