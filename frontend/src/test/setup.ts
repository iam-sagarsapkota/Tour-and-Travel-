import "@testing-library/jest-dom/vitest"

import { cleanup } from "@testing-library/react"
import { afterEach, vi } from "vitest"

afterEach(() => {
  cleanup()
  sessionStorage.clear()
})

// jsdom lacks these browser APIs used by layout/animation code.
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
})

class Observer {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
  takeRecords = () => []
}
vi.stubGlobal("IntersectionObserver", Observer)
vi.stubGlobal("ResizeObserver", Observer)
window.scrollTo = vi.fn() as unknown as typeof window.scrollTo
