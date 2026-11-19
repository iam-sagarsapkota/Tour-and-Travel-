"""Booking business rules: reserve seats, release them, confirm and cancel.

Concurrency: every change to a departure's seats happens inside a transaction
that holds a row lock on that departure (``SELECT ... FOR UPDATE``). Locks are
always taken in the order departure -> booking, so two operations can never
deadlock on each other. The database check constraint
``departure_seats_reserved_within_capacity`` is the final guard against overselling.
"""

import datetime as dt
import logging
import secrets
from collections.abc import Sequence
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.adventures.models import Adventure
from apps.departures.models import Departure

from .exceptions import BookingConflict
from .models import Booking, BookingEvent, BookingParticipant

logger = logging.getLogger(__name__)

# Crockford-style alphabet without look-alikes (0/O, 1/I/L, U).
_REFERENCE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTVWXYZ"
_CENTS = Decimal("0.01")


def _new_reference() -> str:
    while True:
        body = "".join(secrets.choice(_REFERENCE_ALPHABET) for _ in range(8))
        reference = f"HT-{body}"
        if not Booking.objects.filter(reference=reference).exists():
            return reference


def _lock_departure(departure_id) -> Departure:
    return (
        Departure.objects.select_for_update(of=("self",))
        .select_related("adventure", "adventure__destination")
        .get(pk=departure_id)
    )


def _record(booking: Booking, from_status: str, to_status: str, actor=None, note: str = ""):
    BookingEvent.objects.create(
        booking=booking, actor=actor, from_status=from_status, to_status=to_status, note=note
    )


def _change_seats(departure: Departure, delta: int) -> None:
    Departure.objects.filter(pk=departure.pk).update(seats_reserved=F("seats_reserved") + delta)
    departure.refresh_from_db(fields=["seats_reserved"])


def _release_expired_holds(departure: Departure, now) -> int:
    """Expire lapsed holds on a departure the caller has already locked."""
    stale = list(
        Booking.objects.select_for_update().filter(
            departure=departure, status=Booking.Status.PENDING, expires_at__lte=now
        )
    )
    if not stale:
        return 0
    for booking in stale:
        booking.status = Booking.Status.EXPIRED
        booking.save(update_fields=["status", "updated_at"])
        _record(booking, Booking.Status.PENDING, Booking.Status.EXPIRED, note="Payment hold lapsed")
    _change_seats(departure, -sum(booking.participant_count for booking in stale))
    return len(stale)


def max_participants_per_booking(departure: Departure) -> int:
    limits = [settings.MAX_PARTICIPANTS_PER_BOOKING]
    if departure.adventure.max_group_size:
        limits.append(departure.adventure.max_group_size)
    return min(limits)


def quote(departure: Departure, participant_count: int) -> dict:
    """Server-side price for a party size. Reserves nothing."""
    unit = departure.price
    return {
        "departure": departure.pk,
        "participant_count": participant_count,
        "unit_price": unit,
        "total_amount": (unit * participant_count).quantize(_CENTS),
        "currency": departure.adventure.currency,
        "seats_available": departure.seats_available,
        "is_bookable": departure.is_bookable(),
    }


def create_booking(
    *,
    user,
    departure_id,
    participants: Sequence[dict],
    policy_accepted: bool,
    now: dt.datetime | None = None,
) -> Booking:
    """Hold seats for ``len(participants)`` people and create a pending booking."""
    now = now or timezone.now()
    if not policy_accepted:
        raise ValidationError({"policy_accepted": ["You must accept the booking policy."]})
    count = len(participants)
    if count < 1:
        raise ValidationError({"participants": ["Add at least one participant."]})

    with transaction.atomic():
        departure = _lock_departure(departure_id)
        _release_expired_holds(departure, now)

        if not departure.is_open_for_booking(now):
            raise BookingConflict(
                "This departure is not open for booking.", code="departure_unavailable"
            )
        if count > departure.seats_available:
            left = departure.seats_available
            raise BookingConflict(
                f"Only {left} seat{'s' if left != 1 else ''} left on this departure.",
                code="not_enough_seats",
            )

        limit = max_participants_per_booking(departure)
        if count > limit:
            raise ValidationError(
                {"participants": [f"A single booking can include at most {limit} people."]}
            )
        minimum = departure.effective_min_participants
        if not departure.adventure.solo_friendly and count < minimum:
            raise ValidationError(
                {"participants": [f"This trip is for groups of at least {minimum} people."]}
            )
        if Booking.objects.filter(
            user=user, departure=departure, status=Booking.Status.PENDING
        ).exists():
            raise BookingConflict(
                "You already have an unpaid booking for this departure. "
                "Complete or cancel it first.",
                code="pending_booking_exists",
            )

        unit = departure.price
        booking = Booking.objects.create(
            reference=_new_reference(),
            user=user,
            departure=departure,
            status=Booking.Status.PENDING,
            participant_count=count,
            unit_price=unit,
            total_amount=(unit * count).quantize(_CENTS),
            currency=departure.adventure.currency,
            policy_accepted_at=now,
            expires_at=now + dt.timedelta(minutes=settings.BOOKING_HOLD_MINUTES),
        )
        BookingParticipant.objects.bulk_create(
            BookingParticipant(
                booking=booking,
                position=position,
                is_lead=position == 0,
                full_name=person["full_name"].strip(),
                nationality=person.get("nationality", "").strip(),
                date_of_birth=person.get("date_of_birth"),
            )
            for position, person in enumerate(participants)
        )
        _change_seats(departure, count)
        _record(booking, "", Booking.Status.PENDING, actor=user)

    logger.info("Booking %s created (%s seats)", booking.reference, count)
    return booking


