from rest_framework import serializers

from apps.departures.models import Departure

from . import services
from .models import Booking, BookingEvent, BookingParticipant


class ParticipantSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(max_length=150)

    class Meta:
        model = BookingParticipant
        fields = ["full_name", "nationality", "date_of_birth", "is_lead"]
        read_only_fields = ["is_lead"]

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Enter the traveller's full name.")
        return value


class BookingCreateSerializer(serializers.Serializer):
    """Client input. Prices, totals and status are never accepted from the client."""

    departure = serializers.PrimaryKeyRelatedField(queryset=Departure.objects.all())
    participants = ParticipantSerializer(many=True, allow_empty=False, max_length=100)
    policy_accepted = serializers.BooleanField()

    def validate_policy_accepted(self, value):
        if not value:
            raise serializers.ValidationError(
                "Please confirm you have read the booking and cancellation policy."
            )
        return value


class QuoteRequestSerializer(serializers.Serializer):
    departure = serializers.PrimaryKeyRelatedField(
        queryset=Departure.objects.select_related("adventure", "adventure__destination")
    )
    participant_count = serializers.IntegerField(min_value=1, max_value=100)


class QuoteSerializer(serializers.Serializer):
    departure = serializers.UUIDField()
    participant_count = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    currency = serializers.CharField()
    seats_available = serializers.IntegerField()
    is_bookable = serializers.BooleanField()


class BookingDepartureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departure
        fields = ["id", "start_date", "end_date", "status"]


class BookingAdventureSerializer(serializers.Serializer):
    title = serializers.CharField()
    slug = serializers.CharField()
    cover_image = serializers.ImageField()
    duration_days = serializers.IntegerField()
    destination = serializers.CharField(source="destination.name")
    cancellation_policy = serializers.CharField()


class BookingSerializer(serializers.ModelSerializer):
    departure = BookingDepartureSerializer(read_only=True)
    adventure = BookingAdventureSerializer(source="departure.adventure", read_only=True)
    participants = ParticipantSerializer(many=True, read_only=True)
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "reference",
            "status",
            "departure",
            "adventure",
            "participant_count",
            "unit_price",
            "total_amount",
            "currency",
            "participants",
            "expires_at",
            "confirmed_at",
            "cancelled_at",
            "cancellation_reason",
            "created_at",
            "can_cancel",
        ]
        read_only_fields = fields

    def get_can_cancel(self, obj) -> bool:
        return services.can_user_cancel(obj)


class BookingEventSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.full_name", default=None, read_only=True)

    class Meta:
        model = BookingEvent
        fields = ["from_status", "to_status", "actor", "note", "created_at"]


class BookingUserSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    full_name = serializers.CharField()
    email = serializers.EmailField(allow_null=True)
    phone = serializers.CharField(allow_null=True)


class AdminBookingSerializer(BookingSerializer):
    user = BookingUserSerializer(read_only=True)
    history = BookingEventSerializer(source="events", many=True, read_only=True)

    class Meta(BookingSerializer.Meta):
        fields = [*BookingSerializer.Meta.fields, "user", "history", "policy_accepted_at"]
        read_only_fields = fields


class AdminCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)
