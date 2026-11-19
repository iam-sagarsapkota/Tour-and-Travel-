import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query"

import { api } from "@/lib/api"
import type { Booking, Paginated, Quote } from "@/types/api"

export type BookingScope = "upcoming" | "past" | "cancelled"

export interface ParticipantInput {
  full_name: string
  nationality?: string
}

export interface CreateBookingInput {
  departure: string
  participants: ParticipantInput[]
  policy_accepted: boolean
}

/** Server-calculated price for a party size. Nothing is reserved. */
export function useQuote(departure: string, participantCount: number) {
  return useQuery({
    queryKey: ["quote", departure, participantCount],
    queryFn: ({ signal }) =>
      api<Quote>("/bookings/quote/", {
        method: "POST",
        body: { departure, participant_count: participantCount },
        signal,
      }),
    enabled: Boolean(departure) && participantCount > 0,
    placeholderData: keepPreviousData,
  })
}

export function useMyBookings(scope: BookingScope) {
  return useQuery({
    queryKey: ["bookings", scope],
    queryFn: ({ signal }) =>
      api<Paginated<Booking>>("/bookings/", { query: { scope, page_size: 50 }, signal }),
  })
}

export function useBooking(id: string) {
  return useQuery({
    queryKey: ["booking", id],
    queryFn: ({ signal }) => api<Booking>(`/bookings/${encodeURIComponent(id)}/`, { signal }),
  })
}

export function useCreateBooking() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (input: CreateBookingInput) =>
      api<Booking>("/bookings/", { method: "POST", body: input }),
    onSuccess: (booking) => {
      client.setQueryData(["booking", booking.id], booking)
      // Seat counts changed: refresh bookings and catalog availability.
      client.invalidateQueries({ queryKey: ["bookings"] })
      client.invalidateQueries({ queryKey: ["event"] })
      client.invalidateQueries({ queryKey: ["events"] })
    },
  })
}

export function useCancelBooking() {
  const client = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api<Booking>(`/bookings/${encodeURIComponent(id)}/cancel/`, { method: "POST" }),
    onSuccess: (booking) => {
      client.setQueryData(["booking", booking.id], booking)
      client.invalidateQueries({ queryKey: ["bookings"] })
      client.invalidateQueries({ queryKey: ["event"] })
      client.invalidateQueries({ queryKey: ["events"] })
    },
  })
}
