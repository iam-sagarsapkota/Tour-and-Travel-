from django_filters import rest_framework as filters
from rest_framework import viewsets

from apps.operations.audit import AuditedViewSetMixin
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


class DepartureAdminViewSet(AuditedViewSetMixin, viewsets.ModelViewSet):
    """Schedule management. Departures are cancelled via ``status``; there is no delete."""

    queryset = Departure.objects.select_related("adventure")
    serializer_class = DepartureAdminSerializer
    permission_classes = [IsAdmin]
    http_method_names = ["get", "post", "patch", "head", "options"]
    filterset_class = DepartureAdminFilter
    ordering_fields = ["start_date", "created_at"]

    def after_update(self, instance, changes):
        """Tell booked travellers when dates change or the departure is cancelled."""
        from apps.notifications.services import notify_travellers_of_departure_change

        messages = []
        if "start_date" in changes or "end_date" in changes:
            messages.append(
                f"New dates: {instance.start_date:%d %b %Y} - {instance.end_date:%d %b %Y}."
            )
        if changes.get("status", [None, None])[1] == Departure.Status.CANCELLED:
            messages.append(
                "This departure has been cancelled. Our team will contact you about "
                "moving to another date or a refund."
            )
        if messages:
            notify_travellers_of_departure_change(instance, messages)
