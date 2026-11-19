from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import filters as drf_filters
from rest_framework import generics, mixins, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.operations.audit import AuditedViewSetMixin, record
from common.models import PublishStatus
from common.permissions import IsAdmin

from . import services
from .filters import ORDERINGS, EventFilter, apply_event_ordering
from .models import Adventure, AdventureCategory, AdventureImage
from .selectors import public_event_detail, public_events
from .serializers import (
    AdventureAdminSerializer,
    AdventureImageAdminSerializer,
    CategoryAdminSerializer,
    CategorySerializer,
    EventCardSerializer,
    EventDetailSerializer,
)

# --- Public -----------------------------------------------------------------


@extend_schema(
    parameters=[
        OpenApiParameter("ordering", str, enum=list(ORDERINGS), description="Sort order."),
        OpenApiParameter("search", str, description="Matches title, summary and destination."),
    ]
)
class EventListView(generics.ListAPIView):
    """Public listing of published events (summary cards). Guests allowed."""

    serializer_class = EventCardSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter]
    filterset_class = EventFilter
    search_fields = ["title", "summary", "destination__name", "destination__region"]

    def get_queryset(self):
        return public_events()

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return apply_event_ordering(queryset, self.request.query_params.get("ordering"))


class EventDetailView(generics.RetrieveAPIView):
    """Full event detail. Authentication is enforced here, not only in the frontend."""

    serializer_class = EventDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "slug"

    def get_queryset(self):
        return public_event_detail()


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends: list = []
    queryset = AdventureCategory.objects.filter(is_active=True)


# --- Admin ------------------------------------------------------------------


class CategoryAdminViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Categories are deactivated via ``is_active``; there is no delete."""

    queryset = AdventureCategory.objects.all()
    serializer_class = CategoryAdminSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["is_active"]
    search_fields = ["name"]
    ordering_fields = ["display_order", "name"]


@extend_schema_view(
    publish=extend_schema(request=None, responses=AdventureAdminSerializer),
    unpublish=extend_schema(request=None, responses=AdventureAdminSerializer),
    archive=extend_schema(request=None, responses=AdventureAdminSerializer),
)
class AdventureAdminViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Adventures are archived, never deleted (bookings and payments must stay traceable)."""

    queryset = Adventure.objects.select_related("destination", "category").prefetch_related(
        "itinerary", "images"
    )
    serializer_class = AdventureAdminSerializer
    permission_classes = [IsAdmin]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = ["status", "difficulty", "activity_type", "destination", "category"]
    search_fields = ["title", "slug", "destination__name"]
    ordering_fields = ["title", "created_at", "base_price", "duration_days"]
    ordering = ["-created_at"]

    def _respond(self, adventure):
        record(actor=self.request.user, action=self.action, obj=adventure, request=self.request)
        return Response(self.get_serializer(adventure).data)

    @action(detail=True, methods=["post"])
    def publish(self, request, pk=None):
        return self._respond(services.publish(self.get_object()))

    @action(detail=True, methods=["post"])
    def unpublish(self, request, pk=None):
        return self._respond(services.set_status(self.get_object(), PublishStatus.DRAFT))

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        return self._respond(services.set_status(self.get_object(), PublishStatus.ARCHIVED))


class AdventureImageAdminViewSet(
    AuditedViewSetMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Gallery management (multipart upload)."""

    queryset = AdventureImage.objects.select_related("adventure")
    serializer_class = AdventureImageAdminSerializer
    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]
    filterset_fields = ["adventure"]

    def perform_destroy(self, instance):
        image = instance.image
        record(actor=self.request.user, action="delete", obj=instance, request=self.request)
        instance.delete()
        image.delete(save=False)  # remove the file as well as the row