def expire_pending_bookings(now: dt.datetime | None = None) -> int:
    """Release every lapsed hold. Run periodically by Celery beat; safe to repeat."""
    now = now or timezone.now()
    departure_ids = (
        Booking.objects.filter(status=Booking.Status.PENDING, expires_at__lte=now)
        .values_list("departure_id", flat=True)
        .distinct()
    )
    expired = 0
    for departure_id in list(departure_ids):
        with transaction.atomic():
            expired += _release_expired_holds(_lock_departure(departure_id), now)
    if expired:
        logger.info("Expired %s unpaid booking holds", expired)
    return expired


def _lock_booking(booking: Booking) -> tuple[Departure, Booking]:
    departure = _lock_departure(booking.departure_id)
    return departure, Booking.objects.select_for_update().get(pk=booking.pk)


def confirm_booking(booking: Booking, *, actor=None, now: dt.datetime | None = None) -> Booking:
    """Mark a held booking as confirmed. Only verified payments may call this (phase 5).

    Idempotent: confirming an already confirmed booking changes nothing.
    """
    now = now or timezone.now()
    with transaction.atomic():
        departure, locked = _lock_booking(booking)
        if locked.status == Booking.Status.CONFIRMED:
            return locked
        if locked.status == Booking.Status.PENDING and locked.expires_at <= now:
            # Commit the release before reporting it, so the seats really go back on sale.
            _release_expired_holds(departure, now)
            locked.refresh_from_db()
    if locked.status == Booking.Status.EXPIRED:
        raise BookingConflict("The seat hold for this booking expired.", code="booking_expired")

    with transaction.atomic():
        departure, locked = _lock_booking(booking)
        if locked.status == Booking.Status.CONFIRMED:
            return locked
        if locked.status != Booking.Status.PENDING or locked.expires_at <= now:
            raise BookingConflict(
                f"A {locked.status} booking cannot be confirmed.", code="invalid_status"
            )
        locked.status = Booking.Status.CONFIRMED
        locked.confirmed_at = now
        locked.save(update_fields=["status", "confirmed_at", "updated_at"])
        Adventure.objects.filter(pk=departure.adventure_id).update(
            popularity=F("popularity") + locked.participant_count
        )
        _record(locked, Booking.Status.PENDING, Booking.Status.CONFIRMED, actor=actor)
    return locked


def extend_hold(booking: Booking, *, until: dt.datetime) -> Booking:
    """Keep seats held while the traveller is on the payment page. Never shortens a hold."""
    with transaction.atomic():
        _, locked = _lock_booking(booking)
        if locked.status != Booking.Status.PENDING or locked.expires_at <= timezone.now():
            raise BookingConflict(
                "The seat hold for this booking has ended. Please book again.",
                code="booking_expired",
            )
        if until > locked.expires_at:
            locked.expires_at = until
            locked.save(update_fields=["expires_at", "updated_at"])
    return locked


def confirm_paid_booking(booking: Booking, *, now: dt.datetime | None = None) -> bool:
    """Confirm a booking after a verified payment, recovering a lapsed hold if possible.

    A traveller can finish paying after the hold expired. If the departure still
    has room the seats are re-reserved and the booking confirmed; otherwise this
    returns False and the payment is flagged for a refund. Returns True on success.
    """
    now = now or timezone.now()
    try:
        confirm_booking(booking, now=now)
        return True
    except BookingConflict as exc:
        if exc.detail.code != "booking_expired":
            return False

    with transaction.atomic():
        departure, locked = _lock_booking(booking)
        if locked.status == Booking.Status.CONFIRMED:
            return True
        still_running = departure.status in (
            Departure.Status.OPEN,
            Departure.Status.CLOSED,
        ) and departure.start_date >= timezone.localdate(now)
        if (
            locked.status != Booking.Status.EXPIRED
            or not still_running
            or departure.seats_available < locked.participant_count
        ):
            return False
        locked.status = Booking.Status.CONFIRMED
        locked.confirmed_at = now
        locked.save(update_fields=["status", "confirmed_at", "updated_at"])
        _change_seats(departure, locked.participant_count)
        Adventure.objects.filter(pk=departure.adventure_id).update(
            popularity=F("popularity") + locked.participant_count
        )
        _record(
            locked,
            Booking.Status.EXPIRED,
            Booking.Status.CONFIRMED,
            note="Paid after the hold lapsed; seats re-reserved.",
        )
    return True


def can_user_cancel(booking: Booking) -> bool:
    """Travellers may cancel unpaid holds. Paid bookings need the refund workflow (phase 5)."""
    return booking.status == Booking.Status.PENDING


def cancel_booking(booking: Booking, *, actor, reason: str = "") -> Booking:
    reason = reason.strip()
    is_admin = actor.is_admin and actor.pk != booking.user_id
    if is_admin and not reason:
        raise ValidationError({"reason": ["Give a reason; the traveller will see it."]})

    with transaction.atomic():
        departure, locked = _lock_booking(booking)
        allowed = Booking.HOLDING if is_admin else (Booking.Status.PENDING,)
        if locked.status not in allowed:
            message = (
                "Paid bookings can't be cancelled online yet. Please contact us."
                if locked.status == Booking.Status.CONFIRMED
                else f"This booking is already {locked.status}."
            )
            raise BookingConflict(message, code="cancellation_not_allowed")

        previous = locked.status
        locked.status = Booking.Status.CANCELLED
        locked.cancelled_at = timezone.now()
        locked.cancellation_reason = reason
        locked.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
        _change_seats(departure, -locked.participant_count)
        _record(locked, previous, Booking.Status.CANCELLED, actor=actor, note=reason)
    return locked


def confirmed_participants(departure: Departure) -> int:
    return (
        departure.bookings.filter(status=Booking.Status.CONFIRMED).aggregate(
            total=Sum("participant_count")
        )["total"]
        or 0
    )
