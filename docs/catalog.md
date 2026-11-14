# Catalog & departures

## Model

```
Destination 1 ──< Adventure >── 1 AdventureCategory
                     │
                     ├──< AdventureImage
                     ├──< ItineraryDay      (unique day number per adventure)
                     └──< Departure         (scheduled instance)
```

- **Adventure** is the reusable product; **Departure** is one scheduled run with its own
  dates, capacity, minimum participants, booking cutoff, optional price override and status.
- Destinations, adventures and departures are never deleted through the API. They are
  archived or cancelled, because bookings and payments must stay traceable
  (`Adventure → Destination` and `Departure → Adventure` use `PROTECT`).
- Money is `DecimalField` with an explicit ISO currency on the adventure (default `NPR`).
- All externally exposed ids are UUIDs; public URLs use slugs.

### Derived / cached fields

| Field | Maintained by | Purpose |
|-------|---------------|---------|
| `Departure.seats_reserved` | Booking service (phase 4), under a row lock | Seats held by pending + confirmed bookings. A check constraint keeps it ≤ `capacity`. |
| `Adventure.popularity` | Booking service (phase 4) | Sort key for "most popular". |

Neither can be written through the API.

## What "bookable" means

A departure is bookable when its status is `open`, the booking cutoff has not passed, it has
not started, seats remain, and its adventure and destination are published. The rule lives in
one place (`apps/departures/models.py`: `bookable_q`, `DepartureQuerySet.bookable`,
`Departure.is_bookable`) and feeds the listing's `starting_price`, `next_departure` and
`has_availability`.

`starting_price` is the cheapest per-person price among bookable departures, or the
adventure's base price when none is bookable.

## Public API (`/api/v1/`)

| Endpoint | Access | Notes |
|----------|--------|-------|
| `GET events/` | Public | Summary cards, 12 per page |
| `GET events/{slug}/` | **Authenticated** | Full detail: gallery, itinerary, departures, related events |
| `GET destinations/`, `GET destinations/{slug}/` | Public | Detail includes the destination's events |
| `GET categories/` | Public | Active categories |

Only published adventures in published destinations are exposed. Draft and archived records
return 404 on public endpoints, including for admins.

### `GET events/` parameters

| Parameter | Example | Meaning |
|-----------|---------|---------|
| `search` | `annapurna` | Title, summary, destination name or region |
| `difficulty` | `easy,moderate` | One or more of `easy`, `moderate`, `difficult`, `extreme` |
| `activity_type` | `hiking` | `trekking`, `hiking`, `other` |
| `destination`, `category` | `everest` | Slugs |
| `region` | `gandaki` | Case-insensitive |
| `duration_min`, `duration_max` | `5` | Days |
| `price_min`, `price_max` | `25000` | Compared against `starting_price` |
| `departure_from`, `departure_to` | `2027-03-01` | Has a bookable departure starting in the window |
| `available` | `true` | Has at least one bookable departure |
| `featured` | `true` | |
| `ordering` | `-price` | `price`, `date`, `popularity`, `duration`; prefix `-` to reverse |
| `page`, `page_size` | `2` | `page_size` up to 100 |

Unknown `ordering` or `difficulty` values return 400.

## Admin API (`/api/v1/admin/`, admin or super admin only)

| Resource | Operations |
|----------|------------|
| `destinations/` | List, create, edit; publish/archive via `status`; order via `display_order` |
| `categories/` | List, create, edit; deactivate via `is_active` |
| `adventures/` | List, create, edit (with nested `itinerary`); `POST {id}/publish/`, `unpublish/`, `archive/` |
| `adventure-images/` | Gallery upload (multipart), edit, delete |
| `departures/` | List, create, edit; cancel/close via `status` |

Rules enforced server-side:

- An adventure can only be published into a published destination.
- `status`, `published_at` and `popularity` cannot be set directly on an adventure.
- Departures: start date not in the past, end ≥ start, cutoff not after the start date,
  minimum participants ≤ capacity, capacity never below seats already reserved, and a
  departure cannot be moved to another adventure.
- If omitted, `end_date` is derived from the adventure's duration and `booking_cutoff`
  defaults to `DEFAULT_BOOKING_CUTOFF_DAYS` (3) days before the start, Nepal time.
- Images: JPG, PNG or WebP, at most `MAX_IMAGE_UPLOAD_BYTES` (5 MB), verified as real images,
  stored under random filenames.

## Demo data

```bash
docker compose exec backend python manage.py seed_catalog
```

Creates four destinations, three categories and five adventures with departures. It is
idempotent and refuses to run when `DEBUG` is off. Prices, dates and policies are
placeholders; permit notes are informational and point to official sources.
