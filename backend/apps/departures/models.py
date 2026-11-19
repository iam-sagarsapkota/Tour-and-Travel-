from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Coalesce
from django.utils import timezone

from common.models import BaseModel, PublishStatus


def bookable_q(prefix: str = "", now=None) -> Q:
    """Conditions that make a departure bookable right now.

    ``prefix`` lets the same rule be used from another model's queryset,
    e.g. ``bookable_q("departures__")`` on Adventure. The adventure's own
    publication status is checked separately by callers.
    """
    now = now or timezone.now()
    return Q(
        **{
            f"{prefix}status": Departure.Status.OPEN,
            f"{prefix}booking_cutoff__gt": now,
            f"{prefix}start_date__gte": timezone.localdate(now),
            f"{prefix}seats_reserved__lt": F(f"{prefix}capacity"),
        }
    )


class DepartureQuerySet(models.QuerySet):
    def bookable(self, now=None):
        return self.filter(
            bookable_q(now=now),
            adventure__status=PublishStatus.PUBLISHED,
            adventure__destination__status=PublishStatus.PUBLISHED,
        )

    def needing_minimum_decision(self, now=None):
        """Queryset twin of ``Departure.needs_minimum_decision``."""
        now = now or timezone.now()
        return self.annotate(
            _minimum=Coalesce("min_participants", "adventure__min_participants")
        ).filter(
            status__in=[Departure.Status.OPEN, Departure.Status.CLOSED],
            booking_cutoff__lte=now,
            start_date__gte=timezone.localdate(now),
            seats_reserved__lt=F("_minimum"),
        )

    def upcoming(self):
        """Not cancelled and not yet started - shown on the event page, bookable or not."""
        return self.filter(
            status__in=[Departure.Status.OPEN, Departure.Status.CLOSED],
            start_date__gte=timezone.localdate(),
        )


class Departure(BaseModel):
    """A scheduled instance of an adventure with its own dates, capacity and price."""

    class Status(models.TextChoices):
        OPEN = "open", "Open for booking"
        CLOSED = "closed", "Closed for booking"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    adventure = models.ForeignKey(
        "adventures.Adventure", on_delete=models.PROTECT, related_name="departures"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    booking_cutoff = models.DateTimeField(help_text="Bookings close at this moment (UTC).")
    capacity = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    min_participants = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        help_text="Leave empty to use the adventure's minimum.",
    )
    price_override = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text="Per-person price for this departure. Empty = adventure base price.",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True
    )
    # Cached count of seats held by pending + confirmed bookings. Only the booking
    # service changes it, inside a transaction holding a row lock on this departure
    # (phase 4). The check constraint below is the last line of defence against overselling.
    seats_reserved = models.PositiveSmallIntegerField(default=0)

    objects = DepartureQuerySet.as_manager()

    class Meta:
        ordering = ["start_date"]
        indexes = [
            models.Index(fields=["adventure", "start_date"]),
            models.Index(fields=["status", "start_date"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(seats_reserved__lte=F("capacity")),
                name="departure_seats_reserved_within_capacity",
            ),
            models.CheckConstraint(
                condition=Q(capacity__gte=1), name="departure_capacity_positive"
            ),
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")), name="departure_end_not_before_start"
            ),
        ]

    def __str__(self):
        return f"{self.adventure} - {self.start_date}"

    @property
    def price(self) -> Decimal:
        """Per-person price in the adventure's currency."""
        if self.price_override is not None:
            return self.price_override
        return self.adventure.base_price

    @property
    def effective_min_participants(self) -> int:
        return self.min_participants or self.adventure.min_participants

    @property
    def seats_available(self) -> int:
        return max(self.capacity - self.seats_reserved, 0)

    def needs_minimum_decision(self, now=None) -> bool:
        """Booking has closed and the minimum group size was not reached.

        Product decision: nothing happens automatically; an admin decides whether
        the departure runs, is rescheduled or is cancelled.
        """
        now = now or timezone.now()
        return (
            self.status in (self.Status.OPEN, self.Status.CLOSED)
            and self.booking_cutoff <= now
            and self.start_date >= timezone.localdate(now)
            and self.seats_reserved < self.effective_min_participants
        )

    def is_open_for_booking(self, now=None) -> bool:
        """Status, dates and publication allow booking (seat count not considered)."""
        now = now or timezone.now()
        return (
            self.status == self.Status.OPEN
            and self.booking_cutoff > now
            and self.start_date >= timezone.localdate(now)
            and self.adventure.status == PublishStatus.PUBLISHED
            and self.adventure.destination.status == PublishStatus.PUBLISHED
        )

    def is_bookable(self, now=None) -> bool:
        """Python twin of ``DepartureQuerySet.bookable`` for an already-loaded row."""
        return self.is_open_for_booking(now) and self.seats_reserved < self.capacity


# Importable alias (used by SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]).
DepartureStatus = Departure.Status
