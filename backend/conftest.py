import pytest
from django.core.cache import cache
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import User

PASSWORD = "Trek-Safely-2026"


@pytest.fixture(autouse=True)
def _clear_cache():
    """Throttle counters live in the cache; isolate them per test."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def password():
    return PASSWORD


@pytest.fixture
def make_user(db):
    counter = iter(range(1, 10_000))

    def _make(**kwargs):
        n = next(counter)
        kwargs.setdefault("full_name", f"Trekker {n}")
        if "email" not in kwargs and "phone" not in kwargs:
            kwargs["email"] = f"trekker{n}@example.com"
        kwargs.setdefault("password", PASSWORD)
        return User.objects.create_user(**kwargs)

    return _make


@pytest.fixture
def user(make_user):
    return make_user(email="user@example.com", full_name="Pasang Sherpa")


@pytest.fixture
def admin_user(make_user):
    return make_user(email="admin@example.com", role=User.Role.ADMIN)


@pytest.fixture
def super_admin(make_user):
    return make_user(email="root@example.com", role=User.Role.SUPER_ADMIN)


@pytest.fixture
def auth_client():
    """Return an APIClient carrying a valid access token for the given user."""

    def _client(user):
        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client

    return _client


# --- Catalog factories ------------------------------------------------------


@pytest.fixture
def make_destination(db):
    from apps.destinations.models import Destination

    counter = iter(range(1, 10_000))

    def _make(**kwargs):
        n = next(counter)
        kwargs.setdefault("name", f"Region {n}")
        kwargs.setdefault("slug", f"region-{n}")
        kwargs.setdefault("region", "Gandaki")
        kwargs.setdefault("status", "published")
        return Destination.objects.create(**kwargs)

    return _make


@pytest.fixture
def make_category(db):
    from apps.adventures.models import AdventureCategory

    counter = iter(range(1, 10_000))

    def _make(**kwargs):
        n = next(counter)
        kwargs.setdefault("name", f"Category {n}")
        kwargs.setdefault("slug", f"category-{n}")
        return AdventureCategory.objects.create(**kwargs)

    return _make


@pytest.fixture
def make_adventure(db, make_destination, make_category):
    from apps.adventures.models import Adventure

    counter = iter(range(1, 10_000))

    def _make(**kwargs):
        n = next(counter)
        if "destination" not in kwargs:
            kwargs["destination"] = make_destination()
        if "category" not in kwargs:
            kwargs["category"] = make_category()
        kwargs.setdefault("title", f"Trek {n}")
        kwargs.setdefault("slug", f"trek-{n}")
        kwargs.setdefault("summary", "A fine walk.")
        kwargs.setdefault("description", "Long description.")
        kwargs.setdefault("difficulty", "moderate")
        kwargs.setdefault("duration_days", 5)
        kwargs.setdefault("base_price", "25000.00")
        kwargs.setdefault("status", "published")
        adventure = Adventure.objects.create(**kwargs)
        adventure.refresh_from_db()  # load Decimal/typed values as the database stores them
        return adventure

    return _make


@pytest.fixture
def make_departure(db, make_adventure):
    import datetime as dt

    from django.utils import timezone

    from apps.departures.models import Departure

    def _make(*, days_ahead=30, **kwargs):
        if "adventure" not in kwargs:
            kwargs["adventure"] = make_adventure()
        start = kwargs.setdefault(
            "start_date", timezone.localdate() + dt.timedelta(days=days_ahead)
        )
        kwargs.setdefault(
            "end_date", start + dt.timedelta(days=kwargs["adventure"].duration_days - 1)
        )
        kwargs.setdefault("capacity", 12)
        if "booking_cutoff" not in kwargs:
            kwargs["booking_cutoff"] = timezone.now() + dt.timedelta(days=days_ahead - 3)
        departure = Departure.objects.create(**kwargs)
        departure.refresh_from_db()
        return departure

    return _make
