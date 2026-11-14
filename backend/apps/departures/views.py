from rest_framework import viewsets

from common.permissions import IsAdmin

from .models import Departure
from .serializers import DepartureAdminSerializer


class DepartureAdminViewSet(viewsets.ModelViewSet):
    """Schedule management. Departures are cancelled via ``status``; there is no delete."""

    queryset = Departure.objects.select_related("adventure")
    serializer_class = DepartureAdminSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_fields = {
        "adventure": ["exact"],
        "status": ["exact"],
        "start_date": ["gte", "lte"],
    }
    ordering_fields = ["start_date", "created_at"]
