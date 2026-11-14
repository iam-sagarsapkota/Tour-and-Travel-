# Authentication & authorization

## User model

`apps.accounts.User` is a custom model (set as `AUTH_USER_MODEL` before the first migration).

| Field | Notes |
|-------|-------|
| `id` | UUID primary key, safe to expose |
| `full_name` | Required |
| `email` | Unique, stored lowercase, `NULL` when absent |
| `phone` | Unique, stored in E.164 (`+9779812345678`), `NULL` when absent |
| `role` | `user`, `admin`, `super_admin` — the single source of truth for privilege |
| `is_staff`, `is_superuser` | Derived from `role` on every save; never set directly |
| `is_active` | Accounts are deactivated, never deleted |
| `email_verified_at`, `phone_verified_at` | Set by the verification flows (phase 6) |

A database check constraint guarantees every user has an email or a phone number.
A bare 10-digit Nepali mobile number (`98XXXXXXXX`) is normalized to `+977…`; other numbers
must include a country code. A `UserProfile` row is created automatically for each user.

## Token model

JWT via Simple JWT, sent as `Authorization: Bearer <access>`.

- Access token: 15 minutes. Refresh token: 7 days. Both configurable by environment variable.
- Refresh tokens **rotate** on every use and the previous one is blacklisted.
- Logout blacklists the submitted refresh token.
- Changing or resetting a password, or deactivating an account, revokes every session:
  refresh tokens are blacklisted and access tokens stop validating because each token
  carries a hash of the password it was issued under (`CHECK_REVOKE_TOKEN`).

**CSRF:** tokens travel in the `Authorization` header, not in cookies, so the API is not
exposed to CSRF and API views do not use session authentication. The trade-off is that the
frontend must keep tokens out of reach of injected scripts: hold the access token in memory
and treat XSS prevention as the primary control. If the refresh token is later moved into an
`HttpOnly` cookie, CSRF protection must be added to the refresh and logout endpoints.

## Endpoints (`/api/v1/auth/`)

| Method & path | Access | Purpose |
|---------------|--------|---------|
| `POST register/` | Public | Create account; returns user + tokens |
| `POST login/` | Public | `identifier` (email or phone) + `password` |
| `POST token/refresh/` | Public | Rotate refresh token |
| `POST logout/` | Authenticated | Revoke a refresh token |
| `GET, PATCH me/` | Authenticated | Own account; name and profile are editable |
| `POST password/change/` | Authenticated | Requires current password; returns new tokens |
| `POST password/reset/` | Public | Emails a single-use link; same response for unknown emails |
| `POST password/reset/confirm/` | Public | `uid`, `token`, new password |

Admin user management lives at `/api/v1/admin/users/` (list, search, filter, create, edit,
deactivate). Admins manage regular users; only a super admin can change roles or modify
admin accounts. `DELETE` deactivates the account.

## Throttling

| Scope | Limit |
|-------|-------|
| Login | 10 / minute per IP |
| Registration | 20 / hour per IP |
| Password change / reset | 5 / hour |
| Token refresh | 60 / minute |

Login failures return the same `invalid_credentials` error whether the account is unknown,
inactive, or the password is wrong.

## Error format

```json
{"error": {"code": "validation_error", "message": "Invalid input.", "details": {"email": ["..."]}}}
```
