import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { Booking } from "@/types/api"

import { BookingForm } from "./BookingForm"
import { BookingSummary } from "./BookingSummary"

const apiMock = vi.hoisted(() => vi.fn())
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: apiMock,
}))

function renderForm(overrides: Partial<React.ComponentProps<typeof BookingForm>> = {}) {
  const props = {
    departureId: "dep-1",
    minParticipants: 1,
    maxParticipants: 3,
    leadName: "Maya Gurung",
    cancellationPolicy: "Full refund up to 14 days before departure.",
    submitting: false,
    onCountChange: vi.fn(),
    onSubmit: vi.fn(),
    ...overrides,
  }
  render(<BookingForm {...props} />)
  return { ...props, user: userEvent.setup() }
}

describe("BookingForm", () => {
  it("prefills the lead traveller and shows the policy", () => {
    renderForm()
    expect(screen.getByLabelText("Full name")).toHaveValue("Maya Gurung")
    expect(screen.getByText(/Full refund up to 14 days/)).toBeInTheDocument()
  })

  it("adds traveller fields within the allowed range", async () => {
    const { user, onCountChange } = renderForm()
    const add = screen.getByRole("button", { name: "Add a traveller" })
    const remove = screen.getByRole("button", { name: "Remove a traveller" })

    expect(remove).toBeDisabled()
    await user.click(add)
    await user.click(add)
    expect(onCountChange).toHaveBeenLastCalledWith(3)
    expect(screen.getAllByLabelText("Full name")).toHaveLength(3)
    expect(add).toBeDisabled()

    await user.click(remove)
    expect(onCountChange).toHaveBeenLastCalledWith(2)
    expect(screen.getAllByLabelText("Full name")).toHaveLength(2)
  })

  it("starts groups-only trips at the minimum size", () => {
    renderForm({ minParticipants: 2, maxParticipants: 6 })
    expect(screen.getAllByLabelText("Full name")).toHaveLength(2)
    expect(screen.getByRole("button", { name: "Remove a traveller" })).toBeDisabled()
  })

  it("requires every name and the policy before submitting", async () => {
    const { user, onSubmit } = renderForm()
    await user.click(screen.getByRole("button", { name: "Add a traveller" }))
    await user.click(screen.getByRole("button", { name: "Reserve places" }))

    expect(screen.getByText("Enter this traveller's full name.")).toBeInTheDocument()
    expect(screen.getByText(/confirm you have read the cancellation policy/i)).toBeInTheDocument()
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it("submits names and acceptance, never a price", async () => {
    const { user, onSubmit } = renderForm()
    await user.click(screen.getByRole("button", { name: "Add a traveller" }))
    await user.type(screen.getAllByLabelText("Full name")[1], "  Dawa Lama ")
    await user.type(screen.getAllByLabelText("Nationality (optional)")[1], "Nepali")
    await user.click(screen.getByRole("checkbox", { name: /accept the booking/i }))
    await user.click(screen.getByRole("button", { name: "Reserve places" }))

    expect(onSubmit).toHaveBeenCalledWith({
      departure: "dep-1",
      participants: [
        { full_name: "Maya Gurung", nationality: "" },
        { full_name: "Dawa Lama", nationality: "Nepali" },
      ],
      policy_accepted: true,
    })
  })

  it("shows server errors", () => {
    renderForm({ serverError: "Only 1 seat left on this departure." })
    expect(screen.getByRole("alert")).toHaveTextContent("Only 1 seat left")
  })
})

describe("BookingSummary", () => {
  it("shows the server-calculated itemised price", () => {
    render(
      <BookingSummary
        title="Poon Hill Trek"
        startDate="2027-03-01"
        endDate="2027-03-04"
        participantCount={2}
        unitPrice="38000.00"
        total="76000.00"
        currency="NPR"
      />,
    )
    const summary = screen.getByRole("region", { name: "Booking summary" })
    expect(summary).toHaveTextContent("Travellers2")
    expect(summary).toHaveTextContent("Price per personNPR 38,000")
    expect(summary).toHaveTextContent("TotalNPR 76,000")
  })

  it("waits for the server instead of guessing a total", () => {
    render(
      <BookingSummary
        title="Poon Hill Trek"
        startDate="2027-03-01"
        endDate="2027-03-04"
        participantCount={2}
        currency="NPR"
      />,
    )
    expect(screen.getByText("Calculating…")).toBeInTheDocument()
  })
})

const PENDING: Booking = {
  id: "b1",
  reference: "HT-4HBFZ8WV",
  status: "pending",
  departure: { id: "d1", start_date: "2027-03-01", end_date: "2027-03-04", status: "open" },
  adventure: {
    title: "Poon Hill Trek",
    slug: "poon-hill-trek",
    cover_image: null,
    duration_days: 4,
    destination: "Annapurna Region",
    cancellation_policy: "",
  },
  participant_count: 1,
  unit_price: "38000.00",
  total_amount: "38000.00",
  currency: "NPR",
  participants: [{ full_name: "Maya Gurung", nationality: "", date_of_birth: null, is_lead: true }],
  expires_at: "2027-01-01T10:15:00Z",
  confirmed_at: null,
  cancelled_at: null,
  cancellation_reason: "",
  created_at: "2027-01-01T10:00:00Z",
  can_cancel: true,
  payment: null,
}

describe("BookingDetailPage", () => {
  beforeEach(() => {
    apiMock.mockReset()
  })

  async function renderDetail(booking: Booking) {
    apiMock.mockImplementation(async (path: string) => {
      if (path === "/bookings/b1/") return booking
      if (path === "/payments/providers/") return [{ code: "esewa", name: "eSewa" }]
      if (path === "/bookings/b1/cancel/")
        return { ...booking, status: "cancelled", can_cancel: false }
      throw new Error(`unexpected ${path}`)
    })
    const { default: BookingDetailPage } = await import("@/pages/dashboard/BookingDetailPage")
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <MemoryRouter initialEntries={["/dashboard/bookings/b1"]}>
          <Routes>
            <Route path="/dashboard/bookings/:id" element={<BookingDetailPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    await screen.findByRole("heading", { name: "Poon Hill Trek" })
    return userEvent.setup()
  }

  it("explains the hold and asks before cancelling", async () => {
    const user = await renderDetail(PENDING)
    expect(screen.getByText(/places are held until/i)).toBeInTheDocument()

    await user.click(screen.getByRole("button", { name: "Cancel booking" }))
    expect(screen.getByText("Cancel booking HT-4HBFZ8WV?")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Keep booking" }))
    expect(apiMock).not.toHaveBeenCalledWith("/bookings/b1/cancel/", expect.anything())

    await user.click(screen.getByRole("button", { name: "Cancel booking" }))
    await user.click(screen.getByRole("button", { name: "Yes, cancel it" }))

    expect(apiMock).toHaveBeenCalledWith("/bookings/b1/cancel/", { method: "POST" })
    expect(await screen.findByText(/This booking was cancelled/)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel booking" })).not.toBeInTheDocument()
  })

  it("does not offer online cancellation for a paid booking", async () => {
    await renderDetail({ ...PENDING, status: "confirmed", can_cancel: false, expires_at: null })
    expect(screen.getByText(/booking is confirmed/i)).toBeInTheDocument()
    expect(screen.getByText(/please contact us/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Cancel booking" })).not.toBeInTheDocument()
  })
})
