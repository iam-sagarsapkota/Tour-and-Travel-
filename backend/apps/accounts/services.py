"""Account business logic. Views and serializers call these; they hold no HTTP concerns."""

import logging

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .exceptions import InvalidCredentials
from .models import User

logger = logging.getLogger(__name__)


def issue_tokens(user: User) -> dict[str, str]:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


def revoke_refresh_tokens(user: User) -> None:
    """Blacklist every outstanding refresh token of the user (all sessions)."""
    outstanding = OutstandingToken.objects.filter(user=user, blacklistedtoken__isnull=True)
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in outstanding], ignore_conflicts=True
    )


def register_user(*, full_name: str, password: str, email=None, phone=None) -> User:
    """Create a regular user. Role and status are never taken from client input."""
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    with transaction.atomic():
        user = User.objects.create_user(
            email=email, phone=phone, password=password, full_name=full_name
        )
        notify(user, Notification.Kind.WELCOME, dedupe_key=f"welcome:{user.pk}")
        if user.email:
            send_email_verification(user)
    return user


# --- Email verification ------------------------------------------------------

_VERIFY_SALT = "accounts.email-verification"
EMAIL_VERIFICATION_MAX_AGE = 3 * 24 * 60 * 60  # seconds


def send_email_verification(user: User) -> None:
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    if not user.email or user.email_verified:
        return
    token = signing.dumps({"u": str(user.pk), "e": user.email}, salt=_VERIFY_SALT)
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    notify(user, Notification.Kind.EMAIL_VERIFICATION, link=link)


def verify_email(token: str) -> User | None:
    """Mark the address verified. The link only works for the address it was sent to."""
    try:
        data = signing.loads(token, salt=_VERIFY_SALT, max_age=EMAIL_VERIFICATION_MAX_AGE)
        user = User.objects.get(pk=data["u"], is_active=True)
    except signing.BadSignature, User.DoesNotExist, KeyError, TypeError, ValidationError:
        return None
    if user.email != data.get("e"):
        return None
    if not user.email_verified:
        user.email_verified_at = timezone.now()
        user.save(update_fields=["email_verified_at", "updated_at"])
    return user


# --- Sessions -----------------------------------------------------------------


def active_sessions(user: User):
    """Refresh tokens that can still be used: one per signed-in browser/device."""
    return OutstandingToken.objects.filter(
        user=user, blacklistedtoken__isnull=True, expires_at__gt=timezone.now()
    ).order_by("-created_at")


def login(*, identifier: str, password: str, request=None) -> User:
    user = authenticate(request, username=identifier, password=password)
    if user is None:
        logger.info("Failed login attempt")  # no identifier: avoid logging personal data
        raise InvalidCredentials()
    user.last_login = timezone.now()
    user.save(update_fields=["last_login"])
    return user


@transaction.atomic
def set_password(user: User, new_password: str) -> None:
    """Change the password and end every existing session.

    Access tokens die because SIMPLE_JWT["CHECK_REVOKE_TOKEN"] ties them to the
    password hash; refresh tokens are blacklisted explicitly.
    """
    user.set_password(new_password)
    user.save(update_fields=["password", "updated_at"])
    revoke_refresh_tokens(user)


@transaction.atomic
def deactivate_user(user: User) -> None:
    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])
    revoke_refresh_tokens(user)


def send_password_reset(email: str) -> None:
    """Email a single-use reset link. Silently does nothing for unknown/inactive accounts."""
    user = User.objects.filter(email=email.strip().lower(), is_active=True).first()
    if user is None or not user.has_usable_password():
        return
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    from apps.notifications.models import Notification
    from apps.notifications.services import notify

    notify(
        user,
        Notification.Kind.PASSWORD_RESET,
        link=link,
        minutes=settings.PASSWORD_RESET_TIMEOUT // 60,
    )


def get_user_for_reset(uid: str, token: str) -> User | None:
    """Return the user a reset link belongs to, or None if the link is invalid/expired."""
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except User.DoesNotExist, ValidationError, ValueError, TypeError, OverflowError:
        # ValidationError: the decoded uid is not a UUID.
        return None
    return user if default_token_generator.check_token(user, token) else None
