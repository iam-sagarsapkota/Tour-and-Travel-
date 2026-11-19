import datetime as dt
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from .models import Departure


def start_of_day(date: dt.date) -> dt.datetime:
    """Midnight at the start of ``date`` in the business time zone (Nepal)."""
    return dt.datetime.combine(date, dt.time.min, tzinfo=ZoneInfo(settings.BUSINESS_TIME_ZONE))


class PublicDepartureSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_participants = serializers.IntegerField(source="effective_min_participants")
    seats_available = serializers.IntegerField(read_only=True)
    is_bookable = serializers.SerializerMethodField()

    class Meta:
        model = Departure
        fields = [
            "id",
            "start_date",
            "end_date",
            "booking_cutoff",
            "price",
            "capacity",
            "seats_available",
            "min_participants",
            "status",
            "is_bookable",
        ]

    def get_is_bookable(self, obj) -> bool:
        return obj.is_bookable()


class DepartureAdminSerializer(serializers.ModelSerializer):
    adventure_title = serializers.CharField(source="adventure.title", read_only=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    seats_available = serializers.IntegerField(read_only=True)
    min_participants_met = serializers.SerializerMethodField()
    needs_decision = serializers.SerializerMethodField()

    class Meta:
        model = Departure
        fields = [
            "id",
            "adventure",
            "adventure_title",
            "start_date",
            "end_date",
            "booking_cutoff",
            "capacity",
            "min_participants",
            "price_override",
            "price",
            "status",
            "seats_reserved",
            "seats_available",
            "min_participants_met",
            "needs_decision",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "seats_reserved", "created_at", "updated_at"]
        extra_kwargs = {
            "end_date": {"required": False},
            "booking_cutoff": {"required": False},
        }

    def get_min_participants_met(self, obj) -> bool:
        return obj.seats_reserved >= obj.effective_min_participants

    def get_needs_decision(self, obj) -> bool:
        """Bookings have closed below the minimum: an admin must run, move or cancel it."""
        return obj.needs_minimum_decision()

    def validate(self, attrs):
        instance = self.instance
        if instance is not None:
            # A departure belongs to one adventure for life; bookings reference it.
            attrs.pop("adventure", None)
        adventure = instance.adventure if instance else attrs["adventure"]

        def current(field):
            return attrs.get(field, getattr(instance, field, None))

        errors = {}
        start = current("start_date")
        if "start_date" in attrs and start < timezone.localdate():
            errors["start_date"] = ["Start date cannot be in the past."]

        if current("end_date") is None:
            attrs["end_date"] = start + dt.timedelta(days=adventure.duration_days - 1)
        elif current("end_date") < start:
            errors["end_date"] = ["End date cannot be before the start date."]

        if current("booking_cutoff") is None:
            attrs["booking_cutoff"] = start_of_day(start) - dt.timedelta(
                days=settings.DEFAULT_BOOKING_CUTOFF_DAYS
            )
        elif current("booking_cutoff") >= start_of_day(start) + dt.timedelta(days=1):
            errors["booking_cutoff"] = ["Booking cutoff must not be after the start date."]

        capacity = current("capacity")
        minimum = current("min_participants")
        if minimum and capacity and minimum > capacity:
            errors["min_participants"] = ["Cannot exceed capacity."]
        if instance and capacity is not None and capacity < instance.seats_reserved:
            errors["capacity"] = [
                f"{instance.seats_reserved} seats are already reserved; "
                "capacity cannot go below that."
            ]

        if errors:
            raise serializers.ValidationError(errors)
        return attrs
