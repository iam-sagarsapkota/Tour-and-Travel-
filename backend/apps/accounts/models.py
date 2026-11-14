import uuid

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from .managers import UserManager
from .validators import normalize_phone


class User(AbstractBaseUser, PermissionsMixin):
    """Account identified by email OR phone number (at least one is required).

    ``role`` is the single source of truth for privilege. ``is_staff`` and
    ``is_superuser`` are derived from it on every save so Django admin and
    permission checks stay consistent with the API role.
    """

    class Role(models.TextChoices):
        USER = "user", "Registered user"
        ADMIN = "admin", "Admin"
        SUPER_ADMIN = "super_admin", "Super admin"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=150)
    # NULL (never "") when absent, so the unique constraints allow many users
    # without an email or without a phone.
    email = models.EmailField(unique=True, null=True, blank=True)
    phone = models.CharField(max_length=16, unique=True, null=True, blank=True)

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER, db_index=True)
    is_active = models.BooleanField(
        default=True, help_text="Deactivate instead of deleting accounts."
    )
    is_staff = models.BooleanField(default=False, editable=False)

    email_verified_at = models.DateTimeField(null=True, blank=True)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        ordering = ["-date_joined"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email__isnull=False) | models.Q(phone__isnull=False),
                name="accounts_user_email_or_phone_required",
            ),
        ]

    def __str__(self):
        return self.email or self.phone or str(self.pk)

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower() if self.email and self.email.strip() else None
        self.phone = normalize_phone(self.phone) if self.phone else None
        self.is_staff = self.role in (self.Role.ADMIN, self.Role.SUPER_ADMIN)
        self.is_superuser = self.role == self.Role.SUPER_ADMIN
        super().save(*args, **kwargs)

    @property
    def is_admin(self) -> bool:
        return self.role in (self.Role.ADMIN, self.Role.SUPER_ADMIN)

    @property
    def is_super_admin(self) -> bool:
        return self.role == self.Role.SUPER_ADMIN

    @property
    def email_verified(self) -> bool:
        return self.email_verified_at is not None

    @property
    def phone_verified(self) -> bool:
        return self.phone_verified_at is not None

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split(" ")[0] if self.full_name else ""


class UserProfile(models.Model):
    """Optional traveller details, created automatically alongside each user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    emergency_contact_name = models.CharField(max_length=150, blank=True)
    emergency_contact_phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user}"
