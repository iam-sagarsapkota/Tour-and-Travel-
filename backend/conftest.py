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
