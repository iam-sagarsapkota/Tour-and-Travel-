from rest_framework import serializers

from common.models import generate_unique_slug

from .models import Destination


class DestinationSummarySerializer(serializers.ModelSerializer):
    """Compact form embedded in event cards."""

    class Meta:
        model = Destination
        fields = ["name", "slug", "region"]


class DestinationListSerializer(serializers.ModelSerializer):
    event_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Destination
        fields = [
            "id",
            "name",
            "slug",
            "region",
            "short_description",
            "cover_image",
            "best_season",
            "event_count",
        ]


class DestinationDetailSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField()

    class Meta:
        model = Destination
        fields = [
            "id",
            "name",
            "slug",
            "region",
            "short_description",
            "description",
            "cover_image",
            "best_season",
            "seasonal_guidance",
            "attractions",
            "permit_info",
            "events",
        ]

    def get_events(self, obj) -> list[dict]:
        # Imported here: adventures depends on destinations, not the other way round.
        from apps.adventures.selectors import public_events
        from apps.adventures.serializers import EventCardSerializer

        events = public_events().filter(destination=obj)
        return EventCardSerializer(events, many=True, context=self.context).data


class DestinationAdminSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(max_length=120, required=False)

    class Meta:
        model = Destination
        fields = [
            "id",
            "name",
            "slug",
            "region",
            "short_description",
            "description",
            "cover_image",
            "best_season",
            "seasonal_guidance",
            "attractions",
            "permit_info",
            "status",
            "display_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_slug(self, value):
        others = Destination.objects.exclude(pk=self.instance.pk if self.instance else None)
        if others.filter(slug=value).exists():
            raise serializers.ValidationError("This slug is already in use.")
        return value

    def create(self, validated_data):
        if not validated_data.get("slug"):
            validated_data["slug"] = generate_unique_slug(Destination, validated_data["name"])
        return super().create(validated_data)
