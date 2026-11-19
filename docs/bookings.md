# Bookings & capacity

## Lifecycle

```
            create (seats held)            verified payment (phase 5)
  ──────────────────────────▶ pending ───────────────────────────▶ confirmed
                                │  │                                   │
             hold lapses (15 min)│  │ traveller or admin cancels        │ admin cancels (reason required)
                                ▼  ▼                                   ▼
                            expired  cancelled ◀──────────────────────┘
```

- **pending**: seats are held until `expires_at` (`BOOKING_HOLD_MINUTES`, default 15).
- **confirmed**: only the payment service may confirm (phase 5). Nothing in the API lets a
  client mark a booking as paid.
- **expired / cancelled**: seats return to sale. Bookings are never deleted.

Every transition is written to `BookingEvent` (who, when, from, to, note). The admin API
shows this history.

## Product decisions applied

| Decision (PRD §25) | Choice |
|--------------------|--------|
| Pending reservation TTL | 15 minutes, configurable with `BOOKING_HOLD_MINUTES` |
| Minimum group size unmet | Admin decides. After the cutoff, departures below their minimum show `needs_decision: true` in the admin API (`GET /admin/departures/?needs_decision=true`). Nothing is cancelled automatically. |
| Cancellation / refunds | Still open. Travellers can cancel unpaid holds; paid bookings are cancelled by an admin until the refund workflow lands in phase 5. |

## Pricing

- `unit_price` is copied from the departure (price override or adventure base price) when
  the booking is created. `total_amount = unit_price × participant_count`, enforced by a
  database check constraint. Later catalog price changes never alter existing bookings.
- Amounts are `Decimal` with an explicit ISO currency. Any price or total sent by the
  client is ignored.
- `POST /bookings/quote/` returns the same calculation without reserving seats, so the
  booking page can show a server-calculated, itemised price.

## Capacity and concurrency (AC-06)

1. `create_booking` opens a transaction and locks the departure row
   (`SELECT … FOR UPDATE`).
2. Lapsed holds on that departure are expired first, so availability is always current
   even if the periodic sweeper is late.
3. Status, cutoff, publication, seat count, per-booking limits and the groups-only rule are
   checked against the locked row.
4. The booking is written and `Departure.seats_reserved` is incremented in the same
   transaction.

Locks are always taken in the order departure → booking, so confirm, cancel and expiry
cannot deadlock each other. The database constraint `seats_reserved <= capacity` is the
final guard. `test_concurrent_requests_cannot_oversell` starts 8 simultaneous bookings for
3 seats and asserts exactly 3 succeed; it runs on PostgreSQL (CI and Docker) and is skipped on
SQLite, which has no row locks.

The Celery beat service runs `bookings.expire_pending_bookings` every minute to release
lapsed holds on departures nobody is currently booking.

## Rules

| Rule | Error |
|------|-------|
| Departure open, before cutoff, not started, adventure and destination published | 409 `departure_unavailable` |
| Enough seats left | 409 `not_enough_seats` |
| One unpaid hold per traveller per departure | 409 `pending_booking_exists` |
| At most `MAX_PARTICIPANTS_PER_BOOKING` (20) and the adventure's max group size | 400 |
| Groups-only adventures need at least the minimum party size | 400 |
| Policy acknowledgement required; every participant needs a full name | 400 |

## API

| Endpoint | Access | Purpose |
|----------|--------|---------|
| `GET /bookings/?scope=upcoming\|past\|cancelled` | Authenticated | Own bookings |
| `POST /bookings/` | Authenticated | Create (departure, participants, policy_accepted) |
| `GET /bookings/{id}/` | Owner | Detail; other users' bookings return 404 |
| `POST /bookings/{id}/cancel/` | Owner | Cancel an unpaid hold |
| `POST /bookings/quote/` | Public | Price a party size, no reservation |
| `GET /admin/bookings/` | Admin | Search by reference, name, email, phone; filter by status/departure |
| `GET /admin/bookings/{id}/` | Admin | Includes traveller contact and history |
| `POST /admin/bookings/{id}/cancel/` | Admin | Cancel pending or confirmed; `reason` required |

Booking creation is throttled to 30 per hour per user.

## Participant data

Only what running the trip needs: full name (required), nationality and date of birth
(optional). The lead traveller is the first participant. Passport numbers and health
information are not collected.
