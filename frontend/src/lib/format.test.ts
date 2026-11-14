import { describe, expect, it } from "vitest"

import { formatDate, formatDuration, formatMoney } from "./format"

describe("format", () => {
  it("formats whole and fractional money", () => {
    expect(formatMoney("38000.00", "NPR")).toBe("NPR 38,000")
    expect(formatMoney("19999.50", "NPR")).toBe("NPR 19,999.50")
  })

  it("formats ISO dates without time zone drift", () => {
    expect(formatDate("2027-03-01")).toBe("1 Mar 2027")
  })

  it("pluralises duration", () => {
    expect(formatDuration(1)).toBe("1 day")
    expect(formatDuration(14)).toBe("14 days")
  })
})
