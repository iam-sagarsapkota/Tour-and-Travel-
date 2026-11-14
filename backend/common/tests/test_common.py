import pytest
from django.urls import reverse


def test_health_is_public(api):
    response = api.get(reverse("health"))
    assert response.status_code == 200
    assert response.data == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_checks_database(api):
    assert api.get(reverse("ready")).status_code == 200


@pytest.mark.django_db
def test_openapi_schema_is_generated(api):
    response = api.get(reverse("schema"))
    assert response.status_code == 200
    assert "/api/v1/auth/register/" in response.data["paths"]


@pytest.mark.django_db
def test_errors_use_consistent_envelope(api):
    response = api.get("/api/v1/auth/me/")
    assert set(response.data) == {"error"}
    assert set(response.data["error"]) == {"code", "message", "details"}


@pytest.mark.django_db
def test_unknown_route_is_404(api):
    assert api.get("/api/v1/nope/").status_code == 404
