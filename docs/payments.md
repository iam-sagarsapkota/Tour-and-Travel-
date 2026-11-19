# Payments

## Providers

| Provider | Status | Enabled by |
|----------|--------|------------|
| eSewa (ePay v2) | Built; sandbox on by default in development | `ESEWA_ENABLED`, `ESEWA_PRODUCT_CODE`, `ESEWA_SECRET_KEY` |
| Khalti (KPG-2 web checkout) | Built; off until a key is set | `KHALTI_SECRET_KEY` (sandbox key from test-admin.khalti.com) |
| International cards | Not built | Waiting for a provider decision (Nepal merchant eligibility) |

Sources used (November 2026): https://developer.esewa.com.np/pages/Epay and
https://docs.khalti.com/khalti-epayment/.

The eSewa signing rule was checked against the live sandbox: a correctly signed form is
accepted, a wrongly signed one is rejected with `ES104 Invalid payload signature`. The
sample signatures printed on eSewa's docs page do not match its own key and format and
should be ignored.

## Flow

```
booking (pending) ──POST /payments/initiate/──▶ PaymentAttempt + hold extended (20 min)
        │                                          │
        │                       eSewa: auto-submitted signed form   Khalti: redirect to payment_url
        ▼                                          ▼
 browser returns to /payments/<provider>/<attempt>/<outcome>  (frontend)
        │
        └─POST /payments/verify/──▶ server asks the provider's API ──▶ apply result once
                                     (eSewa status API / Khalti lookup)
```

- **The browser is never trusted.** Return parameters are only logged. eSewa's signed
  `data` is checked and recorded, but the decision always comes from the status API
  (eSewa) or lookup API (Khalti), called with our own stored reference and amount.
- **Amounts must match.** If the provider reports a different amount, the attempt fails,
  the booking is not confirmed and the payment is flagged.
- **Idempotent.** Results are applied under row locks; a settled attempt is not checked
  again. Duplicate callbacks, page refreshes and reconciliation racing the browser confirm
  a booking once.
- **Reconciliation.** Celery beat runs `payments.reconcile_open_attempts` every 5 minutes
  for attempts 5 minutes to 48 hours old whose browser never came back (eSewa: "if a
  response is not received within five minutes, use the status check API").
- **Audit trail.** Every request, browser return, status check and status change is kept in
  `PaymentLog`. Payments, attempts and logs cannot be edited or deleted, by admins or
  through Django admin. Secret keys are never logged.

## Status mapping

| eSewa | Khalti | Attempt | Notes |
|-------|--------|---------|-------|
| COMPLETE | Completed | successful | Only success value |
| PENDING, AMBIGUOUS | Pending | processing | Keep checking |
| — | Initiated | initiated | Traveller hasn't paid yet |
| NOT_FOUND | Expired | expired | Treated as processing for the first 30 min (`PAYMENT_ATTEMPT_GRACE_MINUTES`) |
| CANCELED | User canceled | cancelled | |
| FULL_REFUND / PARTIAL_REFUND | Refunded / Partially Refunded | refunded / partially_refunded | Flagged for admin |

Payment status follows its attempts: `pending`, `processing`, `successful`, `failed`,
`cancelled`, `refunded`, `partially_refunded`.

## Failure recovery

| Situation | What happens |
|-----------|--------------|
| Paid after the seat hold lapsed, seats still free | Seats re-reserved, booking confirmed |
| Paid after the hold lapsed, seats sold out (or booking cancelled) | Payment successful, booking not confirmed, payment flagged: refund |
| Paid twice (two tabs / two providers) | Second success recorded and flagged: refund one |
| Provider unreachable at start | Attempt marked failed, traveller sees an error and can retry |
| Provider unreachable while verifying | Attempt stays open; the return page polls and reconciliation retries |

Flagged payments appear at `GET /admin/payments/?needs_attention=true`. After handling one
(for example refunding it in the provider's merchant portal), an admin clears the flag with
`POST /admin/payments/{id}/resolve/` and a note, which is logged.

Refund *workflows* (traveller requests, approval, provider refund APIs) are in the PRD's
post-MVP Phase 2 and depend on the cancellation/refund policy, which is still undecided.

## API

| Endpoint | Access | Purpose |
|----------|--------|---------|
| `GET /payments/providers/` | Authenticated | Enabled payment methods |
| `POST /payments/initiate/` | Booking owner | `{booking, provider}` → `{attempt, method, url, fields}` |
| `POST /payments/verify/` | Booking owner | `{attempt, params}`; checks with the provider |
| `GET /payments/history/` | Authenticated | Own payments with attempts |
| `GET /admin/payments/` | Admin | Filter `status`, `provider`, `needs_attention`; search references |
| `POST /admin/payments/{id}/reconcile/` | Admin | Ask the provider again (also detects refunds) |
| `POST /admin/payments/{id}/resolve/` | Admin | Clear the attention flag with a note |

## Configuration

| Setting | Default | Meaning |
|---------|---------|---------|
| `PAYMENT_HOLD_MINUTES` | 20 | Seat hold extension when payment starts |
| `PAYMENT_ATTEMPT_GRACE_MINUTES` | 30 | Before this age, "expired/not found" is not final |
| `ESEWA_FORM_URL`, `ESEWA_STATUS_URL` | eSewa sandbox | Production: `https://epay.esewa.com.np/api/epay/main/v2/form`, `https://esewa.com.np/api/epay/transaction/status/` |
| `KHALTI_BASE_URL` | `https://dev.khalti.com/api/v2/` | Production: `https://khalti.com/api/v2/` |

`config.settings.production` refuses to start if eSewa uses the `EPAYTEST` merchant or
sandbox URLs, or Khalti points at `dev.khalti.com`.

## Testing with sandboxes

1. `docker compose exec backend python manage.py seed_catalog` adds **Sandbox Payment Test
   Walk (demo)** at NPR 100, inside Khalti's sandbox limit of NPR 10-200.
2. Log in, book it, and choose a payment method on the booking page.
3. **eSewa test wallet:** ID `9711111111` (or …112, …113), password `Nepal@123`,
   MPIN `1122`, token `123456`. The sandbox login shows a reCAPTCHA, so this step is manual.
4. **Khalti:** create a sandbox merchant at https://test-admin.khalti.com/#/join/merchant,
   put its `live_secret_key` in `KHALTI_SECRET_KEY`, restart the backend. Test wallet IDs
   `9800000000`-`9800000005`, MPIN `1111`, OTP `987654`.

Automated tests replace all provider HTTP calls with scripted answers, and the HTTP helper
itself is tested against a local server. No test touches a real gateway.
