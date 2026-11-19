from django.conf import settings
from django.db import models

from common.models import BaseModel


class Notification(BaseModel):
    """One message to one person. Email today; SMS/WhatsApp are future channels."""

    class Kind(models.TextChoices):
        WELCOME = "welcome", "Welcome"
        EMAIL_VERIFICATION = "email_verification", "Email verification"
        PASSWORD_RESET = "password_reset", "Password reset"
        BOOKING_CONFIRMED = "booking_confirmed", "Booking confirmed"
        PAYMENT_FAILED = "payment_failed", "Payment not completed"
        PAYMENT_NEEDS_REVIEW = "payment_needs_review", "Payment under review"
        BOOKING_CANCELLED = "booking_cancelled", "Booking cancelled"
        BOOKING_EXPIRED = "booking_expired", "Booking hold expired"
        DEPARTURE_CHANGED = "departure_changed", "Departure changed"
        TRIP_REMINDER = "trip_reminder", "Trip reminder"

    # Bodies of these contain single-use links; they are blanked once sent.
    SENSITIVE = (Kind.EMAIL_VERIFICATION, Kind.PASSWORD_RESET)

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=30, choices=Kind.choices, db_index=True)
    channel = models.CharField(max_length=10, default="email")
    recipient = models.CharField(max_length=254, blank=True)
    subject = models.CharField(max_length=200)
    body_text = models.TextField()
    body_html = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    # The same event (e.g. a repeated payment callback) never produces a second message.
    dedupe_key = models.CharField(max_length=120, unique=True, null=True, blank=True)
    booking = models.ForeignKey(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return f"{self.kind} to {self.recipient or self.user}"
