import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.adventures.models import Adventure, AdventureImage

pytestmark = pytest.mark.django_db

LIST = reverse("catalog_admin:adventure-list")
CATEGORY_LIST = reverse("catalog_admin:category-list")
IMAGE_LIST = reverse("catalog_admin:adventure-image-list")


def detail(adventure):
    return reverse("catalog_admin:adventure-detail", args=[adventure.pk])


def action(adventure, name):
    return reverse(f"catalog_admin:adventure-{name}", args=[adventure.pk])


def png(name="photo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "#123B32").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@pytest.fixture
def payload(make_destination, make_category):
    return {
        "title": "Mardi Himal Trek",
        "destination": str(make_destination().pk),
        "category": str(make_category().pk),
        "activity_type": "trekking",
        "summary": "A quiet ridge walk below Machhapuchhre.",
        "description": "Full description.",
        "difficulty": "moderate",
        "duration_days": 6,
        "base_price": "32000.00",
        "inclusions": ["Guide", "Permits"],
        "itinerary": [
            {"day_number": 1, "title": "Pokhara to Deurali"},
            {"day_number": 2, "title": "Deurali to Low Camp"},
        ],
    }


class TestAccess:
    def test_requires_admin(self, api, auth_client, user, payload, make_adventure):
        adventure = make_adventure()
        assert api.get(LIST).status_code == 401
        client = auth_client(user)
        assert client.get(LIST).status_code == 403
        assert client.post(LIST, payload).status_code == 403
        assert client.patch(detail(adventure), {"title": "x"}).status_code == 403
        assert client.post(action(adventure, "archive")).status_code == 403

    def test_admin_lists_all_statuses_and_filters(self, auth_client, admin_user, make_adventure):
        make_adventure(status="draft")
        make_adventure(status="archived")
        make_adventure()
        client = auth_client(admin_user)

        assert client.get(LIST).data["count"] == 3
        assert client.get(LIST, {"status": "draft"}).data["count"] == 1


class TestCreateAndEdit:
    def test_create_draft_with_itinerary(self, auth_client, admin_user, payload):
        response = auth_client(admin_user).post(LIST, payload)

        assert response.status_code == 201, response.data
        assert response.data["slug"] == "mardi-himal-trek"
        assert response.data["status"] == "draft"
        assert response.data["currency"] == "NPR"
        adventure = Adventure.objects.get(pk=response.data["id"])
        assert adventure.itinerary.count() == 2
        assert adventure.inclusions == ["Guide", "Permits"]

    def test_client_cannot_set_status_or_popularity_directly(
        self, auth_client, admin_user, payload
    ):
        payload.update(status="published", popularity=999)
        response = auth_client(admin_user).post(LIST, payload)

        assert response.status_code == 201
        adventure = Adventure.objects.get(pk=response.data["id"])
        assert adventure.status == "draft"
        assert adventure.popularity == 0

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("base_price", "0"),
            ("base_price", "-5"),
            ("duration_days", 0),
            ("difficulty", "impossible"),
            ("currency", "RUPEES"),
            ("inclusions", "not-a-list"),
            ("title", ""),
        ],
    )
    def test_validation(self, auth_client, admin_user, payload, field, value):
        payload[field] = value
        response = auth_client(admin_user).post(LIST, payload)
        assert response.status_code == 400
        assert field in response.data["error"]["details"]

    def test_itinerary_days_must_be_unique(self, auth_client, admin_user, payload):
        payload["itinerary"] = [
            {"day_number": 1, "title": "A"},
            {"day_number": 1, "title": "B"},
        ]
        response = auth_client(admin_user).post(LIST, payload)
        assert response.status_code == 400
        assert "itinerary" in response.data["error"]["details"]

    def test_min_participants_cannot_exceed_group_size(self, auth_client, admin_user, payload):
        payload.update(min_participants=10, max_group_size=4)
        assert auth_client(admin_user).post(LIST, payload).status_code == 400

    def test_edit_replaces_itinerary_only_when_provided(self, auth_client, admin_user, payload):
        client = auth_client(admin_user)
        created = client.post(LIST, payload).data
        url = reverse("catalog_admin:adventure-detail", args=[created["id"]])

        renamed = client.patch(url, {"title": "Mardi Himal Base Camp"})
        assert renamed.status_code == 200
        assert renamed.data["slug"] == "mardi-himal-trek"  # slug stays stable
        assert len(renamed.data["itinerary"]) == 2

        replaced = client.patch(url, {"itinerary": [{"day_number": 1, "title": "Only day"}]})
        assert [day["title"] for day in replaced.data["itinerary"]] == ["Only day"]

    def test_delete_is_not_allowed(self, auth_client, admin_user, make_adventure):
        adventure = make_adventure()
        assert auth_client(admin_user).delete(detail(adventure)).status_code == 405


