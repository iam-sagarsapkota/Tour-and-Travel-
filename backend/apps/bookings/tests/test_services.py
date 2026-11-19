import datetime as dt
import threading
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.adventures.models import Adventure
from apps.bookings import services
from apps.bookings.models import Booking, BookingEvent

pytestmark = pytest.mark.django_db

ONE = [{"full_name": "Pasang Sherpa"}]


def people(count):
    return [{"full_name": f"Trekker {n}"} for n in range(count)]


def book(user, departure, participants=ONE, **kwargs):
    return services.create_booking(
        user=user,
        departure_id=departure.pk,
        participants=participants,
        policy_accepted=True,
        **kwargs,
    )


def error_code(exc_info):
    detail = exc_info.value.detail
    return getattr(detail, "code", None) or exc_info.value.default_code


class TestCreate:
    def test_solo_booking_holds_seat_and_prices_server_side(self, user, make_departure):
        departure = make_departure(capacity=10, price_override="38000.00")

        booking = book(user, departure)

        departure.refresh_from_db()
        assert departure.seats_reserved == 1
        assert booking.status == Booking.Status.PENDING
        assert booking.participant_count == 1
        assert booking.unit_price == Decimal("38000.00")
        assert booking.total_amount == Decimal("38000.00")
        assert booking.currency == "NPR"
        assert booking.policy_accepted_at is not None
        assert booking.participants.get().is_lead

    def test_group_booking_multiplies_price(self, user, make_departure):
        departure = make_departure(price_override="19999.50")

        booking = book(user, departure, people(3))

        assert booking.participant_count == 3
        assert booking.total_amount == Decimal("59998.50")
        assert [p.is_lead for p in booking.participants.order_by("position")] == [
            True,
            False,
            False,
        ]
        departure.refresh_from_db()
        assert departure.seats_reserved == 3

    def test_hold_expires_after_configured_minutes(self, user, make_departure, settings):
        settings.BOOKING_HOLD_MINUTES = 15
        now = timezone.now()
        booking = book(user, make_departure(), now=now)
        assert booking.expires_at == now + dt.timedelta(minutes=15)

    def test_reference_is_unique_and_readable(self, make_user, make_departure):
        departure = make_departure()
        refs = {book(make_user(), departure).reference for _ in range(5)}
        assert len(refs) == 5
        for ref in refs:
            assert ref.startswith("HT-")
            assert len(ref) == 11
            assert not set(ref[3:]) & set("01ILOU")

    def test_records_history(self, user, make_departure):
        booking = book(user, make_departure())
        event = BookingEvent.objects.get(booking=booking)
        assert (event.from_status, event.to_status, event.actor) == ("", "pending", user)

    def test_policy_must_be_accepted(self, user, make_departure):
        with pytest.raises(ValidationError):
            services.create_booking(
                user=user,
                departure_id=make_departure().pk,
                participants=ONE,
                policy_accepted=False,
            )

    @pytest.mark.parametrize(
        ("overrides", "code"),
        [
            ({"status": "cancelled"}, "departure_unavailable"),
            ({"status": "closed"}, "departure_unavailable"),
            (
                {"booking_cutoff": timezone.now() - dt.timedelta(minutes=1)},
                "departure_unavailable",
            ),
            ({"capacity": 2, "seats_reserved": 2}, "not_enough_seats"),
        ],
    )
    def test_rejects_unbookable_departure(self, user, make_departure, overrides, code):
        departure = make_departure(**overrides)
        with pytest.raises(APIException) as exc_info:
            book(user, departure)
        assert error_code(exc_info) == code
        assert not Booking.objects.exists()

    def test_rejects_unpublished_adventure(self, user, make_departure, make_adventure):
        departure = make_departure(adventure=make_adventure(status="draft"))
        with pytest.raises(APIException) as exc_info:
            book(user, departure)
        assert error_code(exc_info) == "departure_unavailable"

    def test_rejects_more_people_than_seats(self, user, make_departure):
        departure = make_departure(capacity=5, seats_reserved=3)
        with pytest.raises(APIException) as exc_info:
            book(user, departure, people(3))
        assert error_code(exc_info) == "not_enough_seats"
        departure.refresh_from_db()
        assert departure.seats_reserved == 3

    def test_respects_adventure_max_group_size(self, user, make_departure, make_adventure):
        departure = make_departure(adventure=make_adventure(max_group_size=4), capacity=20)
        with pytest.raises(ValidationError):
            book(user, departure, people(5))

    def test_respects_global_per_booking_limit(self, user, make_departure, settings):
        settings.MAX_PARTICIPANTS_PER_BOOKING = 2
        with pytest.raises(ValidationError):
            book(user, make_departure(), people(3))

    def test_groups_only_adventure_needs_minimum_party(self, user, make_departure, make_adventure):
        adventure = make_adventure(solo_friendly=False, min_participants=2)
        departure = make_departure(adventure=adventure)

        with pytest.raises(ValidationError):
            book(user, departure)
        assert book(user, departure, people(2)).participant_count == 2

    def test_one_open_hold_per_user_and_departure(self, user, make_departure):
        departure = make_departure()
        book(user, departure)
        with pytest.raises(APIException) as exc_info:
            book(user, departure)
        assert error_code(exc_info) == "pending_booking_exists"

    def test_expired_holds_are_released_before_checking_seats(self, make_user, make_departure):
        departure = make_departure(capacity=2)
        past = timezone.now() - dt.timedelta(hours=1)
        stale = book(make_user(), departure, people(2), now=past)

        fresh = book(make_user(), departure, people(2))

        stale.refresh_from_db()
        departure.refresh_from_db()
        assert stale.status == Booking.Status.EXPIRED
        assert fresh.status == Booking.Status.PENDING
        assert departure.seats_reserved == 2


