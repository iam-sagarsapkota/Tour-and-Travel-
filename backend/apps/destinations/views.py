from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny

from common.models import PublishStatus
from common.permissions import IsAdmin

from .models import Destination
from .serializers import (
    DestinationAdminSerializer,
    DestinationDetailSerializer,
    DestinationListSerializer,
)


class DestinationViewSet(viewsets.ReadOnlyModelViewSet):
    """Public directory of published destinations."""

    permission_classes = [AllowAny]
    lookup_field = "slug"
    filterset_fields = ["region"]
    search_fields = ["name", "region", "short_description"]
    ordering_fields = ["display_order", "name"]

    def get_queryset(self):
        return (
            Destination.objects.filter(status=PublishStatus.PUBLISHED)
            .annotate(
                event_count=Count(
                    "adventures", filter=Q(adventures__status=PublishStatus.PUBLISHED)
                )
            )
            .order_by("display_order", "name")  # aggregation drops Meta.ordering
        )

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DestinationDetailSerializer
        return DestinationListSerializer


class DestinationAdminViewSet(viewsets.ModelViewSet):
    """Admin management. Destinations are archived via ``status``; there is no delete."""

    queryset = Destination.objects.all()
    serializer_class = DestinationAdminSerializer
    permission_classes = [IsAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["status", "region"]
    search_fields = ["name", "region"]
    ordering_fields = ["display_order", "name", "created_at"]
