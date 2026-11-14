import pytest
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

LIST = reverse("admin_users:user-list")


def detail(user):
    return reverse("admin_users:user-detail", args=[user.pk])


def new_user(**overrides):
    data = {"full_name": "New Guide", "email": "guide@example.com", "password": "Guide-Pass-2026"}
    data.update(overrides)
    return data


class TestAccess:
    def test_anonymous_is_rejected(self, api):
        assert api.get(LIST).status_code == 401

    def test_regular_user_is_forbidden(self, auth_client, user):
        response = auth_client(user).get(LIST)
        assert response.status_code == 403
        assert response.data["error"]["code"] == "permission_denied"

    def test_regular_user_cannot_read_another_user(self, auth_client, user, make_user):
        assert auth_client(user).get(detail(make_user())).status_code == 403

    def test_admin_can_list_users_without_password_fields(self, auth_client, admin_user, user):
        response = auth_client(admin_user).get(LIST)

        assert response.status_code == 200
        assert response.data["count"] == 2
        assert all("password" not in row for row in response.data["results"])

    def test_search_by_name_email_or_phone(self, auth_client, admin_user, make_user):
        make_user(full_name="Dawa Lama", phone="+9779800000001")
        make_user(full_name="Someone Else")
        client = auth_client(admin_user)

        assert client.get(LIST, {"search": "dawa"}).data["count"] == 1
        assert client.get(LIST, {"search": "9800000001"}).data["count"] == 1

    def test_filter_by_role_and_status(self, auth_client, admin_user, make_user):
        make_user(is_active=False)
        client = auth_client(admin_user)

        assert client.get(LIST, {"role": "admin"}).data["count"] == 1
        assert client.get(LIST, {"is_active": "false"}).data["count"] == 1


class TestCreate:
    def test_admin_creates_regular_user(self, auth_client, admin_user):
        response = auth_client(admin_user).post(LIST, new_user())

        assert response.status_code == 201
        assert "password" not in response.data
        created = User.objects.get(email="guide@example.com")
        assert created.role == User.Role.USER
        assert created.check_password("Guide-Pass-2026")

    def test_create_requires_email_or_phone(self, auth_client, admin_user):
        response = auth_client(admin_user).post(LIST, new_user(email=""))
        assert response.status_code == 400

    def test_create_requires_password(self, auth_client, admin_user):
        data = new_user()
        del data["password"]
        assert auth_client(admin_user).post(LIST, data).status_code == 400

    def test_admin_cannot_grant_admin_role(self, auth_client, admin_user):
        response = auth_client(admin_user).post(LIST, new_user(role="admin"))
        assert response.status_code == 400
        assert "role" in response.data["error"]["details"]
        assert not User.objects.filter(email="guide@example.com").exists()

    def test_super_admin_can_grant_admin_role(self, auth_client, super_admin):
        response = auth_client(super_admin).post(LIST, new_user(role="admin"))
        assert response.status_code == 201
        assert User.objects.get(email="guide@example.com").is_staff


class TestUpdate:
    def test_admin_edits_regular_user(self, auth_client, admin_user, user):
        response = auth_client(admin_user).patch(detail(user), {"full_name": "Renamed"})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.full_name == "Renamed"

    def test_admin_cannot_modify_other_admins_or_super_admins(
        self, auth_client, admin_user, super_admin, make_user
    ):
        other_admin = make_user(role=User.Role.ADMIN)
        client = auth_client(admin_user)

        assert client.patch(detail(super_admin), {"full_name": "Hacked"}).status_code == 403
        assert client.patch(detail(other_admin), {"full_name": "Hacked"}).status_code == 403
        assert client.delete(detail(super_admin)).status_code == 403

    def test_admin_cannot_promote_user(self, auth_client, admin_user, user):
        response = auth_client(admin_user).patch(detail(user), {"role": "super_admin"})
        assert response.status_code == 400
        user.refresh_from_db()
        assert user.role == User.Role.USER

    def test_cannot_remove_last_contact_channel(self, auth_client, admin_user, user):
        response = auth_client(admin_user).patch(detail(user), {"email": ""})
        assert response.status_code == 400

    def test_update_rejects_duplicate_email(self, auth_client, admin_user, user, make_user):
        other = make_user(email="taken@example.com")
        response = auth_client(admin_user).patch(detail(user), {"email": other.email.upper()})
        assert response.status_code == 400

    def test_admin_password_reset_for_user(self, auth_client, admin_user, user):
        response = auth_client(admin_user).patch(detail(user), {"password": "Reset-By-Admin-26"})
        assert response.status_code == 200
        user.refresh_from_db()
        assert user.check_password("Reset-By-Admin-26")


class TestDeactivate:
    def test_delete_deactivates_instead_of_deleting(self, api, auth_client, admin_user, user):
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = str(RefreshToken.for_user(user))

        assert auth_client(admin_user).delete(detail(user)).status_code == 204

        user.refresh_from_db()
        assert not user.is_active
        assert api.post(reverse("auth:token-refresh"), {"refresh": refresh}).status_code == 401
        assert auth_client(user).get(reverse("auth:me")).status_code == 401

    def test_cannot_deactivate_yourself(self, auth_client, super_admin):
        response = auth_client(super_admin).delete(detail(super_admin))
        assert response.status_code == 400
        super_admin.refresh_from_db()
        assert super_admin.is_active

    def test_reactivate_via_update(self, auth_client, admin_user, make_user):
        inactive = make_user(is_active=False)
        assert (
            auth_client(admin_user).patch(detail(inactive), {"is_active": True}).status_code == 200
        )
        inactive.refresh_from_db()
        assert inactive.is_active
