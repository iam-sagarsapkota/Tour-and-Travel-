from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.bookings.models import Booking
from apps.operations.audit import record
from common.permissions import IsAdmin

from . import services
from .gateways import enabled_gateways
from .models import Payment, PaymentAttempt
from .serializers import (
    AdminPaymentSerializer,
    InitiateSerializer,
    PaymentSerializer,
    ProviderSerializer,
    RedirectSerializer,
    ResolveSerializer,
    VerifyResultSerializer,
    VerifySerializer,
)

PAYMENT_RELATED = ("booking__departure__adventure", "booking__user")


class ProvidersView(APIView):
    """Payment methods currently enabled on this server."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses=ProviderSerializer(many=True))
    def get(self, request):
        return Response([{"code": g.code, "name": g.name} for g in enabled_gateways()])


class InitiateView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_scope = "payments"

    @extend_schema(request=InitiateSerializer, responses=RedirectSerializer)
    def post(self, request):
        serializer = InitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = get_object_or_404(
            Booking.objects.select_related("departure__adventure"),
            pk=serializer.validated_data["booking"],
            user=request.user,
        )
        attempt, redirect = services.initiate_payment(
            booking=booking, provider=serializer.validated_data["provider"]
        )
        return Response({"attempt": attempt.pk, **redirect})


class VerifyView(APIView):
    """Called by our frontend when the browser returns from a gateway."""

    permission_classes = [IsAuthenticated]
    throttle_scope = "payments"

    @extend_schema(request=VerifySerializer, responses=VerifyResultSerializer)
    def post(self, request):
        serializer = VerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attempt = get_object_or_404(
            PaymentAttempt.objects.select_related("payment"),
            pk=serializer.validated_data["attempt"],
            payment__booking__user=request.user,
        )
        if serializer.validated_data.get("params"):
            services.record_return(attempt, serializer.validated_data["params"])
        attempt = services.verify_attempt(attempt)
        payment = Payment.objects.select_related(*PAYMENT_RELATED).get(pk=attempt.payment_id)
        return Response(
            {
                "attempt": VerifyResultSerializer().fields["attempt"].to_representation(attempt),
                "payment": PaymentSerializer(payment).data,
            }
        )


class PaymentHistoryView(generics.ListAPIView):
    """The signed-in traveller's payments, newest first."""

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends: list = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Payment.objects.none()
        return (
            Payment.objects.filter(booking__user=self.request.user)
            .select_related(*PAYMENT_RELATED)
            .prefetch_related("attempts")
        )


class AdminPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    """Transactions, verification history and reconciliation. Amounts are read-only."""

    serializer_class = AdminPaymentSerializer
    permission_classes = [IsAdmin]
    queryset = Payment.objects.select_related(*PAYMENT_RELATED).prefetch_related("attempts")
    filterset_fields = ["status", "provider", "needs_attention"]
    search_fields = ["booking__reference", "gateway_reference", "attempts__reference"]
    ordering_fields = ["created_at", "paid_at", "amount"]

    @extend_schema(request=None, responses=AdminPaymentSerializer)
    @action(detail=True, methods=["post"])
    def reconcile(self, request, pk=None):
        """Ask the provider again about every attempt of this payment."""
        payment = self.get_object()
        for attempt in payment.attempts.all():
            services.verify_attempt(attempt, force=True)
        record(actor=request.user, action="reconcile", obj=payment, request=request)
        return Response(self.get_serializer(self.get_queryset().get(pk=payment.pk)).data)

    @extend_schema(request=ResolveSerializer, responses=AdminPaymentSerializer)
    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Clear the needs-attention flag after handling it (e.g. refunding at the provider)."""
        serializer = ResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = services.resolve_attention(
            self.get_object(), actor=request.user, note=serializer.validated_data["note"]
        )
        record(
            actor=request.user,
            action="resolve",
            obj=payment,
            note=serializer.validated_data["note"],
            request=request,
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=payment.pk)).data)
