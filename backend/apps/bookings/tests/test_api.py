import datetime as dt

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings import services
from apps.bookings.models import Booking  # noqa: F401

pytestmark = pytest.mark.django_db

LIST = reverse("bookings:booking-list")
QUOTE = reverse("bookings:booking-quote")
ADMIN_LIST = reverse("admin_bookings:booking-list")


def detail(booking):
    return reverse("bookings:booking-detail", args=[booking.pk])


def cancel_url(booking):
    return reverse("bookings:booking-cancel", args=[booking.pk])


def payload(departure, count=1, **overrides):
    data = {
        "departure": str(departure.pk),
        "participants": [{"full_name": f"Trekker {n}"} for n in range(count)],
        "policy_accepted": True,
    }
    data.update(overrides)
    return data


def make_booking(user, departure, count=1, **kwargs):
    return services.create_booking(
        user=user,
        departure_id=departure.pk,
        participants=[{"full_name": f"P{n}"} for n in range(count)],
        policy_accepted=True,
        **kwargs,
    )


class TestCreateApi:
    def test_requires_authentication(self, api, make_departure):
        assert api.post(LIST, payload(make_departure())).status_code == 401

    def test_creates_pending_booking_with_server_price(self, auth_client, user, make_departure):
        departure = make_departure(price_override="38000")

        response = auth_client(user).post(
            LIST, payload(departure, 2, total_amount="1.00", unit_price="1.00", status="confirmed")
        )

        assert response.status_code == 201, response.data
        data = response.data
        assert data["status"] == "pending"
        assert data["participant_count"] == 2
        assert data["unit_price"] == "38000.00"
        assert data["total_amount"] == "76000.00"  # submitted totals are ignored
        assert data["reference"].startswith("HT-")
        assert data["expires_at"] is not None
        assert data["can_cancel"] is True
        assert data["adventure"]["slug"] == departure.adventure.slug
        assert [p["full_name"] for p in data["participants"]] == ["Trekker 0", "Trekker 1"]

    def test_participant_details_are_validated(self, auth_client, user, make_departure):
        response = auth_client(user).post(
            LIST, payload(make_departure(), participants=[{"full_name": " "}])
        )
        assert response.status_code == 400
        assert "participants" in response.data["error"]["details"]

    def test_needs_at_least_one_participant(self, auth_client, user, make_departure):
        response = auth_client(user).post(LIST, payload(make_departure(), participants=[]))
        assert response.status_code == 400

    def test_policy_acknowledgement_required(self, auth_client, user, make_departure):
        response = auth_client(user).post(LIST, payload(make_departure(), policy_accepted=False))
        assert response.status_code == 400
        assert "policy_accepted" in response.data["error"]["details"]

    def test_full_departure_is_a_conflict(self, auth_client, user, make_departure):
        response = auth_client(user).post(
            LIST, payload(make_departure(capacity=1, seats_reserved=1))
        )
        assert response.status_code == 409
        assert response.data["error"]["code"] == "not_enough_seats"

    def test_unknown_departure(self, auth_client, user):
        response = auth_client(user).post(
            LIST,
            {
                "departure": "00000000-0000-0000-0000-000000000000",
                "participants": [{"full_name": "A"}],
                "policy_accepted": True,
            },
        )
        assert response.status_code == 400


class TestQuote:
    def test_quote_does_not_reserve(self, api, make_departure):
        departure = make_departure(price_override="12500.50", capacity=6, seats_reserved=2)

        response = api.post(QUOTE, {"departure": str(departure.pk), "participant_count": 3})

        assert response.status_code == 200
        assert response.data == {
            "departure": str(departure.pk),
            "participant_count": 3,
            "unit_price": "12500.50",
            "total_amount": "37501.50",
            "currency": "NPR",
            "seats_available": 4,
            "is_bookable": True,
        }
        departure.refresh_from_db()
        assert departure.seats_reserved == 2

    def test_quote_reports_unavailable(self, api, make_departure):
        departure = make_departure(status="closed")
        response = api.post(QUOTE, {"departure": str(departure.pk), "participant_count": 1})
        assert response.data["is_bookable"] is False


