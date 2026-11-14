import datetime as dt
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from apps.departures.models import Departure

pytestmark = pytest.mark.django_db

LIST = reverse("catalog_admin:departure-list")


def detail(departure):
    return reverse("catalog_admin:departure-detail", args=[departure.pk])


def future(days):
    return timezone.localdate() + dt.timedelta(days=days)


class TestModel:
    def test_price_falls_back_to_adventure_base_price(self, make_adventure, make_departure):
        adventure = make_adventure(base_price="40000")
        assert make_departure(adventure=adventure).price == Decimal("40000.00")
        override = make_departure(adventure=adventure, price_override="35000")
        assert override.price == Decimal("35000")

    def test_min_participants_falls_back_to_adventure(self, make_adventure, make_departure):
        adventure = make_adventure(min_participants=2)
        assert make_departure(adventure=adventure).effective_min_participants == 2
        assert (
            make_departure(adventure=adventure, min_participants=4).effective_min_participants == 4
        )

    def test_seats_available(self, make_departure):
        assert make_departure(capacity=10, seats_reserved=3).seats_available == 7

    @pytest.mark.parametrize(
        ("overrides", "bookable"),
        [
            ({}, True),
            ({"status": "closed"}, False),
            ({"status": "cancelled"}, False),
            ({"capacity": 4, "seats_reserved": 4}, False),
            ({"booking_cutoff": timezone.now() - dt.timedelta(minutes=1)}, False),
        ],
    )
    def test_is_bookable(self, make_departure, overrides, bookable):
        assert make_departure(**overrides).is_bookable() is bookable

    def test_not_bookable_when_adventure_is_unpublished(self, make_adventure, make_departure):
        departure = make_departure(adventure=make_adventure(status="draft"))
        assert departure.is_bookable() is False

    def test_bookable_queryset_matches_is_bookable(self, make_departure):
        good = make_departure()
        make_departure(status="cancelled")
        make_departure(capacity=1, seats_reserved=1)
        assert list(Departure.objects.bookable()) == [good]


class TestConstraints:
    def test_cannot_reserve_more_seats_than_capacity(self, make_departure):
        with pytest.raises(IntegrityError), transaction.atomic():
            make_departure(capacity=5, seats_reserved=6)

    def test_end_date_cannot_precede_start_date(self, make_departure):
        with pytest.raises(IntegrityError), transaction.atomic():
            make_departure(start_date=future(10), end_date=future(9))

    def test_capacity_must_be_positive(self, make_departure):
        with pytest.raises(IntegrityError), transaction.atomic():
            make_departure(capacity=0)

    def test_deleting_adventure_with_departures_is_blocked(self, make_departure):
        from django.db.models import ProtectedError

        departure = make_departure()
        with pytest.raises(ProtectedError):
            departure.adventure.delete()


class TestAdminApi:
    def payload(self, adventure, **overrides):
        data = {
            "adventure": str(adventure.pk),
            "start_date": future(45).isoformat(),
            "capacity": 12,
        }
        data.update(overrides)
        return data

    def test_requires_admin(self, api, auth_client, user, make_adventure):
        assert api.get(LIST).status_code == 401
        client = auth_client(user)
        assert client.get(LIST).status_code == 403
        assert client.post(LIST, self.payload(make_adventure())).status_code == 403

    def test_create_fills_end_date_and_cutoff_defaults(
        self, auth_client, admin_user, make_adventure
    ):
        adventure = make_adventure(duration_days=6)

        response = auth_client(admin_user).post(LIST, self.payload(adventure))

        assert response.status_code == 201, response.data
        assert response.data["end_date"] == future(50).isoformat()
        assert response.data["status"] == "open"
        assert response.data["seats_reserved"] == 0
        assert response.data["price"] == "25000.00"
        departure = Departure.objects.get(pk=response.data["id"])
        assert departure.booking_cutoff.date() < departure.start_date

    def test_price_override_and_minimum(self, auth_client, admin_user, make_adventure):
        response = auth_client(admin_user).post(
            LIST,
            self.payload(make_adventure(), price_override="19999.50", min_participants=4),
        )
        assert response.status_code == 201
        assert response.data["price"] == "19999.50"
        assert response.data["min_participants"] == 4

    @pytest.mark.parametrize(
        "overrides",
        [
            {"start_date": (timezone.localdate() - dt.timedelta(days=1)).isoformat()},
            {"end_date": future(40).isoformat()},  # before start
            {"capacity": 0},
            {"price_override": "0"},
            {"min_participants": 20},  # above capacity
            {"booking_cutoff": (timezone.now() + dt.timedelta(days=60)).isoformat()},
        ],
    )
    def test_validation(self, auth_client, admin_user, make_adventure, overrides):
        response = auth_client(admin_user).post(LIST, self.payload(make_adventure(), **overrides))
        assert response.status_code == 400, response.data

    def test_seats_reserved_is_read_only(self, auth_client, admin_user, make_adventure):
        response = auth_client(admin_user).post(
            LIST, self.payload(make_adventure(), seats_reserved=5)
        )
        assert response.status_code == 201
        assert response.data["seats_reserved"] == 0

    def test_cannot_shrink_capacity_below_reserved_seats(
        self, auth_client, admin_user, make_departure
    ):
        departure = make_departure(capacity=10, seats_reserved=6)
        client = auth_client(admin_user)

        assert client.patch(detail(departure), {"capacity": 5}).status_code == 400
        assert client.patch(detail(departure), {"capacity": 6}).status_code == 200

    def test_cannot_move_departure_to_another_adventure(
        self, auth_client, admin_user, make_departure, make_adventure
    ):
        departure = make_departure()
        original = departure.adventure_id
        auth_client(admin_user).patch(detail(departure), {"adventure": str(make_adventure().pk)})
        departure.refresh_from_db()
        assert departure.adventure_id == original

    def test_cancel_via_status_and_no_delete(self, auth_client, admin_user, make_departure):
        departure = make_departure()
        client = auth_client(admin_user)

        assert client.patch(detail(departure), {"status": "cancelled"}).status_code == 200
        assert client.delete(detail(departure)).status_code == 405
        departure.refresh_from_db()
        assert departure.status == "cancelled"

    def test_filter_by_adventure_and_status(self, auth_client, admin_user, make_departure):
        first = make_departure()
        make_departure(status="cancelled")
        client = auth_client(admin_user)

        assert client.get(LIST, {"adventure": str(first.adventure_id)}).data["count"] == 1
        assert client.get(LIST, {"status": "cancelled"}).data["count"] == 1
