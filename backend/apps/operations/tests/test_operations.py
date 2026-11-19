import pytest
from django.urls import reverse
from rest_framework_simplejwt.tokens import RefreshToken

from apps.bookings import services as booking_services
from apps.operations.models import AuditLog, ContactInquiry, SiteSettings

pytestmark = pytest.mark.django_db


class TestSiteSettings:
    def test_public_read_and_admin_update_is_audited(self, api, auth_client, admin_user, user):
        url = reverse("admin_operations:site-settings")
        assert auth_client(user).patch(url, {"announcement": "x"}).status_code == 403

        response = auth_client(admin_user).patch(
            url,
            {"announcement": "Monsoon: some trails closed", "announcement_active": True},
        )

        assert response.status_code == 200
        public = api.get(reverse("operations:site")).data
        assert public["announcement"] == "Monsoon: some trails closed"
        assert public["announcement_active"] is True
        log = AuditLog.objects.get(object_type="operations.sitesettings")
        assert log.actor == admin_user
        assert log.changes["announcement_active"] == [False, True]

    def test_singleton(self):
        SiteSettings(site_name="A").save()
        SiteSettings(site_name="B").save()
        assert SiteSettings.objects.count() == 1
        assert SiteSettings.load().site_name == "B"


class TestContact:
    def test_public_submission_and_admin_handling(self, api, auth_client, admin_user, user):
        response = api.post(
            reverse("operations:contact"),
            {
                "name": "Anna",
                "email": "anna@example.com",
                "subject": "Group of 12",
                "message": "Can you arrange a private departure?",
                "handled": True,  # ignored
            },
        )
        assert response.status_code == 201
        inquiry = ContactInquiry.objects.get()
        assert not inquiry.handled

        url = reverse("admin_operations:contact-list")
        assert auth_client(user).get(url).status_code == 403
        client = auth_client(admin_user)
        assert client.get(url, {"handled": "false"}).data["count"] == 1
        handle = reverse("admin_operations:contact-handle", args=[inquiry.pk])
        assert client.post(handle).data["handled_by"] == admin_user.full_name

    def test_validation(self, api):
        response = api.post(reverse("operations:contact"), {"name": "A", "email": "nope"})
        assert response.status_code == 400


class TestAuditTrail:
    def test_catalog_changes_are_recorded(self, auth_client, admin_user, make_adventure):
        adventure = make_adventure(status="draft")
        client = auth_client(admin_user)

        client.patch(
            reverse("catalog_admin:adventure-detail", args=[adventure.pk]), {"base_price": "41000"}
        )
        client.post(reverse("catalog_admin:adventure-publish", args=[adventure.pk]))

        logs = AuditLog.objects.filter(object_id=str(adventure.pk)).order_by("created_at", "id")
        assert [log.action for log in logs] == ["update", "publish"]
        assert logs[0].changes["base_price"] == ["25000.00", "41000.00"]
        assert logs[0].ip_address == "127.0.0.1"

    def test_user_password_changes_never_logged_in_clear(self, auth_client, admin_user, make_user):
        traveller = make_user()
        auth_client(admin_user).patch(
            reverse("admin_users:user-detail", args=[traveller.pk]),
            {"full_name": "Renamed", "password": "Brand-New-Pass-26"},
        )
        log = AuditLog.objects.get(object_id=str(traveller.pk))
        assert log.changes["password"] == ["(hidden)", "(changed)"]
        assert "Brand-New-Pass-26" not in str(log.changes)

    def test_booking_cancel_and_deactivation_are_recorded(
        self, auth_client, admin_user, user, make_user, make_departure
    ):
        booking = booking_services.create_booking(
            user=user,
            departure_id=make_departure().pk,
            participants=[{"full_name": "A"}],
            policy_accepted=True,
        )
        client = auth_client(admin_user)
        client.post(
            reverse("admin_bookings:booking-cancel", args=[booking.pk]), {"reason": "Duplicate"}
        )
        client.delete(reverse("admin_users:user-detail", args=[make_user().pk]))

        assert set(AuditLog.objects.values_list("action", flat=True)) == {"cancel", "deactivate"}
        assert AuditLog.objects.get(action="cancel").note == "Duplicate"

    def test_audit_log_is_admin_only_and_read_only(self, auth_client, admin_user, user):
        url = reverse("admin_operations:audit-log-list")
        assert auth_client(user).get(url).status_code == 403
        assert auth_client(admin_user).get(url).status_code == 200
        assert auth_client(admin_user).post(url, {}).status_code == 405


class TestSessions:
    def test_list_and_sign_out_everywhere(self, api, auth_client, user, password):
        api.post(reverse("auth:login"), {"identifier": user.email, "password": password})
        api.post(reverse("auth:login"), {"identifier": user.email, "password": password})
        client = auth_client(user)  # adds a third outstanding token
        url = reverse("auth:sessions")

        assert len(client.get(url).data) == 3
        assert client.delete(url).status_code == 204
        assert client.get(url).data == []
        token = RefreshToken.for_user(user)  # new logins still work afterwards
        assert api.post(reverse("auth:token-refresh"), {"refresh": str(token)}).status_code == 200