class TestOwnBookings:
    def test_lists_only_own_bookings(self, auth_client, user, make_user, make_departure):
        mine = make_booking(user, make_departure())
        make_booking(make_user(), make_departure())

        response = auth_client(user).get(LIST)

        assert response.status_code == 200
        assert [row["id"] for row in response.data["results"]] == [str(mine.pk)]

    def test_cannot_read_someone_elses_booking(self, auth_client, user, make_user, make_departure):
        other = make_booking(make_user(), make_departure())
        assert auth_client(user).get(detail(other)).status_code == 404
        assert auth_client(user).post(cancel_url(other)).status_code == 404

    def test_scopes(self, auth_client, user, make_departure):
        upcoming = make_booking(user, make_departure())
        cancelled = make_booking(user, make_departure())
        services.cancel_booking(cancelled, actor=user)
        past = make_booking(user, make_departure())
        services.confirm_booking(past)
        # The trip has since happened: move its departure into the past.
        past.departure.__class__.objects.filter(pk=past.departure_id).update(
            start_date=timezone.localdate() - dt.timedelta(days=10),
            end_date=timezone.localdate() - dt.timedelta(days=5),
        )
        client = auth_client(user)

        def ids(scope):
            return [row["id"] for row in client.get(LIST, {"scope": scope}).data["results"]]

        assert ids("upcoming") == [str(upcoming.pk)]
        assert ids("past") == [str(past.pk)]
        assert ids("cancelled") == [str(cancelled.pk)]

    def test_user_cancels_pending_booking(self, auth_client, user, make_departure):
        booking = make_booking(user, make_departure())

        response = auth_client(user).post(cancel_url(booking))

        assert response.status_code == 200
        assert response.data["status"] == "cancelled"
        assert response.data["can_cancel"] is False

    def test_bookings_cannot_be_edited_or_deleted(self, auth_client, user, make_departure):
        booking = make_booking(user, make_departure())
        client = auth_client(user)
        assert client.patch(detail(booking), {"total_amount": "1"}).status_code == 405
        assert client.delete(detail(booking)).status_code == 405


class TestAdmin:
    def test_requires_admin(self, auth_client, user):
        assert auth_client(user).get(ADMIN_LIST).status_code == 403

    def test_admin_lists_searches_and_filters(
        self, auth_client, admin_user, make_user, make_departure
    ):
        traveller = make_user(email="dawa@example.com", full_name="Dawa Lama")
        booking = make_booking(traveller, make_departure())
        make_booking(make_user(), make_departure())
        client = auth_client(admin_user)

        assert client.get(ADMIN_LIST).data["count"] == 2
        assert client.get(ADMIN_LIST, {"search": booking.reference}).data["count"] == 1
        assert client.get(ADMIN_LIST, {"search": "dawa@example"}).data["count"] == 1
        assert client.get(ADMIN_LIST, {"status": "pending"}).data["count"] == 2

        row = client.get(ADMIN_LIST, {"search": "Dawa"}).data["results"][0]
        assert row["user"]["email"] == "dawa@example.com"

    def test_admin_detail_includes_history(self, auth_client, admin_user, user, make_departure):
        booking = make_booking(user, make_departure())
        url = reverse("admin_bookings:booking-detail", args=[booking.pk])

        data = auth_client(admin_user).get(url).data

        assert [event["to_status"] for event in data["history"]] == ["pending"]

    def test_admin_cancel_requires_reason(self, auth_client, admin_user, user, make_departure):
        booking = make_booking(user, make_departure())
        url = reverse("admin_bookings:booking-cancel", args=[booking.pk])
        client = auth_client(admin_user)

        assert client.post(url, {}).status_code == 400
        response = client.post(url, {"reason": "Trail closed"})
        assert response.status_code == 200
        assert response.data["status"] == "cancelled"

    def test_admin_cannot_edit_bookings(self, auth_client, admin_user, user, make_departure):
        booking = make_booking(user, make_departure())
        url = reverse("admin_bookings:booking-detail", args=[booking.pk])
        assert auth_client(admin_user).patch(url, {"total_amount": "1"}).status_code == 405


class TestDepartureMinimum:
    URL = reverse("catalog_admin:departure-list")

    def test_flags_departures_below_minimum_after_cutoff(
        self, auth_client, admin_user, user, make_departure, make_adventure
    ):
        adventure = make_adventure(min_participants=4)
        short = make_departure(
            adventure=adventure,
            booking_cutoff=timezone.now() - dt.timedelta(hours=1),
            seats_reserved=2,
        )
        make_departure(adventure=adventure, seats_reserved=1)  # cutoff not reached yet
        make_departure(
            adventure=adventure,
            booking_cutoff=timezone.now() - dt.timedelta(hours=1),
            seats_reserved=5,
        )  # minimum met
        client = auth_client(admin_user)

        flagged = client.get(self.URL, {"needs_decision": "true"}).data["results"]

        assert [row["id"] for row in flagged] == [str(short.pk)]
        assert flagged[0]["min_participants_met"] is False
        assert flagged[0]["needs_decision"] is True
