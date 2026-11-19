import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { MemoryRouter, Route, Routes } from "react-router-dom"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { StaticAuthProvider } from "@/features/auth/AuthContext"
import { ApiError } from "@/lib/api"
import type { TravellerDashboard, User } from "@/types/api"

const apiMock = vi.hoisted(() => vi.fn())
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  api: apiMock,
}))

const USER: User = {
  id: "u1",
  full_name: "Maya Gurung",
  email: "maya@example.com",
  phone: null,
  role: "user",
  email_verified: false,
  phone_verified: false,
  date_joined: "2026-11-01T00:00:00Z",
  profile: {
    date_of_birth: null,
    nationality: "Nepali",
    address: "",
    emergency_contact_name: "",
    emergency_contact_phone: "",
    trip_reminders: true,
  },
}

function renderAt(path: string, element: ReactNode, route = path.split("?")[0], auth = {}) {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <StaticAuthProvider value={{ status: "authenticated", user: USER, ...auth }}>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path={route} element={element} />
            <Route path="/login" element={<p>Login page</p>} />
          </Routes>
        </MemoryRouter>
      </StaticAuthProvider>
    </QueryClientProvider>,
  )
}

beforeEach(() => {
  apiMock.mockReset()
})

describe("ProfilePage", () => {
  async function setup(auth = {}) {
    apiMock.mockImplementation(async (path: string) => (path === "/auth/sessions/" ? [] : USER))
    const { default: ProfilePage } = await import("@/pages/dashboard/ProfilePage")
    renderAt("/dashboard/profile", <ProfilePage />, "/dashboard/profile", auth)
    return userEvent.setup()
  }

  it("saves name, profile and reminder preference", async () => {
    const refreshUser = vi.fn()
    const user = await setup({ refreshUser })
    await user.clear(screen.getByLabelText("Full name"))
    await user.type(screen.getByLabelText("Full name"), "Maya L. Gurung")
    await user.click(screen.getByRole("checkbox", { name: /reminder/i }))
    await user.click(screen.getByRole("button", { name: "Save profile" }))

    expect(apiMock).toHaveBeenCalledWith("/auth/me/", {
      method: "PATCH",
      body: {
        full_name: "Maya L. Gurung",
        profile: {
          nationality: "Nepali",
          emergency_contact_name: "",
          emergency_contact_phone: "",
          trip_reminders: false,
        },
      },
    })
    expect(refreshUser).toHaveBeenCalled()
  })

  it("offers to resend the verification email", async () => {
    const user = await setup()
    expect(screen.getByText("Not verified")).toBeInTheDocument()
    await user.click(screen.getByRole("button", { name: "Send verification link" }))
    expect(apiMock).toHaveBeenCalledWith("/auth/verify-email/resend/", { method: "POST" })
    expect(await screen.findByText(/sent a new link/)).toBeInTheDocument()
  })

  it("checks the new password before calling the API", async () => {
    const user = await setup()
    await user.type(screen.getByLabelText("Current password"), "old-password")
    await user.type(screen.getByLabelText("New password"), "Brand-New-2027")
    await user.type(screen.getByLabelText("Confirm new password"), "Different-2027")
    await user.click(screen.getByRole("button", { name: "Change password" }))

    expect(screen.getByText("Passwords do not match.")).toBeInTheDocument()
    expect(apiMock).not.toHaveBeenCalledWith("/auth/password/change/", expect.anything())
  })

  it("shows a wrong current password from the server", async () => {
    const user = await setup()
    apiMock.mockImplementation(async (path: string) => {
      if (path === "/auth/password/change/")
        throw new ApiError(400, "validation_error", "Invalid input.", {
          current_password: ["Current password is incorrect."],
        })
      return []
    })
    await user.type(screen.getByLabelText("Current password"), "wrong")
    await user.type(screen.getByLabelText("New password"), "Brand-New-2027")
    await user.type(screen.getByLabelText("Confirm new password"), "Brand-New-2027")
    await user.click(screen.getByRole("button", { name: "Change password" }))

    expect(await screen.findByText("Current password is incorrect.")).toBeInTheDocument()
  })

  it("signs out everywhere only after confirmation", async () => {
    const endSession = vi.fn()
    const user = await setup({ endSession })
    await user.click(screen.getByRole("button", { name: "Sign out of all devices" }))
    await user.click(screen.getByRole("button", { name: "Yes, sign out everywhere" }))

    expect(apiMock).toHaveBeenCalledWith("/auth/sessions/", { method: "DELETE" })
    expect(endSession).toHaveBeenCalled()
    expect(await screen.findByText("Login page")).toBeInTheDocument()
  })
})

