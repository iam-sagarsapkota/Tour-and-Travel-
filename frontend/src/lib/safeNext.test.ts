import { describe, expect, it } from "vitest"

import { authRedirect, DEFAULT_AFTER_AUTH, safeNext } from "./safeNext"

describe("safeNext", () => {
  it.each([
    ["/events/poon-hill-trek", "/events/poon-hill-trek"],
    ["/events?difficulty=easy", "/events?difficulty=easy"],
    ["/destinations/everest", "/destinations/everest"],
    ["/dashboard", "/dashboard"],
  ])("keeps the local path %s", (input, expected) => {
    expect(safeNext(input)).toBe(expected)
  })

  it.each([
    null,
    undefined,
    "",
    "https://evil.example/events",
    "//evil.example/events",
    "/\\evil.example",
    "\\\\evil.example",
    "javascript:alert(1)",
    "events/relative",
    "/login",
    "/eventsevil",
    "/events/../../admin-secrets",
    "/events\n/x",
  ])("rejects %s and falls back", (input) => {
    expect(safeNext(input)).toBe(DEFAULT_AFTER_AUTH)
  })

  it("builds an encoded auth redirect", () => {
    expect(authRedirect("/register", "/events/abc?x=1")).toBe(
      "/register?next=%2Fevents%2Fabc%3Fx%3D1",
    )
  })
})
