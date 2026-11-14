from django.db.models import Exists, F, OuterRef
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from apps.departures.models import Departure, bookable_q

from .models import Adventure


class EventFilter(filters.FilterSet):
    """Filters for the public event listing (PRD 5.1)."""

    difficulty = filters.CharFilter(method="filter_difficulty")
    activity_type = filters.ChoiceFilter(choices=Adventure.ActivityType.choices)
    destination = filters.CharFilter(field_name="destination__slug")
    region = filters.CharFilter(field_name="destination__region", lookup_expr="iexact")
    category = filters.CharFilter(field_name="category__slug")
    duration_min = filters.NumberFilter(field_name="duration_days", lookup_expr="gte")
    duration_max = filters.NumberFilter(field_name="duration_days", lookup_expr="lte")
    price_min = filters.NumberFilter(field_name="starting_price", lookup_expr="gte")
    price_max = filters.NumberFilter(field_name="starting_price", lookup_expr="lte")
    departure_from = filters.DateFilter(method="filter_departure_window")
    departure_to = filters.DateFilter(method="filter_departure_window")
    available = filters.BooleanFilter(method="filter_available")
    featured = filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Adventure
        fields: list[str] = []

    def filter_difficulty(self, queryset, name, value):
        """Accepts one level or a comma-separated list: ``difficulty=easy,moderate``."""
        levels = [level.strip() for level in value.split(",") if level.strip()]
        invalid = set(levels) - set(Adventure.Difficulty.values)
        if invalid:
            raise ValidationError(
                {"difficulty": [f"Unknown difficulty: {', '.join(sorted(invalid))}."]}
            )
        return queryset.filter(difficulty__in=levels)

    def filter_departure_window(self, queryset, name, value):
        """Keep events with a bookable departure starting inside the requested window."""
        start = self.form.cleaned_data.get("departure_from")
        end = self.form.cleaned_data.get("departure_to")
        if name == "departure_to" and start:
            return queryset  # both bounds were applied together under departure_from
        # Both bounds must hold for the same departure, hence one subquery.
        departures = Departure.objects.filter(bookable_q(), adventure=OuterRef("pk"))
        if start:
            departures = departures.filter(start_date__gte=start)
        if end:
            departures = departures.filter(start_date__lte=end)
        return queryset.filter(Exists(departures))

    def filter_available(self, queryset, name, value):
        return queryset.filter(next_departure_date__isnull=not value)


ORDERINGS = {
    "price": [F("starting_price").asc(), "title"],
    "-price": [F("starting_price").desc(), "title"],
    "date": [F("next_departure_date").asc(nulls_last=True), "title"],
    "-date": [F("next_departure_date").desc(nulls_last=True), "title"],
    "popularity": ["popularity", "title"],
    "-popularity": ["-popularity", "title"],
    "duration": ["duration_days", "title"],
    "-duration": ["-duration_days", "title"],
}


def apply_event_ordering(queryset, ordering: str | None):
    """Whitelisted sorting; anything else is a 400 rather than being passed to the ORM."""
    if not ordering:
        return queryset.order_by("-is_featured", "-popularity", "title")
    if ordering not in ORDERINGS:
        raise ValidationError({"ordering": [f"Choose one of: {', '.join(ORDERINGS)}."]})
    return queryset.order_by(*ORDERINGS[ordering])
