import type { ApiErrorBody } from "@/types/api"

import { tokenStore } from "./tokens"

const BASE_URL = `${import.meta.env.VITE_API_BASE_URL ?? ""}/api/v1`

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  /** Field name -> messages, for validation errors. */
  readonly fieldErrors: Record<string, string[]>

  constructor(
    status: number,
    code: string,
    message: string,
    details?: ApiErrorBody["error"]["details"],
  ) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.code = code
    this.fieldErrors = {}
    for (const [field, value] of Object.entries(details ?? {})) {
      this.fieldErrors[field] = Array.isArray(value) ? value.map(String) : [String(value)]
    }
  }

  /** First message for a field, or for the form as a whole. */
  first(field: string): string | undefined {
    return this.fieldErrors[field]?.[0]
  }

  get formError(): string | undefined {
    return this.first("non_field_errors") ?? this.first("detail")
  }
}

type Query = Record<string, string | number | boolean | null | undefined>

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE"
  body?: unknown
  query?: Query
  /** Send the access token and retry once after a refresh on 401. Default true. */
  auth?: boolean
  signal?: AbortSignal
}

let onSessionExpired: () => void = () => {}
/** The auth provider registers a callback to clear its state when refresh fails. */
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler
}

function buildUrl(path: string, query?: Query): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value))
  }
  const qs = params.toString()
  return `${BASE_URL}${path}${qs ? `?${qs}` : ""}`
}

async function parseError(response: Response): Promise<ApiError> {
  let body: Partial<ApiErrorBody> = {}
  try {
    body = await response.json()
  } catch {
    // Non-JSON error (e.g. proxy failure): fall through to the generic message.
  }
  const error = body.error
  return new ApiError(
    response.status,
    error?.code ?? "error",
    error?.message ?? "Something went wrong. Please try again.",
    error?.details,
  )
}

let refreshInFlight: Promise<boolean> | null = null

/** Exchange the refresh token for a new pair. Concurrent callers share one request. */
export function refreshSession(): Promise<boolean> {
  refreshInFlight ??= (async () => {
    const refresh = tokenStore.getRefresh()
    if (!refresh) return false
    try {
      const response = await fetch(buildUrl("/auth/token/refresh/"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      })
      if (!response.ok) {
        tokenStore.clear()
        return false
      }
      tokenStore.set(await response.json())
      return true
    } catch {
      return false // network problem: keep the refresh token for a later attempt
    }
  })().finally(() => {
    refreshInFlight = null
  })
  return refreshInFlight
}

async function send(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: "application/json" }
  if (options.body !== undefined) headers["Content-Type"] = "application/json"
  const access = tokenStore.getAccess()
  if (options.auth !== false && access) headers.Authorization = `Bearer ${access}`

  return fetch(buildUrl(path, options.query), {
    method: options.method ?? "GET",
    headers,
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  })
}

export async function api<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response: Response
  try {
    response = await send(path, options)
    if (response.status === 401 && options.auth !== false && tokenStore.getRefresh()) {
      if (await refreshSession()) {
        response = await send(path, options)
      } else if (!tokenStore.getRefresh()) {
        onSessionExpired()
      }
    }
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error
    throw new ApiError(0, "network_error", "Cannot reach the server. Check your connection.")
  }

  if (!response.ok) throw await parseError(response)
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}
