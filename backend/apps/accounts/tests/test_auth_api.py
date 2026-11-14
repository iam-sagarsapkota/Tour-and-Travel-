import re

import pytest
from django.core import mail
from django.urls import reverse

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

REGISTER = reverse("auth:register")
LOGIN = reverse("auth:login")
REFRESH = reverse("auth:token-refresh")
LOGOUT = reverse("auth:logout")
ME = reverse("auth:me")
PASSWORD_CHANGE = reverse("auth:password-change")
PASSWORD_RESET = reverse("auth:password-reset")
PASSWORD_RESET_CONFIRM = reverse("auth:password-reset-confirm")


def registration(**overrides):
    data = {
        "full_name": "Maya Gurung",
        "email": "maya@example.com",
        "password": "Trek-Safely-2026",
        "password_confirm": "Trek-Safely-2026",
    }
    data.update(overrides)
    return {k: v for k, v in data.items() if v is not None}


def login(api, identifier, password):
    return api.post(LOGIN, {"identifier": identifier, "password": password})


class TestRegistration:
    def test_register_with_email(self, api):
        response = api.post(REGISTER, registration())

        assert response.status_code == 201
        assert response.data["user"]["email"] == "maya@example.com"
        assert response.data["user"]["role"] == "user"
        assert set(response.data["tokens"]) == {"access", "refresh"}
        assert "password" not in response.data["user"]
        assert User.objects.get(email="maya@example.com").check_password("Trek-Safely-2026")

    def test_register_with_phone_only(self, api):
        response = api.post(REGISTER, registration(email=None, phone="9812345678"))

        assert response.status_code == 201
        assert response.data["user"]["phone"] == "+9779812345678"
        assert response.data["user"]["email"] is None

    def test_requires_email_or_phone(self, api):
        response = api.post(REGISTER, registration(email=None))

        assert response.status_code == 400
        assert response.data["error"]["code"] == "validation_error"
        assert "email or phone" in str(response.data["error"]["details"]).lower()

    def test_requires_full_name(self, api):
        response = api.post(REGISTER, registration(full_name="  "))
        assert response.status_code == 400
        assert "full_name" in response.data["error"]["details"]

    def test_password_confirmation_must_match(self, api):
        response = api.post(REGISTER, registration(password_confirm="Different-2026"))
        assert response.status_code == 400
        assert "password_confirm" in response.data["error"]["details"]

    @pytest.mark.parametrize("weak", ["short1", "12345678901", "password"])
    def test_rejects_weak_password(self, api, weak):
        response = api.post(REGISTER, registration(password=weak, password_confirm=weak))
        assert response.status_code == 400
        assert "password" in response.data["error"]["details"]

    def test_rejects_duplicate_email_case_insensitively(self, api, user):
        response = api.post(REGISTER, registration(email="USER@example.com"))
        assert response.status_code == 400
        assert "email" in response.data["error"]["details"]

    def test_rejects_duplicate_phone_in_other_format(self, api, make_user):
        make_user(phone="+9779812345678")
        response = api.post(REGISTER, registration(email=None, phone="981-2345678"))
        assert response.status_code == 400
        assert "phone" in response.data["error"]["details"]

    def test_rejects_invalid_phone(self, api):
        response = api.post(REGISTER, registration(email=None, phone="12345"))
        assert response.status_code == 400
        assert "phone" in response.data["error"]["details"]

    def test_cannot_self_assign_privileged_role(self, api):
        response = api.post(REGISTER, registration(role="super_admin", is_staff=True))

        assert response.status_code == 201
        created = User.objects.get(email="maya@example.com")
        assert created.role == User.Role.USER
        assert not created.is_staff


class TestLogin:
    def test_login_with_email(self, api, user, password):
        response = login(api, "User@Example.com", password)

        assert response.status_code == 200
        assert response.data["user"]["id"] == str(user.id)
        assert set(response.data["tokens"]) == {"access", "refresh"}
        user.refresh_from_db()
        assert user.last_login is not None

    def test_login_with_phone(self, api, make_user, password):
        make_user(phone="+9779812345678")
        assert login(api, "9812345678", password).status_code == 200

    def test_wrong_password_is_rejected(self, api, user):
        response = login(api, user.email, "not-the-password")
        assert response.status_code == 401
        assert response.data["error"]["code"] == "invalid_credentials"

    def test_unknown_account_gets_same_error(self, api):
        response = login(api, "ghost@example.com", "whatever-123")
        assert response.status_code == 401
        assert response.data["error"]["code"] == "invalid_credentials"

    def test_inactive_account_cannot_login(self, api, make_user, password):
        inactive = make_user(is_active=False)
        assert login(api, inactive.email, password).status_code == 401

    def test_login_is_throttled(self, api, user):
        statuses = [login(api, user.email, "wrong-password").status_code for _ in range(11)]
        assert statuses[:10] == [401] * 10
        assert statuses[10] == 429


