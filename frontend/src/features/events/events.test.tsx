import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import type { EventCard as EventCardData } from "@/types/api"

import { EventCard } from "./EventCard"
import { FilterSidebar } from "./FilterSidebar"
import {
  EMPTY_FILTERS,
  activeFilterCount,
  filtersToParams,
  filtersToQuery,
  parseFilters,
} from "./filters"

const EVENT: EventCardData = {
  id: "e1",
  title: "Ghorepani Poon Hill Trek",
  slug: "poon-hill-trek",
  summary: "Sunrise over Dhaulagiri.",
  destination: { name: "Annapurna Region", slug: "annapurna", region: "Gandaki" },
  category: { name: "Short Treks", slug: "short-treks" },
  activity_type: "trekking",
  cover_image: null,
  difficulty: "easy",
  duration_days: 4,
  starting_price: "38000.00",
  currency: "NPR",
  next_departure: {
    id: "d1",
    start_date: "2027-03-01",
    end_date: "2027-03-04",
    seats_available: 6,
  },
  has_availability: true,
  is_featured: false,
}

function renderCard(event: EventCardData, spotlight = false) {
  return render(
    <MemoryRouter>
      <EventCard event={event} spotlight={spotlight} />
    </MemoryRouter>,
  )
}

describe("EventCard", () => {
  it("shows the summary a guest needs", () => {
    renderCard(EVENT)

    const card = screen.getByRole("article")
    expect(within(card).getByRole("link", { name: "Ghorepani Poon Hill Trek" })).toHaveAttribute(
      "href",
      "/events/poon-hill-trek",
    )
    expect(card).toHaveTextContent("Annapurna Region")
    expect(card).toHaveTextContent("Difficulty: Easy")
    expect(card).toHaveTextContent("4 days")
    expect(card).toHaveTextContent("NPR 38,000")
    expect(card).toHaveTextContent("Next departure 1 Mar 2027")
    expect(card).toHaveTextContent("6 seats left")
    expect(
      within(card).getByRole("img", { name: "Ghorepani Poon Hill Trek, Annapurna Region" }),
    ).toBeInTheDocument()
  })

  it("explains when no dates are open", () => {
    renderCard({ ...EVENT, next_departure: null, has_availability: false })
    const card = screen.getByRole("article")
    expect(card).toHaveTextContent("Dates to be announced")
    expect(card).toHaveTextContent("No dates open for booking")
  })

  it("uses the singular for the last seat and marks featured events", () => {
    renderCard(
      {
        ...EVENT,
        is_featured: true,
        next_departure: { ...EVENT.next_departure!, seats_available: 1 },
      },
      true,
    )
    const card = screen.getByRole("article")
    expect(card).toHaveTextContent("1 seat left")
    expect(card).toHaveTextContent("Featured")
  })
})

describe("FilterSidebar", () => {
  const destinations = [{ slug: "everest", name: "Everest Region" }]

  function setup(filters = EMPTY_FILTERS) {
    const onChange = vi.fn()
    const onClear = vi.fn()
    render(
      <FilterSidebar
        filters={filters}
        destinations={destinations}
        onChange={onChange}
        onClear={onClear}
      />,
    )
    return { onChange, onClear, user: userEvent.setup() }
  }

  it("adds and removes difficulty levels", async () => {
    const { onChange, user } = setup({ ...EMPTY_FILTERS, difficulty: ["easy"] })

    await user.click(screen.getByRole("checkbox", { name: "Moderate" }))
    expect(onChange).toHaveBeenLastCalledWith({ difficulty: ["easy", "moderate"] })

    await user.click(screen.getByRole("checkbox", { name: "Easy" }))
    expect(onChange).toHaveBeenLastCalledWith({ difficulty: [] })
  })

  it("reports select and checkbox changes", async () => {
    const { onChange, user } = setup()

    await user.selectOptions(screen.getByLabelText("Destination"), "everest")
    expect(onChange).toHaveBeenLastCalledWith({ destination: "everest" })

    await user.selectOptions(screen.getByLabelText("Duration"), "4-7")
    expect(onChange).toHaveBeenLastCalledWith({ duration: "4-7" })

    await user.click(screen.getByRole("checkbox", { name: /open dates/i }))
    expect(onChange).toHaveBeenLastCalledWith({ available: true })
  })

  it("disables Clear all until a filter is active", () => {
    setup()
    expect(screen.getByRole("button", { name: "Clear all" })).toBeDisabled()
  })

  it("shows the active count and clears", async () => {
    const { onClear, user } = setup({ ...EMPTY_FILTERS, difficulty: ["easy"], available: true })
    await user.click(screen.getByRole("button", { name: "Clear all (2)" }))
    expect(onClear).toHaveBeenCalledOnce()
  })
})

describe("filters", () => {
  it("round-trips through the URL", () => {
    const params = new URLSearchParams(
      "search=base+camp&difficulty=easy,moderate&destination=everest&duration=8-14" +
        "&price_max=90000&departure_from=2027-03-01&available=true&ordering=-price&page=2",
    )
    const filters = parseFilters(params)

    expect(filters).toMatchObject({
      search: "base camp",
      difficulty: ["easy", "moderate"],
      destination: "everest",
      duration: "8-14",
      price_max: "90000",
      available: true,
      ordering: "-price",
      page: 2,
    })
    expect(filtersToParams(filters).toString()).toBe(params.toString())
  })

  it("drops invalid values instead of sending them to the API", () => {
    const filters = parseFilters(
      new URLSearchParams(
        "difficulty=easy,impossible&ordering=password&page=-3&price_max=abc&duration=99&departure_from=soon",
      ),
    )
    expect(filters).toEqual({ ...EMPTY_FILTERS, difficulty: ["easy"] })
  })

  it("keeps a clean URL for the default listing", () => {
    expect(filtersToParams(EMPTY_FILTERS).toString()).toBe("")
  })

  it("translates the duration preset into a min/max query", () => {
    expect(filtersToQuery({ ...EMPTY_FILTERS, duration: "4-7" })).toMatchObject({
      duration_min: "4",
      duration_max: "7",
    })
    expect(filtersToQuery({ ...EMPTY_FILTERS, duration: "15-" })).toMatchObject({
      duration_min: "15",
      duration_max: undefined,
    })
  })

  it("counts active filters, ignoring sort order and page", () => {
    expect(activeFilterCount({ ...EMPTY_FILTERS, ordering: "price", page: 3 })).toBe(0)
    expect(
      activeFilterCount({ ...EMPTY_FILTERS, difficulty: ["easy", "extreme"], search: "abc" }),
    ).toBe(3)
  })
})
