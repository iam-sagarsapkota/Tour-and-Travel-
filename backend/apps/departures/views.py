from django_filters import rest_framework as filters
from rest_framework import viewsets

from common.permissions import IsAdmin

from .models import Departure
from .serializers import DepartureAdminSerializer


class DepartureAdminFilter(filters.FilterSet):
    start_date__gte = filters.DateFilter(field_name="start_date", lookup_expr="gte")
    start_date__lte = filters.DateFilter(field_name="start_date", lookup_expr="lte")
    needs_decision = filters.BooleanFilter(method="filter_needs_decision")

    class Meta:
        model = Departure
        fields = ["adventure", "status"]

    def filter_needs_decision(self, queryset, name, value):
        flagged = Departure.objects.needing_minimum_decision().values("pk")
        return queryset.filter(pk__in=flagged) if value else queryset.exclude(pk__in=flagged)


class DepartureAdminViewSet(viewsets.ModelViewSet):
    """Schedule management. Departures are cancelled via ``status``; there is no delete."""

    queryset = Departure.objects.select_related("adventure")
    serializer_class = DepartureAdminSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_class = DepartureAdminFilter
    ordering_fields = ["start_date", "created_at"]
