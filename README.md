# Himalaya Trails — Tour & Travel System

A trekking and hiking booking platform promoting Nepal tourism. Visitors discover
adventures, registered users book solo or group places and pay online, and administrators
manage the catalog, departures, bookings and operations.

Built from `Tour_Travel_System_PRD_ReactBits.pdf` (PRD v1.1) in phases — see
[docs/phases.md](docs/phases.md) for the plan and current status.

**Current status: Phases 1–5 complete.** Accounts and authentication, the tourism catalog,
the public React site, solo/group bookings with capacity locking, and eSewa/Khalti payments
with server-side verification are built. Card payments, dashboards and notifications are next.

## Stack

| Area | Technology (pinned version) |
|------|-----------------------------|
| Backend | Python 3.14, Django 6.1.3, Django REST Framework 3.18.3 |
| Auth | Simple JWT 5.5.1 (rotating refresh tokens, blacklist) |
| API docs | drf-spectacular 0.30.0 (OpenAPI) |
| Database | PostgreSQL 18.7 |
| Cache / broker | Redis 8.8.4, Celery 5.7.0 |
| Images | Pillow 13.0.0 |
| Tests / quality | pytest 9.2.0, pytest-django 4.14.0, Ruff 0.17.5 |
| Runtime | Docker Compose |
| Frontend | React 19, Vite 8, TypeScript, Tailwind CSS 4, shadcn/ui, React Bits (GSAP) |
| Frontend tests | Vitest, React Testing Library, oxlint, Prettier |


## Repository layout

```
backend/
  config/            settings (base, development, production, test), urls, celery
  apps/accounts/     custom user model, auth API, admin user management
  apps/destinations/ destination directory
  apps/adventures/   categories, adventures, gallery, itinerary, public event API
  apps/departures/   scheduled departures, capacity and "bookable" rule
  apps/bookings/     bookings, seat holds, expiry task, cancellation
  apps/payments/     eSewa and Khalti gateways, verification, reconciliation
  common/            error envelope, pagination, health endpoints
  requirements/      pinned dependencies (base, dev, prod)
frontend/
  src/               React app (see docs/frontend.md for the layout)
  Dockerfile         dev server and production Nginx image
docs/                phases, authentication, catalog, bookings, payments, frontend
docker-compose.yml   development stack
.github/workflows/   CI
```

## Run with Docker

Prerequisites: Docker Desktop (running).

```bash
cp .env.example .env          # then set DJANGO_SECRET_KEY and POSTGRES_PASSWORD
docker compose up --build
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py seed_catalog   # optional demo data
```

Migrations run automatically when the backend container starts.

| URL | What |
|-----|------|
| http://localhost:5173/ | Website |
| http://localhost:8000/api/v1/docs/ | Swagger UI |
| http://localhost:8000/api/v1/schema/ | OpenAPI schema |
| http://localhost:8000/django-admin/ | Django admin |
| http://localhost:8000/health/ , `/ready/` | Liveness / readiness |

Other commands:

```bash
docker compose exec backend pytest                     # tests (against PostgreSQL)
docker compose exec frontend npm test                  # frontend tests
docker compose exec backend ruff check .               # lint
docker compose exec backend python manage.py migrate   # apply migrations manually
docker compose logs -f
docker compose down
```

## Run the tests without Docker

```bash
cd backend
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements/dev.txt   # Linux/macOS: .venv/bin/python
.venv/Scripts/python -m pytest
```

Without `DATABASE_URL` the test settings use in-memory SQLite. CI and Docker run the same
suite against PostgreSQL.

## Environment variables

See [.env.example](.env.example). Secrets are read from the environment only;
`config.settings.production` refuses to start without `DJANGO_SECRET_KEY` and
`DJANGO_ALLOWED_HOSTS`.

## Documentation

- [Delivery phases and open decisions](docs/phases.md)
- [Authentication, roles and token model](docs/authentication.md)
- [Catalog, departures and listing filters](docs/catalog.md)
- [Bookings, seat holds and concurrency](docs/bookings.md)
- [Payments: eSewa, Khalti, verification and sandbox testing](docs/payments.md)
- [Frontend structure, auth handling and React Bits notes](docs/frontend.md)

## Branches

- `main` — reviewed, stable code
- `development` — integration branch; each completed phase is pushed here first
