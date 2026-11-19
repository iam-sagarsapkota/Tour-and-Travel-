/** Shapes returned by the backend API (see /api/v1/docs/). Money arrives as decimal strings. */

export type Role = "user" | "admin" | "super_admin"

export interface UserProfile {
  date_of_birth: string | null
  nationality: string
  address: string
  emergency_contact_name: string
  emergency_contact_phone: string
  trip_reminders: boolean
}

export interface User {
  id: string
  full_name: string
  email: string | null
  phone: string | null
  role: Role
  email_verified: boolean
  phone_verified: boolean
  date_joined: string
  profile: UserProfile
}

export interface Tokens {
  access: string
  refresh: string
}

export interface AuthResponse {
  user: User
  tokens: Tokens
}

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type Difficulty = "easy" | "moderate" | "difficult" | "extreme"
export type ActivityType = "trekking" | "hiking" | "other"

export interface DestinationSummary {
  name: string
  slug: string
  region: string
}

export interface CategorySummary {
  name: string
  slug: string
}

export interface Category extends CategorySummary {
  id: string
  description: string
}

export interface NextDeparture {
  id: string
  start_date: string
  end_date: string
  seats_available: number
}

export interface EventCard {
  id: string
  title: string
  slug: string
  summary: string
  destination: DestinationSummary
  category: CategorySummary | null
  activity_type: ActivityType
  cover_image: string | null
  difficulty: Difficulty
  duration_days: number
  starting_price: string
  currency: string
  next_departure: NextDeparture | null
  has_availability: boolean
  is_featured: boolean
}

export interface EventImage {
  id: string
  image: string
  alt_text: string
  display_order: number
}

export interface ItineraryDay {
  day_number: number
  title: string
  description: string
  overnight_location: string
  altitude_m: number | null
}

export interface Departure {
  id: string
  start_date: string
  end_date: string
  booking_cutoff: string
  price: string
  capacity: number
  seats_available: number
  min_participants: number
  status: "open" | "closed" | "cancelled" | "completed"
  is_bookable: boolean
}

export interface EventDetail extends EventCard {
  description: string
  images: EventImage[]
  distance_km: string | null
  max_elevation_m: number | null
  start_point: string
  end_point: string
  route_summary: string
  route_map_url: string
  base_price: string
  min_participants: number
  max_group_size: number | null
  solo_friendly: boolean
  inclusions: string[]
  exclusions: string[]
  accommodation: string
  transportation: string
  meals: string
  equipment: string
  safety_guidance: string
  meeting_point: string
  organizer: string
  cancellation_policy: string
  itinerary: ItineraryDay[]
  departures: Departure[]
  related: EventCard[]
}

export interface Destination {
  id: string
  name: string
  slug: string
  region: string
  short_description: string
  cover_image: string | null
  best_season: string
  event_count: number
}

export interface DestinationDetail extends Omit<Destination, "event_count"> {
  description: string
  seasonal_guidance: string
  attractions: string
  permit_info: string
  events: EventCard[]
}

/** Error envelope produced by the API for every failure. */
export interface ApiErrorBody {
  error: {
    code: string
    message: string
    details: Record<string, string[] | string> | null
  }
}

export type BookingStatus = "pending" | "confirmed" | "cancelled" | "expired"

export interface BookingParticipant {
  full_name: string
  nationality: string
  date_of_birth: string | null
  is_lead: boolean
}

export interface Booking {
  id: string
  reference: string
  status: BookingStatus
  departure: { id: string; start_date: string; end_date: string; status: Departure["status"] }
  adventure: {
    title: string
    slug: string
    cover_image: string | null
    duration_days: number
    destination: string
    cancellation_policy: string
  }
  participant_count: number
  unit_price: string
  total_amount: string
  currency: string
  participants: BookingParticipant[]
  expires_at: string | null
  confirmed_at: string | null
  cancelled_at: string | null
  cancellation_reason: string
  created_at: string
  can_cancel: boolean
  payment: { status: PaymentStatus; provider: string; paid_at: string | null } | null
}

export type PaymentStatus =
  | "pending"
  | "processing"
  | "successful"
  | "failed"
  | "cancelled"
  | "refunded"
  | "partially_refunded"

export type AttemptStatus =
  | "initiated"
  | "processing"
  | "successful"
  | "failed"
  | "cancelled"
  | "expired"
  | "refunded"
  | "partially_refunded"

export interface PaymentProvider {
  code: "esewa" | "khalti"
  name: string
}

/** Where to send the browser. POST means submit `fields` as a form to `url`. */
export interface PaymentRedirect {
  attempt: string
  method: "GET" | "POST"
  url: string
  fields: Record<string, string>
}

export interface PaymentAttempt {
  id: string
  provider: string
  reference: string
  amount: string
  currency: string
  status: AttemptStatus
  gateway_status: string
  gateway_transaction_id: string
  created_at: string
  completed_at: string | null
}

export interface Payment {
  id: string
  booking_id: string
  booking_reference: string
  booking_status: BookingStatus
  adventure: string
  amount: string
  currency: string
  status: PaymentStatus
  provider: string
  gateway_reference: string
  paid_at: string | null
  created_at: string
  attempts: PaymentAttempt[]
}

export interface VerifyResult {
  attempt: PaymentAttempt
  payment: Payment
}

export interface Quote {
  departure: string
  participant_count: number
  unit_price: string
  total_amount: string
  currency: string
  seats_available: number
  is_bookable: boolean
}

export interface TravellerDashboard {
  counts: { total: number; upcoming: number; completed: number; cancelled: number }
  total_spent: string
  currency: string
  upcoming: Booking[]
  pending_payment: Booking[]
  recommendations: EventCard[]
}

export interface Session {
  id: number
  created_at: string
  expires_at: string
}

export interface SiteSettings {
  site_name: string
  support_email: string
  support_phone: string
  announcement: string
  announcement_active: boolean
}
