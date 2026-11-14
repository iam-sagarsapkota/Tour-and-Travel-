import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import User, UserProfile
from apps.accounts.validators import normalize_phone

pytestmark = pytest.mark.django_db


class TestCreateUser:
    def test_with_email_only(self):
        user = User.objects.create_user(email="a@example.com", password="x", full_name="A")
        assert user.email == "a@example.com"
        assert user.phone is None
        assert user.check_password("x")

    def test_with_phone_only(self):
        user = User.objects.create_user(phone="+9779812345678", password="x", full_name="A")
        assert user.email is None
        assert user.phone == "+9779812345678"

    def test_requires_email_or_phone(self):
        with pytest.raises(ValueError, match="email or phone"):
            User.objects.create_user(password="x", full_name="A")

    def test_primary_key_is_uuid(self, user):
        assert isinstance(user.pk, uuid.UUID)

    def test_defaults_to_regular_active_user(self, user):
        assert user.role == User.Role.USER
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser

    def test_password_is_hashed(self, user, password):
        assert user.password != password

    def test_profile_is_created_automatically(self, user):
        assert UserProfile.objects.filter(user=user).count() == 1


class TestNormalization:
    def test_email_is_lowercased_and_trimmed(self, make_user):
        assert make_user(email="  Mixed.Case@Example.COM ").email == "mixed.case@example.com"

    def test_blank_contacts_are_stored_as_null(self, make_user):
        user = make_user(email="a@example.com", phone="")
        assert user.phone is None

    def test_phone_is_normalized_on_save(self, make_user):
        assert make_user(phone="981-234 5678").phone == "+9779812345678"

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("+9779812345678", "+9779812345678"),
            ("9812345678", "+9779812345678"),  # Nepal mobile without country code
            ("+977 981-234-5678", "+9779812345678"),
            ("0014155550123", "+14155550123"),
            ("+44 (20) 7946 0958", "+442079460958"),
        ],
    )
    def test_normalize_phone(self, raw, expected):
        assert normalize_phone(raw) == expected

    @pytest.mark.parametrize("raw", ["12345", "abcdefghij", "+0123456789", "+1234567890123456"])
    def test_normalize_phone_rejects_invalid(self, raw):
        with pytest.raises(ValidationError):
            normalize_phone(raw)


class TestConstraints:
    def test_database_rejects_user_without_any_contact(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            User(full_name="Nobody").save()

    def test_email_unique_case_insensitively(self, make_user):
        make_user(email="dup@example.com")
        with pytest.raises(IntegrityError), transaction.atomic():
            make_user(email="DUP@example.com")

    def test_phone_unique_after_normalization(self, make_user):
        make_user(phone="+9779812345678")
        with pytest.raises(IntegrityError), transaction.atomic():
            make_user(phone="9812345678")

    def test_many_users_may_have_no_phone(self, make_user):
        make_user(email="a@example.com")
        make_user(email="b@example.com")
        assert User.objects.filter(phone__isnull=True).count() == 2


class TestRoles:
    def test_create_superuser_is_super_admin(self):
        user = User.objects.create_superuser(email="root@example.com", password="x", full_name="R")
        assert user.role == User.Role.SUPER_ADMIN
        assert user.is_staff
        assert user.is_superuser

    def test_admin_role_grants_staff_but_not_superuser(self, admin_user):
        assert admin_user.is_staff
        assert not admin_user.is_superuser

    def test_demotion_removes_flags(self, super_admin):
        super_admin.role = User.Role.USER
        super_admin.save()
        super_admin.refresh_from_db()
        assert not super_admin.is_staff
        assert not super_admin.is_superuser

    def test_role_helpers(self, user, admin_user, super_admin):
        assert (user.is_admin, admin_user.is_admin, super_admin.is_admin) == (False, True, True)
        assert not admin_user.is_super_admin
        assert super_admin.is_super_admin
