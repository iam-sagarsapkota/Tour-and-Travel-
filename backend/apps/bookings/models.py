from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q

from common.models import BaseModel


class Booking(BaseModel):
    """One reservation of one or more places on a departure.

    Prices are copied from the departure at booking time (``unit_price``) and the
    total is fixed by a check constraint, so later catalog price changes never
    alter an existing booking. Bookings are never deleted.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"  # seats held until expires_at
        CONFIRMED = "confirmed", "Confirmed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"  # hold lapsed without payment

    # Statuses that occupy seats on the departure.
    HOLDING = (Status.PENDING, Status.CONFIRMED)

    reference = models.CharField(max_length=12, unique=True, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings"
    )
    departure = models.ForeignKey(
        "departures.Departure", on_delete=models.PROTECT, related_name="bookings"
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    participant_count = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)

    policy_accepted_at = models.DateTimeField()
    expires_at = models.DateTimeField(
        null=True, blank=True, help_text="When an unpaid hold is released."
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "expires_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["departure", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(participant_count__gte=1), name="booking_has_participants"
            ),
            models.CheckConstraint(condition=Q(unit_price__gt=0), name="booking_price_positive"),
            models.CheckConstraint(
                condition=Q(total_amount=F("unit_price") * F("participant_count")),
                name="booking_total_matches_price",
            ),
            models.CheckConstraint(
                condition=~Q(status="pending") | Q(expires_at__isnull=False),
                name="booking_pending_has_expiry",
            ),
        ]

    def __str__(self):
        return self.reference


class BookingParticipant(models.Model):
    """Traveller on a booking. Only what operating the trip needs is collected."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="participants")
    position = models.PositiveSmallIntegerField()
    full_name = models.CharField(max_length=150)
    nationality = models.CharField(max_length=80, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    is_lead = models.BooleanField(default=False)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["booking", "position"], name="participant_unique_position"
            )
        ]

    def __str__(self):
        return self.full_name


class BookingEvent(models.Model):
    """Append-only history of status changes: who, when, from what, to what, and why."""

    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Empty for automatic changes (e.g. hold expiry).",
    )
    from_status = models.CharField(max_length=10, blank=True)
    to_status = models.CharField(max_length=10)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.booking}: {self.from_status or '-'} -> {self.to_status}"


# Importable alias (used by SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]).
BookingStatus = Booking.Status
