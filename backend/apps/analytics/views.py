from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.adventures.serializers import EventCardSerializer
from apps.bookings.serializers import BookingSerializer
from common.permissions import IsAdmin

from . import services


class AdminDashboardView(APIView):
    """KPIs, monthly series and operational alerts for administrators."""

    permission_classes = [IsAdmin]

    @extend_schema(
        parameters=[OpenApiParameter("months", int, description="1-24, default 12")],
        responses=inline_serializer("AdminDashboard", {"kpis": serializers.DictField()}),
    )
    def get(self, request):
        try:
            months = int(request.query_params.get("months", 12))
        except ValueError:
            months = 0
        if not 1 <= months <= 24:
            raise ValidationError({"months": ["Choose between 1 and 24 months."]})
        data = services.admin_overview(months=months)
        return Response(_jsonable(data))


class TravellerDashboardView(APIView):
    """The signed-in traveller's overview."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=inline_serializer("TravellerDashboard", {"counts": serializers.DictField()})
    )
    def get(self, request):
        data = services.traveller_overview(request.user)
        context = {"request": request}
        return Response(
            {
                "counts": data["counts"],
                "total_spent": f"{data['total_spent']:.2f}",
                "currency": data["currency"],
                "upcoming": BookingSerializer(data["upcoming"], many=True, context=context).data,
                "pending_payment": BookingSerializer(
                    data["pending_payment"], many=True, context=context
                ).data,
                "recommendations": EventCardSerializer(
                    data["recommendations"], many=True, context=context
                ).data,
            }
        )


def _jsonable(value):
    """Decimals as fixed-point strings, dates as ISO strings, UUIDs as strings."""
    from decimal import Decimal

    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if value.__class__.__name__ == "UUID":
        return str(value)
    return value
