/**
 * Validate the `next` return path used after login/registration.
 *
 * Only same-site paths under a known prefix are accepted. Anything else
 * (absolute URLs, protocol-relative `//host`, backslash tricks, unknown
 * sections) falls back to the default, which prevents open redirects.
 */
const ALLOWED_PREFIXES = ["/events", "/destinations", "/dashboard", "/admin", "/payments"]

export const DEFAULT_AFTER_AUTH = "/events"

export function safeNext(next: string | null | undefined, fallback = DEFAULT_AFTER_AUTH): string {
  if (!next) return fallback
  // Must be a single-slash absolute path with no scheme, backslashes or control characters.
  if (!next.startsWith("/") || next.startsWith("//")) return fallback
  // oxlint-disable-next-line no-control-regex -- rejecting control characters is the point
  if (/[\\\u0000-\u001f]/.test(next)) return fallback

  let url: URL
  try {
    url = new URL(next, "http://local.invalid")
  } catch {
    return fallback
  }
  if (url.origin !== "http://local.invalid") return fallback

  const allowed = ALLOWED_PREFIXES.some(
    (prefix) => url.pathname === prefix || url.pathname.startsWith(`${prefix}/`),
  )
  return allowed ? `${url.pathname}${url.search}${url.hash}` : fallback
}

/** Build `/register?next=...` (or `/login?next=...`) for a guest who hit a protected page. */
export function authRedirect(page: "/register" | "/login", next: string): string {
  return `${page}?next=${encodeURIComponent(next)}`
}