class TestTokens:
    def test_access_token_authenticates(self, api, user, password):
        tokens = login(api, user.email, password).data["tokens"]
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        assert api.get(ME).status_code == 200

    def test_refresh_rotates_and_revokes_old_token(self, api, user, password):
        old_refresh = login(api, user.email, password).data["tokens"]["refresh"]

        rotated = api.post(REFRESH, {"refresh": old_refresh})
        assert rotated.status_code == 200
        assert rotated.data["refresh"] != old_refresh
        assert "access" in rotated.data

        assert api.post(REFRESH, {"refresh": old_refresh}).status_code == 401

    def test_refresh_fails_for_deactivated_user(self, api, user, password):
        refresh = login(api, user.email, password).data["tokens"]["refresh"]
        user.is_active = False
        user.save()
        assert api.post(REFRESH, {"refresh": refresh}).status_code == 401

    def test_logout_revokes_refresh_token(self, api, user, password):
        tokens = login(api, user.email, password).data["tokens"]
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

        assert api.post(LOGOUT, {"refresh": tokens["refresh"]}).status_code == 204
        assert api.post(REFRESH, {"refresh": tokens["refresh"]}).status_code == 401

    def test_logout_requires_authentication(self, api):
        assert api.post(LOGOUT, {"refresh": "anything"}).status_code == 401


class TestMe:
    def test_requires_authentication(self, api):
        response = api.get(ME)
        assert response.status_code == 401
        assert response.data["error"]["code"] == "not_authenticated"

    def test_returns_current_user_with_profile(self, auth_client, user):
        response = auth_client(user).get(ME)

        assert response.status_code == 200
        assert response.data["full_name"] == "Pasang Sherpa"
        assert response.data["email_verified"] is False
        assert "nationality" in response.data["profile"]
        assert "password" not in response.data

    def test_update_name_and_profile(self, auth_client, user):
        response = auth_client(user).patch(
            ME,
            {"full_name": "Pasang L. Sherpa", "profile": {"nationality": "Nepali"}},
            format="json",
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.full_name == "Pasang L. Sherpa"
        assert user.profile.nationality == "Nepali"

    def test_cannot_escalate_role_or_change_contact(self, auth_client, user):
        response = auth_client(user).patch(
            ME, {"role": "admin", "email": "other@example.com", "is_active": False}, format="json"
        )

        assert response.status_code == 200
        user.refresh_from_db()
        assert user.role == User.Role.USER
        assert user.email == "user@example.com"
        assert user.is_active


class TestPasswordChange:
    NEW = "Even-Safer-Trek-2027"

    def payload(self, current):
        return {
            "current_password": current,
            "new_password": self.NEW,
            "new_password_confirm": self.NEW,
        }

    def test_rejects_wrong_current_password(self, auth_client, user):
        response = auth_client(user).post(PASSWORD_CHANGE, self.payload("wrong"))
        assert response.status_code == 400
        assert "current_password" in response.data["error"]["details"]

    def test_change_revokes_existing_tokens_and_returns_new(self, api, user, password):
        old = login(api, user.email, password).data["tokens"]
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {old['access']}")

        response = api.post(PASSWORD_CHANGE, self.payload(password))
        assert response.status_code == 200
        new = response.data["tokens"]

        # Old credentials and tokens are dead...
        assert api.get(ME).status_code == 401
        api.credentials()
        assert api.post(REFRESH, {"refresh": old["refresh"]}).status_code == 401
        assert login(api, user.email, password).status_code == 401
        # ...new ones work.
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {new['access']}")
        assert api.get(ME).status_code == 200
        api.credentials()
        assert login(api, user.email, self.NEW).status_code == 200


class TestPasswordReset:
    NEW = "Fresh-Summit-Pass-2027"

    def request_link(self, api, email):
        response = api.post(PASSWORD_RESET, {"email": email})
        assert response.status_code == 202
        return response

    def extract(self, body):
        match = re.search(r"uid=([\w-]+)&token=([\w-]+)", body)
        assert match, body
        return match.group(1), match.group(2)

    def confirm(self, api, uid, token, new=None):
        new = new or self.NEW
        return api.post(
            PASSWORD_RESET_CONFIRM,
            {"uid": uid, "token": token, "new_password": new, "new_password_confirm": new},
        )

    def test_sends_email_with_reset_link(self, api, user):
        self.request_link(api, "USER@example.com")

        assert len(mail.outbox) == 1
        assert mail.outbox[0].to == [user.email]
        assert "/reset-password?uid=" in mail.outbox[0].body

    def test_unknown_email_gets_same_response_and_no_mail(self, api):
        self.request_link(api, "ghost@example.com")
        assert mail.outbox == []

    def test_inactive_user_gets_no_mail(self, api, make_user):
        inactive = make_user(is_active=False)
        self.request_link(api, inactive.email)
        assert mail.outbox == []

    def test_confirm_sets_new_password_and_is_single_use(self, api, user, password):
        old_refresh = login(api, user.email, password).data["tokens"]["refresh"]
        self.request_link(api, user.email)
        uid, token = self.extract(mail.outbox[0].body)

        assert self.confirm(api, uid, token).status_code == 204
        assert login(api, user.email, self.NEW).status_code == 200
        assert login(api, user.email, password).status_code == 401
        assert api.post(REFRESH, {"refresh": old_refresh}).status_code == 401
        # The link cannot be replayed.
        assert self.confirm(api, uid, token, "Another-Pass-2028").status_code == 400

    @pytest.mark.parametrize(("uid", "token"), [("bad", "bad"), ("", "")])
    def test_rejects_invalid_link(self, api, user, uid, token):
        assert self.confirm(api, uid, token).status_code == 400

    def test_rejects_tampered_token(self, api, user):
        self.request_link(api, user.email)
        uid, _ = self.extract(mail.outbox[0].body)
        assert self.confirm(api, uid, "abc-tampered").status_code == 400

    def test_confirm_enforces_password_validators(self, api, user):
        self.request_link(api, user.email)
        uid, token = self.extract(mail.outbox[0].body)
        assert self.confirm(api, uid, token, "12345678").status_code == 400
