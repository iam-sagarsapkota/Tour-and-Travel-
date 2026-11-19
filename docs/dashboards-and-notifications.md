# Dashboards, notifications and operations

## Traveller account area (`/dashboard`)

| Page | Contents |
|------|----------|
| Overview | Upcoming and completed trip counts, total paid, bookings waiting for payment (with *Pay now*), upcoming trips, recommendations (published, bookable, not already booked) |
| Bookings | Upcoming / past / cancelled tabs; detail with travellers, price, policy, payment and cancellation |
| Payments | Every payment with provider, provider reference and status |
| Profile & security | Name, nationality, emergency contact, trip-reminder preference; email verification status and resend; password change (signs out other devices); signed-in devices and *sign out everywhere* |

API: `GET /dashboard/`, `GET /payments/history/`, `GET/DELETE /auth/sessions/`,
`POST /auth/verify-email/`, `POST /auth/verify-email/resend/`, `GET /notifications/`,
`POST /notifications/read-all/`.

Email or phone changes are not self-service yet; they need verification of the new channel.

## Admin area (`/admin`, admins and super admins)

| Section | What admins can do |
|---------|--------------------|
| Dashboard | KPIs, monthly bookings and revenue, destination popularity, top adventures, recent bookings, alerts |
| Bookings | Search and filter; expand for travellers and history; cancel with a reason (emailed to the traveller) |
| Payments | Filter by status / needs-attention; attempts and provider log; re-check with the provider; resolve with a note |
| Departures | Schedule; close, reopen or cancel (travellers emailed); filter those below their minimum |
| Adventures | Create drafts; edit details, inclusions and itinerary; publish, unpublish, archive |
| Users | Search, filter by role/status, deactivate and reactivate (super admin needed for admin accounts) |
| Inbox | Contact-form messages; mark handled |
| Audit log | Read-only trail of admin changes |
| Settings | Support email/phone and the site announcement banner |

Destinations, categories and photo uploads are managed in Django admin
(`/django-admin/`) for now; their APIs exist under `/api/v1/admin/`.

The browser guard is a convenience. Every `/api/v1/admin/` endpoint checks the role on the
server.

### KPI definitions (`GET /admin/dashboard/?months=1..24`)

| KPI | Definition |
|-----|-----------|
| Verified revenue | Sum of payments a provider confirmed (`successful`), by payment date |
| Bookings | Bookings created in the period (any status) |
| Booking conversion | confirmed ÷ (confirmed + cancelled + expired), bookings created in the period; pending ones are undecided and excluded |
| Payment success rate | successful ÷ settled attempts (successful, failed, cancelled, expired) |
| Upcoming departures | Open or closed departures that haven't started |
| Active users | Active accounts that signed in during the last 30 days |

Monthly series use calendar months in Nepal time (Asia/Kathmandu). Alerts: payments
flagged for attention, departures past their cutoff below the minimum, and open departures
at 80% capacity or more.

### Charts

Single-series column and bar charts in the brand forest green, drawn as inline SVG with no
chart library. Bars are capped at 24px with rounded data-ends; every bar has a hover and
keyboard-focus tooltip; every chart has a *Show table* view; count charts use whole-number
ticks; empty periods say so instead of drawing an empty axis.

React Bits *Count Up* was not used for KPI tiles: it requires the `motion` library, which
would add a second animation library next to GSAP (PRD §10.1), and plain numbers read faster
on an operational dashboard.

## Notifications

Email via Celery. Each message is stored as a `Notification`, then sent after the database
transaction commits, so an email never goes out for a change that was rolled back.

| Kind | Sent when |
|------|-----------|
| welcome | Registration |
| email_verification | Registration with an email; resend from the profile |
| password_reset | Reset requested |
| booking_confirmed | Payment verified and booking confirmed (acts as the receipt) |
| payment_failed | A payment attempt failed or expired |
| payment_needs_review | Money received but the booking couldn't be confirmed |
| booking_cancelled | Cancelled by the traveller or an admin (includes the reason) |
| booking_expired | Seat hold lapsed without payment (not sent if a payment is in flight) |
| departure_changed | Admin changed the dates or cancelled the departure |
| trip_reminder | Daily at 08:45 Nepal time for trips starting in `TRIP_REMINDER_DAYS` (3); opt-out in profile |

- **No duplicates:** each event carries a dedupe key, so repeated payment callbacks or
  re-runs of the reminder job send one email.
- **Retries:** SMTP and network errors retry with exponential backoff (30 s to 15 min,
  5 tries) and are then marked `failed`. Other errors fail immediately.
- **Single-use links:** verification and reset emails have their body removed from the
  database once sent, and the in-app list never shows them.
- **Phone-only accounts:** messages are kept in-app with status `skipped`. SMS and
  WhatsApp are future channels.
- **Design:** responsive branded HTML plus a plain-text version. Values are autoescaped.

In development, emails print to the backend and Celery console unless `EMAIL_BACKEND` is set.

## Audit log

`AuditLog` records who changed what in the admin area: catalog create/update/publish/archive,
departure changes, user edits and deactivation, booking cancellations, payment re-checks
and resolutions, contact handling and site settings. Each entry has field-level
before/after values, a note where given, and the client IP. Passwords are never recorded
(only "changed"). Entries can't be edited or deleted. API: `GET /admin/audit-logs/`.

## Site settings and contact

- `GET /site/` (public) and `PATCH /admin/site-settings/` (admin): site name, support email
  and phone, announcement banner.
- `POST /contact/` (public, 10 per hour per IP) and `/admin/contact-inquiries/` (list,
  `POST {id}/handle/`).
