import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { ApiError } from "@/lib/api"
import type { PaymentAttempt, VerifyResult } from "@/types/api"

import { goToGateway } from "./payments"
import { PaymentSelector } from "./PaymentSelector"

const apiMock = vi.hoisted(() => vi.fn())
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: apiMock,
}))

const PROVIDERS = [
  { code: "esewa" as const, name: "eSewa" },
  { code: "khalti" as const, name: "Khalti" },
]

describe("PaymentSelector", () => {
  function setup(overrides: Partial<React.ComponentProps<typeof PaymentSelector>> = {}) {
    const onPay = vi.fn()
    render(
      <PaymentSelector
        providers={PROVIDERS}
        amount="76000.00"
        currency="NPR"
        submitting={false}
        error={null}
        onPay={onPay}
        {...overrides}
      />,
    )
    return { onPay, user: userEvent.setup() }
  }

  it("pays with the chosen provider and shows the server amount", async () => {
    const { onPay, user } = setup()
    expect(screen.getByRole("radio", { name: "eSewa" })).toBeChecked()

    await user.click(screen.getByRole("radio", { name: "Khalti" }))
    await user.click(screen.getByRole("button", { name: "Pay NPR 76,000 with Khalti" }))

    expect(onPay).toHaveBeenCalledWith("khalti")
  })

  it("prevents double submission while connecting", () => {
    setup({ submitting: true })
    expect(screen.getByRole("button", { name: /Connecting to the provider/ })).toBeDisabled()
  })

  it("shows provider errors from the server", () => {
    setup({
      error: new ApiError(400, "validation_error", "Invalid input.", {
        provider: ["Khalti payments must be more than NPR 10."],
      }),
    })
    expect(screen.getByRole("alert")).toHaveTextContent("more than NPR 10")
  })

  it("explains when no method is available", () => {
    setup({ providers: [] })
    expect(screen.getByText(/Online payment is not available/)).toBeInTheDocument()
    expect(screen.queryByRole("button")).not.toBeInTheDocument()
  })
})

describe("goToGateway", () => {
  it("posts eSewa's signed fields as a hidden form", () => {
    const submit = vi.spyOn(HTMLFormElement.prototype, "submit").mockImplementation(() => {})

    goToGateway({
      attempt: "a1",
      method: "POST",
      url: "https://rc-epay.esewa.com.np/api/epay/main/v2/form",
      fields: { total_amount: "76000", signature: "abc=" },
    })

    const form = document.body.querySelector("form")!
    expect(form.method).toBe("post")
    expect(form.action).toBe("https://rc-epay.esewa.com.np/api/epay/main/v2/form")
    expect(Object.fromEntries(new FormData(form))).toEqual({
      total_amount: "76000",
      signature: "abc=",
    })
    expect(submit).toHaveBeenCalledOnce()
    form.remove()
  })
})

const ATTEMPT: PaymentAttempt = {
  id: "att-1",
  provider: "esewa",
  reference: "HT-4HBFZ8WV-1A2B3C",
  amount: "76000.00",
  currency: "NPR",
  status: "successful",
  gateway_status: "COMPLETE",
  gateway_transaction_id: "0007G36",
  created_at: "2026-11-19T10:00:00Z",
  completed_at: "2026-11-19T10:03:00Z",
}

function result(attempt: Partial<PaymentAttempt>, bookingStatus = "confirmed"): VerifyResult {
  return {
    attempt: { ...ATTEMPT, ...attempt },
    payment: {
      id: "pay-1",
      booking_id: "b1",
      booking_reference: "HT-4HBFZ8WV",
      booking_status: bookingStatus as VerifyResult["payment"]["booking_status"],
      adventure: "Poon Hill Trek",
      amount: "76000.00",
      currency: "NPR",
      status: "successful",
      provider: "esewa",
      gateway_reference: "0007G36",
      paid_at: null,
      created_at: "2026-11-19T10:00:00Z",
      attempts: [],
    },
  }
}

describe("PaymentReturnPage", () => {
  beforeEach(() => {
    apiMock.mockReset()
  })

  async function renderReturn(url: string) {
    const { default: PaymentReturnPage } = await import("@/pages/PaymentReturnPage")
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <MemoryRouter initialEntries={[url]}>
          <Routes>
            <Route path="/payments/:provider/:attemptId/:outcome" element={<PaymentReturnPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
  }

  it("sends the gateway parameters to our server and shows a confirmed booking", async () => {
    apiMock.mockResolvedValue(result({}))
    await renderReturn("/payments/esewa/att-1/success?data=eyJzdGF0dXMiOiJDT01QTEVURSJ9")

    expect(
      await screen.findByRole("heading", { name: /Payment received - you're booked/ }),
    ).toBeInTheDocument()
    expect(apiMock).toHaveBeenCalledWith("/payments/verify/", {
      method: "POST",
      body: { attempt: "att-1", params: { data: "eyJzdGF0dXMiOiJDT01QTEVURSJ9" } },
      signal: expect.anything(),
    })
    expect(screen.getByRole("link", { name: "View booking HT-4HBFZ8WV" })).toHaveAttribute(
      "href",
      "/dashboard/bookings/b1",
    )
  })

  it("does not claim success just because the URL says so", async () => {
    apiMock.mockResolvedValue(result({ status: "failed", gateway_status: "COMPLETE" }))
    await renderReturn("/payments/khalti/att-1/return?status=Completed&pidx=X")
    expect(
      await screen.findByRole("heading", { name: "Payment not completed" }),
    ).toBeInTheDocument()
  })

  it("explains a paid booking that could not be confirmed", async () => {
    apiMock.mockResolvedValue(result({}, "expired"))
    await renderReturn("/payments/esewa/att-1/success")
    expect(await screen.findByText(/team will contact you and refund/)).toBeInTheDocument()
  })

  it("shows processing and cancelled states", async () => {
    apiMock.mockResolvedValue(result({ status: "processing" }))
    await renderReturn("/payments/esewa/att-1/failure")
    expect(
      await screen.findByRole("heading", { name: "Payment still processing" }),
    ).toBeInTheDocument()
  })

  it("lets the traveller retry when our server can't be reached", async () => {
    apiMock.mockRejectedValue(new ApiError(0, "network_error", "Cannot reach the server."))
    await renderReturn("/payments/esewa/att-1/success")
    // The verify query retries once before giving up, so allow for the retry delay.
    expect(
      await screen.findByRole("button", { name: "Try again" }, { timeout: 4000 }),
    ).toBeInTheDocument()
  })
})
