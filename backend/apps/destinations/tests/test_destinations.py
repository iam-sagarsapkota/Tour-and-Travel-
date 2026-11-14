import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.destinations.models import Destination

pytestmark = pytest.mark.django_db

LIST = reverse("destinations:destination-list")
ADMIN_LIST = reverse("catalog_admin:destination-list")


def detail(destination):
    return reverse("destinations:destination-detail", args=[destination.slug])


def admin_detail(destination):
    return reverse("catalog_admin:destination-detail", args=[destination.pk])


class TestPublic:
    def test_lists_published_destinations_in_display_order(self, api, make_destination):
        make_destination(slug="langtang", display_order=2)
        make_destination(slug="everest", display_order=1)
        make_destination(slug="secret", status="draft")
        make_destination(slug="old", status="archived")

        response = api.get(LIST)

        assert response.status_code == 200
        assert [row["slug"] for row in response.data["results"]] == ["everest", "langtang"]

    def test_list_includes_published_event_count(self, api, make_destination, make_adventure):
        everest = make_destination(slug="everest")
        make_adventure(destination=everest)
        make_adventure(destination=everest, status="draft")

        assert api.get(LIST).data["results"][0]["event_count"] == 1

    def test_detail_is_public_and_lists_related_events(self, api, make_destination, make_adventure):
        everest = make_destination(
            slug="everest",
            description="Home of Sagarmatha.",
            permit_info="Sagarmatha National Park permit required.",
        )
        make_adventure(destination=everest, slug="ebc")
        make_adventure(destination=everest, slug="hidden", status="draft")

        response = api.get(detail(everest))

        assert response.status_code == 200
        assert response.data["permit_info"].startswith("Sagarmatha")
        assert [event["slug"] for event in response.data["events"]] == ["ebc"]

    def test_unpublished_detail_is_404(self, api, make_destination):
        assert api.get(detail(make_destination(status="draft"))).status_code == 404


class TestAdmin:
    def test_requires_admin(self, api, auth_client, user):
        assert api.get(ADMIN_LIST).status_code == 401
        assert auth_client(user).get(ADMIN_LIST).status_code == 403
        assert auth_client(user).post(ADMIN_LIST, {"name": "X"}).status_code == 403

    def test_admin_sees_all_statuses(self, auth_client, admin_user, make_destination):
        make_destination(status="draft")
        make_destination(status="archived")
        make_destination()
        assert auth_client(admin_user).get(ADMIN_LIST).data["count"] == 3

    def test_create_generates_slug_and_defaults_to_draft(self, auth_client, admin_user):
        response = auth_client(admin_user).post(
            ADMIN_LIST, {"name": "Annapurna Region", "region": "Gandaki"}
        )

        assert response.status_code == 201
        assert response.data["slug"] == "annapurna-region"
        assert response.data["status"] == "draft"

    def test_duplicate_names_get_distinct_slugs(self, auth_client, admin_user):
        client = auth_client(admin_user)
        first = client.post(ADMIN_LIST, {"name": "Pokhara", "region": "Gandaki"})
        second = client.post(ADMIN_LIST, {"name": "Pokhara", "region": "Gandaki"})

        assert first.data["slug"] == "pokhara"
        assert second.status_code == 201
        assert second.data["slug"] == "pokhara-2"

    def test_publish_archive_and_reorder(self, auth_client, admin_user, make_destination):
        destination = make_destination(status="draft")
        client = auth_client(admin_user)

        response = client.patch(
            admin_detail(destination), {"status": "published", "display_order": 5}
        )
        assert response.status_code == 200
        assert api_visible(destination)

        client.patch(admin_detail(destination), {"status": "archived"})
        assert not api_visible(destination)

    def test_delete_is_not_allowed(self, auth_client, admin_user, make_destination):
        destination = make_destination()
        assert auth_client(admin_user).delete(admin_detail(destination)).status_code == 405
        assert Destination.objects.filter(pk=destination.pk).exists()


def api_visible(destination):
    from rest_framework.test import APIClient

    return APIClient().get(detail(destination)).status_code == 200


def test_slug_is_unique(make_destination):
    make_destination(slug="everest")
    with pytest.raises(IntegrityError), transaction.atomic():
        make_destination(slug="everest")
