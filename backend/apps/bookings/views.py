from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.operations.audit import record
from common.permissions import IsAdmin

from . import services
from .models import Booking
from .serializers import (
    AdminBookingSerializer,
    AdminCancelSerializer,
    BookingCreateSerializer,
    BookingSerializer,
    QuoteRequestSerializer,
    QuoteSerializer,
)

BOOKING_RELATED = ("departure__adventure__destination", "user", "payment")


def _scope_filter(scope: str | None) -> Q | None:
    today = timezone.localdate()
    return {
        "upcoming": Q(status__in=Booking.HOLDING, departure__end_date__gte=today),
        "past": Q(status=Booking.Status.CONFIRMED, departure__end_date__lt=today),
        "cancelled": Q(status__in=[Booking.Status.CANCELLED, Booking.Status.EXPIRED]),
    }.get(scope or "")


class BookingViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """The signed-in traveller's own bookings. Other users' bookings are 404."""

    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends: list = []
    queryset = Booking.objects.none()  # for schema generation; see get_queryset

    def get_throttles(self):
        if self.action == "create":
            self.throttle_scope = "bookings_create"
        return super().get_throttles()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Booking.objects.none()
        queryset = (
            Booking.objects.filter(user=self.request.user)
            .select_related(*BOOKING_RELATED)
            .prefetch_related("participants")
        )
        scope = _scope_filter(self.request.query_params.get("scope"))
        return queryset.filter(scope) if scope is not None else queryset

    @extend_schema(
        parameters=[
            OpenApiParameter("scope", str, enum=["upcoming", "past", "cancelled"]),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(request=BookingCreateSerializer, responses={201: BookingSerializer})
    def create(self, request, *args, **kwargs):
        serializer = BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        booking = services.create_booking(
            user=request.user,
            departure_id=data["departure"].pk,
            participants=data["participants"],
            policy_accepted=data["policy_accepted"],
        )
        booking = self.get_queryset().get(pk=booking.pk)
        return Response(self.get_serializer(booking).data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses=BookingSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        booking = services.cancel_booking(self.get_object(), actor=request.user)
        return Response(self.get_serializer(self.get_queryset().get(pk=booking.pk)).data)

    @extend_schema(request=QuoteRequestSerializer, responses=QuoteSerializer)
    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def quote(self, request):
        """Price a party size for a departure without reserving anything."""
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.quote(
            serializer.validated_data["departure"], serializer.validated_data["participant_count"]
        )
        return Response(QuoteSerializer(result).data)


class AdminBookingViewSet(viewsets.ReadOnlyModelViewSet):
    """Admin view of all bookings. Totals and history are read-only; only cancel is allowed."""

    serializer_class = AdminBookingSerializer
    permission_classes = [IsAdmin]
    queryset = Booking.objects.select_related(*BOOKING_RELATED).prefetch_related(
        "participants", "events__actor"
    )
    filterset_fields = ["status", "departure", "departure__adventure"]
    search_fields = ["reference", "user__full_name", "user__email", "user__phone"]
    ordering_fields = ["created_at", "total_amount"]

    @extend_schema(request=AdminCancelSerializer, responses=AdminBookingSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        serializer = AdminCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = services.cancel_booking(
            self.get_object(), actor=request.user, reason=serializer.validated_data["reason"]
        )
        record(
            actor=request.user,
            action="cancel",
            obj=booking,
            note=serializer.validated_data["reason"],
            request=request,
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=booking.pk)).data)
