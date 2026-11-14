import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.urls import reverse

from apps.adventures.models import Adventure
from apps.departures.models import Departure

pytestmark = pytest.mark.django_db


def test_seed_is_idempotent_and_publicly_listed(api, settings):
    settings.DEBUG = True
    call_command("seed_catalog")
    adventures, departures = Adventure.objects.count(), Departure.objects.count()

    call_command("seed_catalog")

    assert Adventure.objects.count() == adventures > 0
    assert Departure.objects.count() == departures > 0
    response = api.get(reverse("events:event-list"))
    assert response.data["count"] == adventures
    assert all(card["has_availability"] for card in response.data["results"])


def test_seed_refuses_to_run_outside_debug(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("seed_catalog")
