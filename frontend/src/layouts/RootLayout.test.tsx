import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { Link, MemoryRouter, Route, Routes } from "react-router-dom"
import { afterEach, describe, expect, it, vi } from "vitest"

import { StaticAuthProvider } from "@/features/auth/AuthContext"

import { RootLayout } from "./RootLayout"

describe("RootLayout", () => {
  const original = window.scrollTo
  afterEach(() => {
    window.scrollTo = original
  })

  it("survives navigation when scrollTo returns a Promise (Chromium behaviour)", async () => {
    // Regression: an effect returning this Promise crashed React with a blank page.
    const scrollTo = vi.fn(() => Promise.resolve())
    window.scrollTo = scrollTo as unknown as typeof window.scrollTo

    render(
      <QueryClientProvider client={new QueryClient()}>
        <StaticAuthProvider value={{ status: "guest" }}>
          <MemoryRouter initialEntries={["/"]}>
            <Routes>
              <Route element={<RootLayout />}>
                <Route index element={<Link to="/next">Go</Link>} />
                <Route path="next" element={<p>Next page</p>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </StaticAuthProvider>
      </QueryClientProvider>,
    )

    await userEvent.setup().click(screen.getByRole("link", { name: "Go" }))

    expect(screen.getByText("Next page")).toBeInTheDocument()
    expect(scrollTo).toHaveBeenCalledTimes(2)
  })
})
