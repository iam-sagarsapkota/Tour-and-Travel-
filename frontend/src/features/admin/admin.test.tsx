import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { StaticAuthProvider } from "@/features/auth/AuthContext"
import type { AdminAdventure, AdminBooking, Paginated, User } from "@/types/api"

import { ColumnChart } from "./charts"
import { RequireAdmin } from "./RequireAdmin"
import { ConfirmAction } from "./ui"

const apiMock = vi.hoisted(() => vi.fn())
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: apiMock,
}))

const ADMIN = { id: "a1", full_name: "Demo Admin", role: "admin" } as User

function renderWith(
  path: string,
  routes: ReactNode,
  auth: Record<string, unknown> = { status: "authenticated", user: ADMIN },
) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <StaticAuthProvider value={auth}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>{routes}</Routes>
        </MemoryRouter>
      </StaticAuthProvider>
    </QueryClientProvider>,
  )
}

function page<T>(results: T[]): Paginated<T> {
  return { count: results.length, next: null, previous: null, results }
}

beforeEach(() => {
  apiMock.mockReset()
})

describe("RequireAdmin", () => {
  const routes = (
    <>
      <Route element={<RequireAdmin />}>
        <Route path="/admin" element={<p>Admin home</p>} />
      </Route>
      <Route path="/login" element={<p>Login page</p>} />
    </>
  )

  it("sends guests to log in", () => {
    renderWith("/admin", routes, { status: "guest" })
    expect(screen.getByText("Login page")).toBeInTheDocument()
  })

  it("blocks travellers", () => {
    renderWith("/admin", routes, { status: "authenticated", user: { ...ADMIN, role: "user" } })
    expect(screen.getByText("Admins only")).toBeInTheDocument()
    expect(screen.queryByText("Admin home")).not.toBeInTheDocument()
  })

  it("lets admins in", () => {
    renderWith("/admin", routes)
    expect(screen.getByText("Admin home")).toBeInTheDocument()
  })
})

describe("ColumnChart", () => {
  const data = [
    { label: "Oct", fullLabel: "October 2026", value: 4, display: "4" },
    { label: "Nov", fullLabel: "November 2026", value: 10, display: "10" },
  ]

  it("exposes every value to keyboard and screen readers, with a table view", async () => {
    render(<ColumnChart title="Bookings per month" data={data} valueLabel="Bookings" />)

    const bar = screen.getByRole("img", { name: "November 2026: 10" })
    fireEvent.focus(bar)
    expect(screen.getByRole("status")).toHaveTextContent("10November 2026")

    await userEvent.setup().click(screen.getByRole("button", { name: "Show table" }))
    const table = screen.getByRole("table", { name: "Bookings per month" })
    expect(within(table).getByText("October 2026")).toBeInTheDocument()
    expect(within(table).getByText("4")).toBeInTheDocument()
  })

  it("uses whole-number ticks for counts and says so when empty", () => {
    const { container, unmount } = render(
      <ColumnChart
        title="t"
        data={[{ ...data[0], value: 2, display: "2" }]}
        valueLabel="v"
        integer
      />,
    )
    const ticks = [...container.querySelectorAll("text")].map((t) => t.textContent)
    expect(ticks).toEqual(expect.arrayContaining(["0", "1", "2", "3", "4"]))
    expect(ticks.some((t) => t?.includes("."))).toBe(false)
    unmount()

    render(
      <ColumnChart
        title="t"
        data={[{ ...data[0], value: 0, display: "0" }]}
        valueLabel="v"
        emptyText="Nothing yet"
      />,
    )
    expect(screen.getByText("Nothing yet")).toBeInTheDocument()
  })

  it("caps bar width at 24px", () => {
    const { container } = render(<ColumnChart title="t" data={data.slice(0, 1)} valueLabel="v" />)
    const path = container.querySelector("path")!.getAttribute("d")!
    const xs = [...path.matchAll(/[MHQ]\s*([\d.]+)/g)].map((m) => Number(m[1]))
    expect(Math.max(...xs) - Math.min(...xs)).toBeLessThanOrEqual(24)
  })
})

describe("ConfirmAction", () => {
  it("needs a second step and, when asked, a note", async () => {
    const onConfirm = vi.fn()
    render(
      <ConfirmAction
        label="Cancel"
        question="Cancel HT-1?"
        confirmLabel="Cancel booking"
        requireNote="Reason"
        pending={false}
        onConfirm={onConfirm}
      />,
    )
    const user = userEvent.setup()
    await user.click(screen.getByRole("button", { name: "Cancel" }))
    const confirm = screen.getByRole("button", { name: "Cancel booking" })
    expect(confirm).toBeDisabled()

    await user.type(screen.getByLabelText("Reason"), "  Trail closed ")
    await user.click(confirm)
    expect(onConfirm).toHaveBeenCalledWith("Trail closed")
  })
})