class TestExpiry:
    def test_sweeper_expires_only_stale_holds(self, make_user, make_departure):
        quiet, busy = make_departure(capacity=10), make_departure(capacity=10)
        stale = book(make_user(), quiet, people(2), now=timezone.now() - dt.timedelta(hours=1))
        live = book(make_user(), busy, people(3))

        assert services.expire_pending_bookings() == 1

        stale.refresh_from_db()
        live.refresh_from_db()
        quiet.refresh_from_db()
        busy.refresh_from_db()
        assert stale.status == Booking.Status.EXPIRED
        assert live.status == Booking.Status.PENDING
        assert (quiet.seats_reserved, busy.seats_reserved) == (0, 3)
        assert stale.events.filter(to_status="expired", actor__isnull=True).exists()

    def test_sweeper_is_idempotent(self, user, make_departure):
        book(user, make_departure(), now=timezone.now() - dt.timedelta(hours=1))
        assert services.expire_pending_bookings() == 1
        assert services.expire_pending_bookings() == 0

    def test_celery_task_runs_the_sweeper(self, user, make_departure):
        from apps.bookings.tasks import expire_pending_bookings_task

        book(user, make_departure(), now=timezone.now() - dt.timedelta(hours=1))
        assert expire_pending_bookings_task.delay().get() == 1


class TestConfirm:
    def test_confirm_pending_booking(self, user, make_departure):
        booking = book(user, make_departure(), people(2))
        adventure_id = booking.departure.adventure_id

        services.confirm_booking(booking)

        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED
        assert booking.confirmed_at is not None
        assert Adventure.objects.get(pk=adventure_id).popularity == 2
        booking.departure.refresh_from_db()
        assert booking.departure.seats_reserved == 2  # seats stay held

    def test_cannot_confirm_expired_hold(self, user, make_departure):
        booking = book(user, make_departure(), now=timezone.now() - dt.timedelta(hours=1))
        with pytest.raises(APIException) as exc_info:
            services.confirm_booking(booking)
        assert error_code(exc_info) == "booking_expired"
        booking.refresh_from_db()
        assert booking.status == Booking.Status.EXPIRED

    def test_confirm_is_idempotent(self, user, make_departure):
        booking = book(user, make_departure())
        services.confirm_booking(booking)
        services.confirm_booking(booking)
        assert booking.events.filter(to_status="confirmed").count() == 1
        assert Adventure.objects.get(pk=booking.departure.adventure_id).popularity == 1


