# Delivery phases

The PRD (`Tour_Travel_System_PRD_ReactBits.pdf`, v1.1) is delivered as seven phases.
Each phase is built test-first, pushed to the `development` branch when its tests
pass, and merged to `main` once reviewed.

| # | Phase | PRD sections | Status |
|---|-------|--------------|--------|
| 1 | Foundation & identity | 2, 3, 4.1, 12, 13 (Identity), 15, 17 | **Done** |
| 2 | Catalog & departures (backend) | 5, 6.1, 9.2, 13 (Catalog, Scheduling), 20 | **Done** |
| 3 | Frontend foundation & public site | 4.2, 5, 10, 11 | **Done** |
| 4 | Bookings & capacity | 6.2, 6.3, 13 (Booking) | Next |
| 5 | Payments | 7, 13 (Payments) | Planned |
| 6 | Dashboards & notifications | 8, 9, 14, 13 (Operations) | Planned |
| 7 | Hardening & release | 16, 17, 18, 19 | Planned |

Reviews, wishlist, coupons, maps, itinerary PDF and advanced reports are the PRD's
post-MVP "Phase 2" release and follow after phase 7.

## Phase 1 — Foundation & identity (done)

- Repository layout, Django 6.1 project with split settings (base/development/production/test).
- **Custom user model** (`accounts.User`) created before the first migration: UUID primary
  key, email **or** phone (database check constraint), role (user / admin / super admin),
  verification timestamps, auto-created `UserProfile`.
- Auth API under `/api/v1/auth/`: register, login (email or phone), token refresh with
  rotation, logout, me, password change, password reset request/confirm.
- Admin user management under `/api/v1/admin/users/` with role and object-level permissions.
- Consistent error envelope, throttling, OpenAPI docs, health/readiness endpoints.
- Docker Compose (PostgreSQL, Redis, backend, Celery worker), CI workflow, 89 backend tests.

Not in this phase (deliberately): email/phone **verification** flows and moving email
sending to Celery — both land with notifications in phase 6. Phone-only accounts cannot
self-serve a password reset until an SMS channel exists; an admin can reset it for them.

## Phase 2 — Catalog & departures (backend, done)

- Models: Destination, AdventureCategory, Adventure, AdventureImage, ItineraryDay, Departure,
  with database constraints (positive price/duration/capacity, seats reserved ≤ capacity,
  end date ≥ start date, unique itinerary day).
- Public listing `GET /events/` with search, filters, sorting and pagination; authenticated
  detail `GET /events/{slug}/`; public destinations and categories.
- Admin API for destinations, categories, adventures (draft → published → archived),
  gallery images and departures, all admin-only.
- Validated image uploads, `seed_catalog` demo data, 96 new tests (185 total).
- Details: [catalog.md](catalog.md).

Not in this phase: bookings do not exist yet, so `seats_reserved` and `popularity` stay at
zero until phase 4. Route maps are a stored URL only; map rendering is post-MVP.

## Phase 3 — Frontend foundation & public site (done)

- React + Vite + TypeScript, Tailwind, shadcn/ui, brand tokens, Manrope/Inter.
- React Bits: Split Text (hero), Spotlight Card (featured events), Animated Content
  (scroll reveal), lazy-loaded and reduced-motion aware.
- Login and registration (email or phone), session restore, token refresh, logout.
- Guest → `/register?next=/events/{slug}` → back to the event, with `next` validated.
- Homepage, event listing with URL-based filters and pagination, event detail,
  destination directory and detail; loading, empty and error states throughout.
- Frontend service in Docker Compose, production image on unprivileged Nginx,
  frontend CI job, 46 frontend tests.
- Details: [frontend.md](frontend.md).

Not in this phase: no booking button yet (phase 4); remaining React Bits components listed
in frontend.md; SEO prerendering is evaluated in phase 7.

## Phase 4 — Bookings & capacity

Booking and BookingParticipant, server-side Decimal pricing, human-readable booking
reference, `select_for_update` capacity locking, pending-reservation expiry (Celery beat),
cancellation rules, concurrency tests on PostgreSQL, booking flow UI.

## Phase 5 — Payments

Payment, PaymentAttempt, Refund; eSewa and Khalti (sandbox) with server-side verification;
card provider behind the same interface once eligibility is confirmed; idempotent
callbacks, reconciliation, refund workflow, payment UI.

## Phase 6 — Dashboards & notifications

User dashboard (bookings, payments, profile, security), admin dashboard (KPIs, charts,
management modules), AuditLog, SiteSettings, transactional email via Celery with retry,
contact verification.

## Phase 7 — Hardening & release

Playwright end-to-end flows, security review, performance and SEO work,
`docker-compose.prod.yml` with Nginx/Gunicorn, backup/restore procedure, complete docs set.

## Decisions needed from the product owner

These come from PRD section 25 and block the phases noted:

| Decision | Needed by |
|----------|-----------|
| Pending reservation TTL (how long unpaid seats are held) | Phase 4 |
| Minimum group size behaviour when unmet | Phase 4 |
| Cancellation / refund policy | Phase 4–5 |
| International card provider (Nepal merchant eligibility) | Phase 5 |
| Currency / FX display rules | Phase 5 |
| Which contact channel must be verified before booking | Phase 6 |
