from django.db import transaction
from rest_framework import serializers

from apps.departures.serializers import PublicDepartureSerializer
from apps.destinations.serializers import DestinationSummarySerializer
from common.models import generate_unique_slug

from .models import Adventure, AdventureCategory, AdventureImage, ItineraryDay
from .selectors import related_events

# --- Public -----------------------------------------------------------------


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureCategory
        fields = ["id", "name", "slug", "description"]


class CategorySummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureCategory
        fields = ["name", "slug"]


class NextDepartureSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    seats_available = serializers.IntegerField()


class EventCardSerializer(serializers.ModelSerializer):
    """Summary shown to everyone, including guests. Requires ``selectors.public_events()``."""

    destination = DestinationSummarySerializer(read_only=True)
    category = CategorySummarySerializer(read_only=True)
    starting_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    next_departure = serializers.SerializerMethodField()
    has_availability = serializers.SerializerMethodField()

    class Meta:
        model = Adventure
        fields = [
            "id",
            "title",
            "slug",
            "summary",
            "destination",
            "category",
            "activity_type",
            "cover_image",
            "difficulty",
            "duration_days",
            "starting_price",
            "currency",
            "next_departure",
            "has_availability",
            "is_featured",
        ]

    def get_next_departure(self, obj) -> dict | None:
        departures = obj.bookable_departures
        return NextDepartureSerializer(departures[0]).data if departures else None

    def get_has_availability(self, obj) -> bool:
        return bool(obj.bookable_departures)


class AdventureImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureImage
        fields = ["id", "image", "alt_text", "display_order"]


class ItineraryDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ItineraryDay
        fields = ["day_number", "title", "description", "overnight_location", "altitude_m"]


class EventDetailSerializer(EventCardSerializer):
    """Full event page - authenticated users only. Requires ``public_event_detail()``."""

    images = AdventureImageSerializer(many=True, read_only=True)
    itinerary = ItineraryDaySerializer(many=True, read_only=True)
    departures = PublicDepartureSerializer(source="upcoming_departures", many=True, read_only=True)
    related = serializers.SerializerMethodField()

    class Meta(EventCardSerializer.Meta):
        fields = [
            *EventCardSerializer.Meta.fields,
            "description",
            "images",
            "distance_km",
            "max_elevation_m",
            "start_point",
            "end_point",
            "route_summary",
            "route_map_url",
            "base_price",
            "min_participants",
            "max_group_size",
            "solo_friendly",
            "inclusions",
            "exclusions",
            "accommodation",
            "transportation",
            "meals",
            "equipment",
            "safety_guidance",
            "meeting_point",
            "organizer",
            "cancellation_policy",
            "itinerary",
            "departures",
            "related",
        ]

    def get_related(self, obj) -> list[dict]:
        return EventCardSerializer(related_events(obj), many=True, context=self.context).data


# --- Admin ------------------------------------------------------------------


class CategoryAdminSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=80, required=False)

    class Meta:
        model = AdventureCategory
        fields = ["id", "name", "slug", "description", "display_order", "is_active"]

    def validate_slug(self, value):
        others = AdventureCategory.objects.exclude(pk=self.instance.pk if self.instance else None)
        if others.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already in use.")
        return value

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = generate_unique_slug(
                AdventureCategory, validated_data["name"], max_length=80
            )
        return super().create(validated_data)


class AdventureImageAdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdventureImage
        fields = ["id", "adventure", "image", "alt_text", "display_order", "created_at"]
        read_only_fields = ["id", "created_at"]


class AdventureAdminSerializer(serializers.ModelSerializer):
    """Create/edit adventures. Status changes go through the publish/archive actions."""

    slug = serializers.SlugField(max_length=160, required=False)
    inclusions = serializers.ListField(child=serializers.CharField(max_length=200), required=False)
    exclusions = serializers.ListField(child=serializers.CharField(max_length=200), required=False)
    itinerary = ItineraryDaySerializer(many=True, required=False)
    images = AdventureImageSerializer(many=True, read_only=True)

    class Meta:
        model = Adventure
        exclude = ["popularity"]
        read_only_fields = ["id", "status", "published_at", "created_at", "updated_at"]

    def validate_slug(self, value):
        others = Adventure.objects.exclude(pk=self.instance.pk if self.instance else None)
        if others.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already in use.")
        return value

    def validate_itinerary(self, days):
        numbers = [day["day_number"] for day in days]
        if len(numbers) != len(set(numbers)):
            raise serializers.ValidationError("Each day number may appear only once.")
        return days

    def validate(self, attrs):
        def current(field):
            return attrs.get(field, getattr(self.instance, field, None))

        minimum, maximum = current("min_participants"), current("max_group_size")
        if minimum and maximum and minimum > maximum:
            raise serializers.ValidationError(
                {"min_participants": ["Cannot exceed the maximum group size."]}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        days = validated_data.pop("itinerary", [])
        if not validated_data.get("slug"):
            validated_data["slug"] = generate_unique_slug(
                Adventure, validated_data["title"], max_length=160
            )
        adventure = super().create(validated_data)
        self._replace_itinerary(adventure, days)
        return adventure

    @transaction.atomic
    def update(self, instance, validated_data):
        days = validated_data.pop("itinerary", None)
        adventure = super().update(instance, validated_data)
        if days is not None:
            self._replace_itinerary(adventure, days)
        return adventure

    @staticmethod
    def _replace_itinerary(adventure, days):
        adventure.itinerary.all().delete()
        ItineraryDay.objects.bulk_create(ItineraryDay(adventure=adventure, **day) for day in days)