class TestCancel:
    def test_user_cancels_pending_and_seats_return(self, user, make_departure):
        booking = book(user, make_departure(capacity=4), people(3))

        services.cancel_booking(booking, actor=user)

        booking.refresh_from_db()
        assert booking.status == Booking.Status.CANCELLED
        assert booking.cancelled_at is not None
        booking.departure.refresh_from_db()
        assert booking.departure.seats_reserved == 0

    def test_user_cannot_cancel_confirmed_booking_yet(self, user, make_departure):
        booking = book(user, make_departure())
        services.confirm_booking(booking)
        with pytest.raises(APIException) as exc_info:
            services.cancel_booking(booking, actor=user)
        assert error_code(exc_info) == "cancellation_not_allowed"

    def test_admin_cancels_confirmed_booking_with_reason(self, user, admin_user, make_departure):
        booking = book(user, make_departure(), people(2))
        services.confirm_booking(booking)

        services.cancel_booking(booking, actor=admin_user, reason="Landslide on the trail")

        booking.refresh_from_db()
        assert booking.status == Booking.Status.CANCELLED
        assert booking.cancellation_reason == "Landslide on the trail"
        booking.departure.refresh_from_db()
        assert booking.departure.seats_reserved == 0
        event = booking.events.get(to_status="cancelled")
        assert (event.actor, event.from_status, event.note) == (
            admin_user,
            "confirmed",
            "Landslide on the trail",
        )

    def test_admin_must_give_reason(self, user, admin_user, make_departure):
        booking = book(user, make_departure())
        with pytest.raises(ValidationError):
            services.cancel_booking(booking, actor=admin_user, reason=" ")

    def test_cancelling_twice_is_rejected_without_double_release(
        self, user, make_user, make_departure
    ):
        booking = book(user, make_departure(capacity=5), people(2))
        book(make_user(), booking.departure)  # another traveller's seat must stay held
        services.cancel_booking(booking, actor=user)
        with pytest.raises(APIException):
            services.cancel_booking(booking, actor=user)
        booking.departure.refresh_from_db()
        assert booking.departure.seats_reserved == 1


class TestConstraints:
    def test_total_must_equal_unit_price_times_participants(self, user, make_departure):
        booking = book(user, make_departure())
        with pytest.raises(IntegrityError), transaction.atomic():
            Booking.objects.filter(pk=booking.pk).update(total_amount=Decimal("1.00"))

    def test_pending_booking_needs_expiry(self, user, make_departure):
        booking = book(user, make_departure())
        with pytest.raises(IntegrityError), transaction.atomic():
            Booking.objects.filter(pk=booking.pk).update(expires_at=None)


@pytest.mark.django_db(transaction=True)
def test_concurrent_requests_cannot_oversell(make_user, make_departure):
    """AC-06. Needs real row locks, so it runs on PostgreSQL (CI and Docker) only."""
    if connection.vendor != "postgresql":
        pytest.skip("Row-level locking is only exercised on PostgreSQL.")

    departure = make_departure(capacity=3)
    users = [make_user() for _ in range(8)]
    barrier = threading.Barrier(len(users))
    outcomes: list[str] = []
    lock = threading.Lock()

    def attempt(user):
        try:
            barrier.wait()
            book(user, departure)
            result = "ok"
        except APIException as exc:
            result = str(getattr(exc.detail, "code", exc.default_code))
        except Exception as exc:  # surface anything unexpected in the assertion
            result = repr(exc)
        finally:
            connection.close()
        with lock:
            outcomes.append(result)

    threads = [threading.Thread(target=attempt, args=(user,)) for user in users]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert outcomes.count("ok") == 3, outcomes
    assert set(outcomes) <= {"ok", "not_enough_seats", "departure_unavailable"}, outcomes
    departure.refresh_from_db()
    assert departure.seats_reserved == 3
    assert Booking.objects.filter(departure=departure).count() == 3
