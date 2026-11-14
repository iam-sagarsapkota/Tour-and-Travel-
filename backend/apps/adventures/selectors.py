"""Read-side querysets for the public catalog."""

from django.db.models import Min, Prefetch
from django.db.models.functions import Coalesce

from apps.departures.models import Departure, bookable_q
from common.models import PublishStatus

from .models import Adventure


def public_events():
    """Published adventures in published destinations, ready for ``EventCardSerializer``.

    Annotations (computed over currently bookable departures only):
      - ``next_departure_date``: earliest bookable start date, or NULL
      - ``starting_price``: cheapest bookable per-person price, else the base price
    ``bookable_departures`` holds those departures in date order (one extra query).
    """
    bookable = bookable_q("departures__")
    return (
        Adventure.objects.filter(
            status=PublishStatus.PUBLISHED, destination__status=PublishStatus.PUBLISHED
        )
        .select_related("destination", "category")
        .annotate(
            next_departure_date=Min("departures__start_date", filter=bookable),
            starting_price=Coalesce(
                Min(Coalesce("departures__price_override", "base_price"), filter=bookable),
                "base_price",
            ),
        )
        .prefetch_related(
            Prefetch(
                "departures",
                queryset=Departure.objects.filter(bookable_q()).order_by("start_date"),
                to_attr="bookable_departures",
            )
        )
        .order_by("-is_featured", "-popularity", "title")  # aggregation drops Meta.ordering
    )


def public_event_detail():
    return public_events().prefetch_related(
        "images",
        "itinerary",
        Prefetch(
            "departures",
            queryset=Departure.objects.upcoming().order_by("start_date"),
            to_attr="upcoming_departures",
        ),
    )


def related_events(adventure, limit: int = 4):
    """Other public events in the same destination first, then the same category."""
    same_destination = list(
        public_events()
        .filter(destination=adventure.destination_id)
        .exclude(pk=adventure.pk)[:limit]
    )
    if len(same_destination) >= limit or adventure.category_id is None:
        return same_destination
    seen = [adventure.pk, *(event.pk for event in same_destination)]
    same_category = public_events().filter(category=adventure.category_id).exclude(pk__in=seen)
    return same_destination + list(same_category[: limit - len(same_destination)])