describe("admin bookings", () => {
  it("cancels with a reason and refreshes", async () => {
    const booking = {
      id: "b1",
      reference: "HT-AAAA2222",
      status: "confirmed",
      departure: { id: "d1", start_date: "2027-03-01", end_date: "2027-03-04", status: "open" },
      adventure: { title: "Poon Hill Trek" },
      participant_count: 2,
      unit_price: "38000.00",
      total_amount: "76000.00",
      currency: "NPR",
      participants: [],
      payment: { status: "successful", provider: "esewa", paid_at: null },
      user: { id: "u1", full_name: "Maya Gurung", email: "maya@example.com", phone: null },
      history: [],
      cancellation_reason: "",
    } as unknown as AdminBooking
    apiMock.mockImplementation(async (path: string) =>
      path === "/admin/bookings/" ? page([booking]) : {},
    )
    const { BookingsPage } = await import("@/pages/admin/OperationsPages")
    renderWith("/admin/bookings", <Route path="/admin/bookings" element={<BookingsPage />} />)
    const user = userEvent.setup()

    await user.click(await screen.findByRole("button", { name: "Cancel" }))
    await user.type(screen.getByLabelText("Reason (sent to the traveller)"), "Landslide")
    await user.click(screen.getByRole("button", { name: "Cancel booking" }))

    expect(apiMock).toHaveBeenCalledWith("/admin/bookings/b1/cancel/", {
      method: "POST",
      body: { reason: "Landslide" },
    })
  })
})

describe("adventure form", () => {
  const adventure = {
    id: "adv1",
    title: "Poon Hill Trek",
    slug: "poon-hill",
    destination: "dest1",
    category: null,
    activity_type: "trekking",
    summary: "",
    description: "",
    difficulty: "easy",
    duration_days: 4,
    base_price: "38000.00",
    currency: "NPR",
    min_participants: 1,
    max_group_size: null,
    solo_friendly: true,
    inclusions: ["Guide"],
    exclusions: [],
    meeting_point: "",
    cancellation_policy: "",
    is_featured: false,
    status: "draft",
    published_at: null,
    itinerary: [
      {
        day_number: 1,
        title: "Nayapul to Tikhedhunga",
        description: "Long day",
        overnight_location: "",
        altitude_m: null,
      },
    ],
  } as AdminAdventure

  async function open() {
    apiMock.mockImplementation(async (path: string) => {
      if (path === "/admin/adventures/adv1/") return adventure
      if (path.startsWith("/admin/destinations/"))
        return page([{ id: "dest1", name: "Annapurna", status: "published" }])
      if (path.startsWith("/admin/categories/")) return page([])
      return adventure
    })
    const { AdventureFormPage } = await import("@/pages/admin/CatalogPages")
    renderWith(
      "/admin/adventures/adv1",
      <>
        <Route path="/admin/adventures/:id" element={<AdventureFormPage />} />
        <Route path="/admin/adventures" element={<p>List</p>} />
      </>,
    )
    await screen.findByRole("heading", { name: "Edit: Poon Hill Trek" })
    return userEvent.setup()
  }

  it("does not resend an unchanged itinerary (which would wipe day details)", async () => {
    const user = await open()
    await user.clear(screen.getByLabelText("Base price per person (NPR)"))
    await user.type(screen.getByLabelText("Base price per person (NPR)"), "41000")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    const call = apiMock.mock.calls.find(
      ([path, options]) => path === "/admin/adventures/adv1/" && options?.method === "PATCH",
    )!
    expect(call[1].body.base_price).toBe("41000")
    expect(call[1].body.inclusions).toEqual(["Guide"])
    expect("itinerary" in call[1].body).toBe(false)
  })

  it("sends the itinerary when days were edited", async () => {
    const user = await open()
    await user.type(screen.getByLabelText("Itinerary"), "\nTikhedhunga to Ghorepani")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    const call = apiMock.mock.calls.find(
      ([path, options]) => path === "/admin/adventures/adv1/" && options?.method === "PATCH",
    )!
    expect(call[1].body.itinerary).toEqual([
      { day_number: 1, title: "Nayapul to Tikhedhunga" },
      { day_number: 2, title: "Tikhedhunga to Ghorepani" },
    ])
  })
})
