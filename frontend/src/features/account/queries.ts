import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type {
  Paginated,
  Payment,
  Session,
  SiteSettings,
  Tokens,
  TravellerDashboard,
  User,
  UserProfile,
} from "@/types/api"

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: ({ signal }) => api<TravellerDashboard>("/dashboard/", { signal }),
  })
}

export function usePaymentHistory() {
  return useQuery({
    queryKey: ["payments", "history"],
    queryFn: ({ signal }) =>
      api<Paginated<Payment>>("/payments/history/", { query: { page_size: 50 }, signal }),
  })
}

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: ({ signal }) => api<Session[]>("/auth/sessions/", { signal }),
  })
}

export function useSiteSettings() {
  return useQuery({
    queryKey: ["site"],
    queryFn: ({ signal }) => api<SiteSettings>("/site/", { auth: false, signal }),
    staleTime: 10 * 60 * 1000,
  })
}

export interface ProfileInput {
  full_name?: string
  profile?: Partial<UserProfile>
}

export function useUpdateProfile() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: ProfileInput) => api<User>("/auth/me/", { method: "PATCH", body: input }),
    onSuccess: () => client.invalidateQueries({ queryKey: ["dashboard"] }),
  })
}

export function useChangePassword() {
  return useMutation({
    mutationFn: (input: {
      current_password: string
      new_password: string
      new_password_confirm: string
    }) => api<{ tokens: Tokens }>("/auth/password/change/", { method: "POST", body: input }),
  })
}

export function useResendVerification() {
  return useMutation({
    mutationFn: () => api<void>("/auth/verify-email/resend/", { method: "POST" }),
  })
}

export function useSignOutEverywhere() {
  return useMutation({
    mutationFn: () => api<void>("/auth/sessions/", { method: "DELETE" }),
  })
}