describe("OverviewPage", () => {
  it("summarises trips and links unpaid bookings to payment", async () => {
    const pending = {
      id: "b1",
      reference: "HT-AAAA2222",
      status: "pending",
      departure: { id: "d1", start_date: "2027-03-01", end_date: "2027-03-04", status: "open" },
      adventure: {
        title: "Poon Hill Trek",
        slug: "poon-hill",
        cover_image: null,
        duration_days: 4,
        destination: "Annapurna",
        cancellation_policy: "",
      },
      participant_count: 2,
      unit_price: "38000.00",
      total_amount: "76000.00",
      currency: "NPR",
      participants: [],
      expires_at: "2027-01-01T00:00:00Z",
      confirmed_at: null,
      cancelled_at: null,
      cancellation_reason: "",
      created_at: "2026-11-19T00:00:00Z",
      can_cancel: true,
      payment: null,
    }
    const dashboard = {
      counts: { total: 3, upcoming: 1, completed: 1, cancelled: 1 },
      total_spent: "45000.00",
      currency: "NPR",
      upcoming: [pending],
      pending_payment: [pending],
      recommendations: [],
    } as unknown as TravellerDashboard
    apiMock.mockResolvedValue(dashboard)
    const { default: OverviewPage } = await import("@/pages/dashboard/OverviewPage")
    renderAt("/dashboard", <OverviewPage />)

    expect(await screen.findByRole("heading", { name: "Namaste, Maya" })).toBeInTheDocument()
    expect((await screen.findByText("Total paid")).nextSibling).toHaveTextContent("NPR 45,000")
    expect(screen.getByRole("link", { name: "Pay now" })).toHaveAttribute(
      "href",
      "/dashboard/bookings/b1",
    )
  })
})

describe("public account pages", () => {
  it("never reveals whether an email is registered", async () => {
    apiMock.mockResolvedValue(undefined)
    const { ForgotPasswordPage } = await import("@/pages/AccountPublicPages")
    renderAt("/forgot-password", <ForgotPasswordPage />, "/forgot-password", { status: "guest" })
    const user = userEvent.setup()
    await user.type(screen.getByLabelText("Email"), "ghost@example.com")
    await user.click(screen.getByRole("button", { name: "Send reset link" }))

    expect(await screen.findByText(/If an account exists for that email/)).toBeInTheDocument()
  })

  it("rejects an incomplete reset link", async () => {
    const { ResetPasswordPage } = await import("@/pages/AccountPublicPages")
    renderAt("/reset-password?uid=abc", <ResetPasswordPage />, "/reset-password", {
      status: "guest",
    })
    expect(screen.getByText(/link is incomplete/)).toBeInTheDocument()
  })

  it("resets the password with the link's uid and token", async () => {
    apiMock.mockResolvedValue(undefined)
    const { ResetPasswordPage } = await import("@/pages/AccountPublicPages")
    renderAt("/reset-password?uid=U1&token=T1", <ResetPasswordPage />, "/reset-password", {
      status: "guest",
    })
    const user = userEvent.setup()
    await user.type(screen.getByLabelText("New password"), "Brand-New-2027")
    await user.type(screen.getByLabelText("Confirm new password"), "Brand-New-2027")
    await user.click(screen.getByRole("button", { name: "Set new password" }))

    expect(apiMock).toHaveBeenCalledWith("/auth/password/reset/confirm/", {
      method: "POST",
      body: {
        uid: "U1",
        token: "T1",
        new_password: "Brand-New-2027",
        new_password_confirm: "Brand-New-2027",
      },
      auth: false,
    })
    expect(await screen.findByText("Your password has been changed.")).toBeInTheDocument()
  })

  it("verifies an email link exactly once", async () => {
    apiMock.mockResolvedValue(undefined)
    const { VerifyEmailPage } = await import("@/pages/AccountPublicPages")
    renderAt("/verify-email?token=TOK", <VerifyEmailPage />, "/verify-email")

    expect(await screen.findByText("Your email is verified.")).toBeInTheDocument()
    expect(apiMock.mock.calls.filter(([path]) => path === "/auth/verify-email/")).toHaveLength(1)
  })

  it("sends the contact form", async () => {
    apiMock.mockImplementation(async (path: string) =>
      path === "/site/" ? { support_email: "hello@trails.test", support_phone: "" } : {},
    )
    const { ContactPage } = await import("@/pages/AccountPublicPages")
    renderAt("/contact", <ContactPage />, "/contact", { status: "guest" })
    const user = userEvent.setup()
    await user.type(screen.getByLabelText("Your name"), "Anna")
    await user.type(screen.getByLabelText("Email"), "anna@example.com")
    await user.type(screen.getByLabelText("Subject"), "Private group")
    await user.type(screen.getByLabelText("Message"), "Twelve of us in March.")
    await user.click(screen.getByRole("button", { name: "Send message" }))

    expect(await screen.findByText(/Your message has been sent/)).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "hello@trails.test" })).toBeInTheDocument()
  })
})
