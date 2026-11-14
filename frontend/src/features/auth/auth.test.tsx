import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom"
import { describe, expect, it, vi } from "vitest"

import { ApiError } from "@/lib/api"
import type { User } from "@/types/api"

import { StaticAuthProvider } from "./AuthContext"
import { LoginPage, RegisterPage } from "./AuthForms"
import { RequireAuth } from "./RequireAuth"

const USER = { id: "1", full_name: "Maya Gurung" } as User

function Where() {
  const location = useLocation()
  return <p data-testid="where">{`${location.pathname}${location.search}`}</p>
}

function renderApp(
  initial: string,
  auth: React.ComponentProps<typeof StaticAuthProvider>["value"] = {},
) {
  return render(
    <StaticAuthProvider value={auth}>
      <MemoryRouter initialEntries={[initial]}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route element={<RequireAuth />}>
            <Route path="/events/:slug" element={<p>Secret itinerary</p>} />
          </Route>
          <Route path="*" element={<Where />} />
        </Routes>
      </MemoryRouter>
    </StaticAuthProvider>,
  )
}

describe("RequireAuth", () => {
  it("sends a guest to registration with a return path", () => {
    renderApp("/events/poon-hill-trek?ref=home")

    expect(screen.queryByText("Secret itinerary")).not.toBeInTheDocument()
    expect(screen.getByRole("heading", { name: "Create your account" })).toBeInTheDocument()
    // The login link keeps the return path.
    expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute(
      "href",
      "/login?next=%2Fevents%2Fpoon-hill-trek%3Fref%3Dhome",
    )
  })

  it("shows the page to an authenticated user", () => {
    renderApp("/events/poon-hill-trek", { status: "authenticated", user: USER })
    expect(screen.getByText("Secret itinerary")).toBeInTheDocument()
  })

  it("shows a loading state while the session is being restored", () => {
    renderApp("/events/poon-hill-trek", { status: "loading" })
    expect(screen.getByRole("status")).toBeInTheDocument()
    expect(screen.queryByText("Secret itinerary")).not.toBeInTheDocument()
  })
})

describe("RegisterPage", () => {
  it("requires an email or a phone number", async () => {
    const register = vi.fn()
    renderApp("/register", { register })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Full name"), "Maya Gurung")
    await user.type(screen.getByLabelText("Password"), "Trek-Safely-2026")
    await user.type(screen.getByLabelText("Confirm password"), "Trek-Safely-2026")
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect(screen.getByText(/email or a phone number/i)).toBeInTheDocument()
    expect(screen.getByLabelText("Email")).toHaveAttribute("aria-invalid", "true")
    expect(register).not.toHaveBeenCalled()
  })

  it("rejects mismatched passwords before calling the API", async () => {
    const register = vi.fn()
    renderApp("/register", { register })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Full name"), "Maya Gurung")
    await user.type(screen.getByLabelText("Phone number"), "9812345678")
    await user.type(screen.getByLabelText("Password"), "Trek-Safely-2026")
    await user.type(screen.getByLabelText("Confirm password"), "Different-2026")
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect(screen.getByText("Passwords do not match.")).toBeInTheDocument()
    expect(register).not.toHaveBeenCalled()
  })

  it("registers with phone only and returns to the requested event", async () => {
    const register = vi.fn().mockResolvedValue(USER)
    renderApp("/register?next=%2Fevents%2Fpoon-hill-trek", { register })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Full name"), "Maya Gurung")
    await user.type(screen.getByLabelText("Phone number"), "9812345678")
    await user.type(screen.getByLabelText("Password"), "Trek-Safely-2026")
    await user.type(screen.getByLabelText("Confirm password"), "Trek-Safely-2026")
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect(register).toHaveBeenCalledWith({
      full_name: "Maya Gurung",
      phone: "9812345678",
      password: "Trek-Safely-2026",
      password_confirm: "Trek-Safely-2026",
    })
    // RequireAuth still sees a guest in this static test, so assert the navigation target.
    expect(await screen.findByRole("heading", { name: "Create your account" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Log in" })).toHaveAttribute(
      "href",
      "/login?next=%2Fevents%2Fpoon-hill-trek",
    )
  })

  it("shows field errors returned by the API", async () => {
    const register = vi.fn().mockRejectedValue(
      new ApiError(400, "validation_error", "Invalid input.", {
        email: ["An account with this email already exists."],
      }),
    )
    renderApp("/register", { register })
    const user = userEvent.setup()

    await user.type(screen.getByLabelText("Full name"), "Maya Gurung")
    await user.type(screen.getByLabelText("Email"), "maya@example.com")
    await user.type(screen.getByLabelText("Password"), "Trek-Safely-2026")
    await user.type(screen.getByLabelText("Confirm password"), "Trek-Safely-2026")
    await user.click(screen.getByRole("button", { name: "Create account" }))

    expect(
      await screen.findByText("An account with this email already exists."),
    ).toBeInTheDocument()
  })
})

describe("LoginPage", () => {
  async function submit(next: string, login = vi.fn().mockResolvedValue(USER)) {
    renderApp(`/login${next}`, { login })
    const user = userEvent.setup()
    await user.type(screen.getByLabelText("Email or phone number"), "maya@example.com")
    await user.type(screen.getByLabelText("Password"), "Trek-Safely-2026")
    await user.click(screen.getByRole("button", { name: "Log in" }))
    return login
  }

  it("goes to the default page after login", async () => {
    const login = await submit("")
    expect(login).toHaveBeenCalledWith("maya@example.com", "Trek-Safely-2026")
    expect(await screen.findByTestId("where")).toHaveTextContent("/events")
  })

  it("returns to a safe local next path", async () => {
    await submit("?next=%2Fdestinations%2Feverest")
    expect(await screen.findByTestId("where")).toHaveTextContent("/destinations/everest")
  })

  it.each(["https%3A%2F%2Fevil.example", "%2F%2Fevil.example%2Fevents"])(
    "ignores the unsafe next value %s",
    async (next) => {
      await submit(`?next=${next}`)
      expect(await screen.findByTestId("where")).toHaveTextContent(/^\/events$/)
    },
  )

  it("explains a failed login without revealing which part was wrong", async () => {
    const login = vi
      .fn()
      .mockRejectedValue(new ApiError(401, "invalid_credentials", "Invalid credentials."))
    await submit("", login)
    expect(await screen.findByRole("alert")).toHaveTextContent(/don't match an account/i)
  })

  it("validates empty fields locally", async () => {
    const login = vi.fn()
    renderApp("/login", { login })
    await userEvent.setup().click(screen.getByRole("button", { name: "Log in" }))
    expect(screen.getByText("Enter your email or phone number.")).toBeInTheDocument()
    expect(login).not.toHaveBeenCalled()
  })
})