class TestWorkflow:
    def test_publish_makes_event_public(self, api, auth_client, admin_user, make_adventure):
        adventure = make_adventure(status="draft")

        response = auth_client(admin_user).post(action(adventure, "publish"))

        assert response.status_code == 200
        assert response.data["status"] == "published"
        assert response.data["published_at"] is not None
        assert api.get(reverse("events:event-list")).data["count"] == 1

    def test_cannot_publish_into_unpublished_destination(
        self, auth_client, admin_user, make_adventure, make_destination
    ):
        adventure = make_adventure(status="draft", destination=make_destination(status="draft"))

        response = auth_client(admin_user).post(action(adventure, "publish"))

        assert response.status_code == 400
        adventure.refresh_from_db()
        assert adventure.status == "draft"

    def test_archive_hides_event_and_unpublish_returns_to_draft(
        self, api, auth_client, admin_user, make_adventure
    ):
        adventure = make_adventure()
        client = auth_client(admin_user)

        assert client.post(action(adventure, "archive")).data["status"] == "archived"
        assert api.get(reverse("events:event-list")).data["count"] == 0
        assert client.post(action(adventure, "unpublish")).data["status"] == "draft"


class TestImages:
    def test_upload_cover_image(self, auth_client, admin_user, make_adventure, settings, tmp_path):
        settings.MEDIA_ROOT = tmp_path
        adventure = make_adventure()

        response = auth_client(admin_user).patch(
            detail(adventure), {"cover_image": png()}, format="multipart"
        )

        assert response.status_code == 200, response.data
        assert response.data["cover_image"].endswith(".png")

    def test_gallery_upload_list_and_delete(
        self, auth_client, admin_user, make_adventure, settings, tmp_path
    ):
        settings.MEDIA_ROOT = tmp_path
        adventure = make_adventure()
        client = auth_client(admin_user)

        created = client.post(
            IMAGE_LIST,
            {"adventure": str(adventure.pk), "image": png(), "alt_text": "Ridge at dawn"},
            format="multipart",
        )
        assert created.status_code == 201, created.data
        assert client.get(IMAGE_LIST, {"adventure": str(adventure.pk)}).data["count"] == 1

        url = reverse("catalog_admin:adventure-image-detail", args=[created.data["id"]])
        assert client.delete(url).status_code == 204
        assert not AdventureImage.objects.exists()

    def test_rejects_non_image_upload(self, auth_client, admin_user, make_adventure):
        fake = SimpleUploadedFile("shell.png", b"<?php echo 1; ?>", content_type="image/png")
        response = auth_client(admin_user).post(
            IMAGE_LIST,
            {"adventure": str(make_adventure().pk), "image": fake},
            format="multipart",
        )
        assert response.status_code == 400

    def test_rejects_disallowed_extension(self, auth_client, admin_user, make_adventure):
        response = auth_client(admin_user).post(
            IMAGE_LIST,
            {"adventure": str(make_adventure().pk), "image": png("photo.gif")},
            format="multipart",
        )
        assert response.status_code == 400

    def test_rejects_oversized_upload(self, auth_client, admin_user, make_adventure, settings):
        settings.MAX_IMAGE_UPLOAD_BYTES = 10
        response = auth_client(admin_user).post(
            IMAGE_LIST,
            {"adventure": str(make_adventure().pk), "image": png()},
            format="multipart",
        )
        assert response.status_code == 400

    def test_regular_user_cannot_upload(self, auth_client, user, make_adventure):
        response = auth_client(user).post(
            IMAGE_LIST,
            {"adventure": str(make_adventure().pk), "image": png()},
            format="multipart",
        )
        assert response.status_code == 403


class TestCategoriesAdmin:
    def test_crud(self, auth_client, admin_user, user):
        assert auth_client(user).post(CATEGORY_LIST, {"name": "Teahouse"}).status_code == 403
        client = auth_client(admin_user)

        created = client.post(CATEGORY_LIST, {"name": "Teahouse Treks"})
        assert created.status_code == 201
        assert created.data["slug"] == "teahouse-treks"

        url = reverse("catalog_admin:category-detail", args=[created.data["id"]])
        assert client.patch(url, {"is_active": False}).data["is_active"] is False
        assert client.delete(url).status_code == 405
