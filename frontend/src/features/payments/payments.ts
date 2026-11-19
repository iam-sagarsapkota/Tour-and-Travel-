import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { PaymentProvider, PaymentRedirect, VerifyResult } from "@/types/api"

export function useProviders() {
  return useQuery({
    queryKey: ["payment-providers"],
    queryFn: ({ signal }) => api<PaymentProvider[]>("/payments/providers/", { signal }),
    staleTime: 10 * 60 * 1000,
  })
}

export function useInitiatePayment() {
  return useMutation({
    mutationFn: (input: { booking: string; provider: string }) =>
      api<PaymentRedirect>("/payments/initiate/", { method: "POST", body: input }),
  })
}

/** Ask our server to check the attempt with the provider. Safe to call repeatedly. */
export function useVerifyPayment(attempt: string, params: Record<string, string>) {
  const client = useQueryClient()
  return useQuery({
    queryKey: ["payment-verify", attempt],
    queryFn: async ({ signal }) => {
      const result = await api<VerifyResult>("/payments/verify/", {
        method: "POST",
        body: { attempt, params },
        signal,
      })
      client.invalidateQueries({ queryKey: ["booking", result.payment.booking_id] })
      client.invalidateQueries({ queryKey: ["bookings"] })
      return result
    },
    // Keep asking while the provider still reports the payment as in progress.
    refetchInterval: (query) => {
      const status = query.state.data?.attempt.status
      return status === "initiated" || status === "processing" ? 5000 : false
    },
    retry: 1,
  })
}

/**
 * Leave for the gateway. eSewa expects a form POST (signed fields); Khalti gives a URL.
 * The form is built from server-provided values only.
 */
export function goToGateway(redirect: PaymentRedirect, doc: Document = document) {
  if (redirect.method === "GET") {
    window.location.assign(redirect.url)
    return
  }
  const form = doc.createElement("form")
  form.method = "POST"
  form.action = redirect.url
  form.style.display = "none"
  for (const [name, value] of Object.entries(redirect.fields)) {
    const input = doc.createElement("input")
    input.type = "hidden"
    input.name = name
    input.value = value
    form.appendChild(input)
  }
  doc.body.appendChild(form)
  form.submit()
}
