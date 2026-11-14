/**
 * Token storage.
 *
 * - Access token: memory only. It is short-lived and never written to storage.
 * - Refresh token: sessionStorage, so a page reload keeps the user signed in but
 *   closing the tab ends the session. It is rotated by the API on every use.
 *
 * Tokens are sent in the Authorization header (never cookies), so there is no CSRF
 * exposure; preventing XSS is what protects them. See docs/authentication.md.
 */
const REFRESH_KEY = "ht.refresh"

let accessToken: string | null = null

export const tokenStore = {
  getAccess: () => accessToken,
  getRefresh: (): string | null => {
    try {
      return sessionStorage.getItem(REFRESH_KEY)
    } catch {
      return null
    }
  },
  set(tokens: { access: string; refresh?: string }) {
    accessToken = tokens.access
    if (tokens.refresh) {
      try {
        sessionStorage.setItem(REFRESH_KEY, tokens.refresh)
      } catch {
        // Storage unavailable (private mode): session lasts until reload.
      }
    }
  },
  clear() {
    accessToken = null
    try {
      sessionStorage.removeItem(REFRESH_KEY)
    } catch {
      // nothing to clear
    }
  },
}
