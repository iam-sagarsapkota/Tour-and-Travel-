import datetime as dt
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.bookings import services as booking_services
from apps.payments.models import Payment, PaymentAttempt

pytestmark = pytest.mark.django_db

ADMIN = reverse("admin-dashboard")
MINE = reverse("dashboard")


def book(user, departure, count=1, **kwargs):
    return booking_services.create_booking(
        user=user,
        departure_id=departure.pk,
        participants=[{"full_name": f"P{n}"} for n in range(count)],
        policy_accepted=True,
        **kwargs,
    )


def pay(booking, *, provider="esewa", status="successful"):
    payment = Payment.objects.create(
        booking=booking,
        amount=booking.total_amount,
        currency="NPR",
        status=status,
        provider=provider if status == "successful" else "",
        paid_at=timezone.now() if status == "successful" else None,
    )
    PaymentAttempt.objects.create(
        payment=payment,
        provider=provider,
        reference=f"{booking.reference}-{status[:3].upper()}",
        amount=booking.total_amount,
        currency="NPR",
        status=status,
    )
    if status == "successful":
        booking_services.confirm_booking(booking)
    return payment


@pytest.fixture
def activity(make_user, make_departure, make_adventure, make_destination):
    everest = make_destination(name="Everest Region", slug="everest")
    ebc = make_adventure(title="EBC", slug="ebc", destination=everest)
    departure = make_departure(adventure=ebc, price_override="50000", capacity=5)
    first = book(make_user(), departure, 2)
    pay(first)
    second = book(make_user(), departure, 2)
    pay(second)
    failed = book(make_user(), make_departure(price_override="1000"))
    pay(failed, status="failed")
    booking_services.cancel_booking(failed, actor=failed.user)
    return {"departure": departure, "bookings": [first, second, failed]}


class TestAdminDashboard:
    def test_admin_only(self, auth_client, user):
        assert auth_client(user).get(ADMIN).status_code == 403

    def test_kpis(self, auth_client, admin_user, activity):
        data = auth_client(admin_user).get(ADMIN).data
        kpis = data["kpis"]

        assert kpis["bookings"] == 3
        assert kpis["confirmed_bookings"] == 2
        assert kpis["verified_revenue"] == "200000.00"  # 2 bookings x 2 people x 50,000
        assert kpis["payment_success_rate"] == pytest.approx(2 / 3, abs=1e-4)
        assert kpis["booking_conversion"] == pytest.approx(2 / 3, abs=1e-4)
        assert kpis["published_adventures"] >= 1

    def test_monthly_series_and_rankings(self, auth_client, admin_user, activity):
        data = auth_client(admin_user).get(ADMIN, {"months": 3}).data

        assert len(data["monthly"]) == 3
        current = data["monthly"][-1]
        assert current["bookings"] == 2
        assert Decimal(current["revenue"]) == Decimal("200000")
        assert data["destination_popularity"][0]["slug"] == "everest"
        assert data["destination_popularity"][0]["travellers"] == 4
        assert data["event_performance"][0]["revenue"] == "200000.00"
        assert len(data["recent_bookings"]) == 3

    def test_operational_alerts(
        self, auth_client, admin_user, activity, make_departure, make_adventure
    ):
        make_departure(
            adventure=make_adventure(min_participants=4),
            booking_cutoff=timezone.now() - dt.timedelta(hours=1),
            seats_reserved=1,
        )
        Payment.objects.filter(pk=activity["bookings"][0].payment.pk).update(
            needs_attention=True, attention_reason="Duplicate"
        )

        data = auth_client(admin_user).get(ADMIN).data

        assert [a["id"] for a in data["capacity_alerts"]] == [str(activity["departure"].pk)]  # 4/5
        assert len(data["departures_needing_decision"]) == 1
        assert [p["reference"] for p in data["payments_needing_attention"]] == [
            activity["bookings"][0].reference
        ]

    @pytest.mark.parametrize("months", ["0", "25", "abc"])
    def test_months_validated(self, auth_client, admin_user, months):
        assert auth_client(admin_user).get(ADMIN, {"months": months}).status_code == 400

    def test_empty_system(self, auth_client, admin_user):
        kpis = auth_client(admin_user).get(ADMIN).data["kpis"]
        assert kpis["payment_success_rate"] is None
        assert kpis["verified_revenue"] == "0.00"


class TestTravellerDashboard:
    def test_requires_login(self, api):
        assert api.get(MINE).status_code == 401

    def test_overview(self, auth_client, user, make_departure, make_adventure):
        trip = make_departure(price_override="30000")
        confirmed = book(user, trip, 2)
        pay(confirmed)
        unpaid = book(user, make_departure())
        cancelled = book(user, make_departure())
        booking_services.cancel_booking(cancelled, actor=user)
        recommended = make_adventure(slug="recommended", is_featured=True)
        make_departure(adventure=recommended)

        data = auth_client(user).get(MINE).data

        assert data["counts"] == {"total": 3, "upcoming": 2, "completed": 0, "cancelled": 1}
        assert data["total_spent"] == "60000.00"
        assert [b["id"] for b in data["pending_payment"]] == [str(unpaid.pk)]
        assert {b["id"] for b in data["upcoming"]} == {str(confirmed.pk), str(unpaid.pk)}
        slugs = [event["slug"] for event in data["recommendations"]]
        assert slugs[0] == "recommended"
        assert trip.adventure.slug not in slugs  # already booked
