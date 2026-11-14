from decimal import Decimal

from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from common.models import BaseModel, PublishStatus
from common.uploads import UploadTo, validate_image_upload

currency_validator = RegexValidator(r"^[A-Z]{3}$", "Use a 3-letter ISO 4217 code, e.g. NPR.")


class AdventureCategory(BaseModel):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "name"]
        verbose_name_plural = "adventure categories"

    def __str__(self):
        return self.name


class Adventure(BaseModel):
    """The reusable catalog product. Scheduled instances are ``departures.Departure``."""

    class ActivityType(models.TextChoices):
        TREKKING = "trekking", "Trekking"
        HIKING = "hiking", "Hiking"
        OTHER = "other", "Other adventure"

    class Difficulty(models.TextChoices):
        # Assigned by an administrator from terrain, altitude, duration, exposure
        # and physical demand - not from duration alone.
        EASY = "easy", "Easy"
        MODERATE = "moderate", "Moderate"
        DIFFICULT = "difficult", "Difficult"
        EXTREME = "extreme", "Extreme"

    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=160, unique=True)
    destination = models.ForeignKey(
        "destinations.Destination", on_delete=models.PROTECT, related_name="adventures"
    )
    category = models.ForeignKey(
        AdventureCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adventures",
    )
    activity_type = models.CharField(
        max_length=10, choices=ActivityType.choices, default=ActivityType.TREKKING, db_index=True
    )
    summary = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(
        upload_to=UploadTo("adventures/covers"), blank=True, validators=[validate_image_upload]
    )

    difficulty = models.CharField(max_length=10, choices=Difficulty.choices, db_index=True)
    duration_days = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    distance_km = models.DecimalField(
        max_digits=6,
        decimal_places=1,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.1"))],
    )
    max_elevation_m = models.PositiveIntegerField(null=True, blank=True)
    start_point = models.CharField(max_length=120, blank=True)
    end_point = models.CharField(max_length=120, blank=True)
    route_summary = models.TextField(blank=True)
    route_map_url = models.URLField(blank=True)

    base_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))]
    )
    currency = models.CharField(max_length=3, default="NPR", validators=[currency_validator])
    min_participants = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    max_group_size = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1)]
    )
    solo_friendly = models.BooleanField(default=True)

    inclusions = models.JSONField(default=list, blank=True)
    exclusions = models.JSONField(default=list, blank=True)
    accommodation = models.TextField(blank=True)
    transportation = models.TextField(blank=True)
    meals = models.TextField(blank=True)
    equipment = models.TextField(blank=True)
    safety_guidance = models.TextField(blank=True)
    meeting_point = models.CharField(max_length=255, blank=True)
    organizer = models.CharField(max_length=120, blank=True)
    cancellation_policy = models.TextField(blank=True)

    is_featured = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10, choices=PublishStatus.choices, default=PublishStatus.DRAFT, db_index=True
    )
    published_at = models.DateTimeField(null=True, blank=True)
    # Cached counter used only for "sort by popularity". The booking service
    # increments it on confirmed bookings (phase 4); it is not client-editable.
    popularity = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-is_featured", "-popularity", "title"]
        indexes = [
            models.Index(fields=["status", "difficulty"]),
            models.Index(fields=["status", "duration_days"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(base_price__gt=0), name="adventure_base_price_positive"
            ),
            models.CheckConstraint(
                condition=models.Q(duration_days__gte=1), name="adventure_duration_positive"
            ),
        ]

    def __str__(self):
        return self.title


class AdventureImage(BaseModel):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(
        upload_to=UploadTo("adventures/gallery"), validators=[validate_image_upload]
    )
    alt_text = models.CharField(max_length=160, blank=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "created_at"]

    def __str__(self):
        return self.alt_text or f"Image of {self.adventure}"


class ItineraryDay(models.Model):
    adventure = models.ForeignKey(Adventure, on_delete=models.CASCADE, related_name="itinerary")
    day_number = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    overnight_location = models.CharField(max_length=120, blank=True)
    altitude_m = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["day_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["adventure", "day_number"], name="itinerary_unique_day_per_adventure"
            )
        ]

    def __str__(self):
        return f"Day {self.day_number}: {self.title}"
