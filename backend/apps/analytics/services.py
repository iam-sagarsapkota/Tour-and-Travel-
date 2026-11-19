"""Numbers for the traveller and admin dashboards.

Definitions (also in docs/dashboards.md):
- Verified revenue: sum of payments a provider confirmed (status successful), by paid_at.
- Booking conversion: confirmed / (confirmed + cancelled + expired), over bookings
  created in the period. Pending bookings are still undecided and excluded.
- Payment success rate: successful / settled attempts (successful, failed, cancelled,
  expired), over attempts created in the period.
- Months are calendar months in Nepal time (Asia/Kathmandu).
"""

import datetime as dt
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.accounts.models import User
from apps.adventures.models import Adventure
from apps.adventures.selectors import public_events
from apps.bookings.models import Booking
from apps.departures.models import Departure
from apps.payments.models import Payment, PaymentAttempt
from common.models import PublishStatus

NEPAL = ZoneInfo(settings.BUSINESS_TIME_ZONE)
ZERO = Decimal("0.00")
CAPACITY_ALERT = Decimal("0.8")


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _month_starts(months: int, now) -> list[dt.date]:
    local = now.astimezone(NEPAL)
    year, month = local.year, local.month
    starts = []
    for _ in range(months):
        starts.append(dt.date(year, month, 1))
        month -= 1
        if month == 0:
            year, month = year - 1, 12
    return list(reversed(starts))


def admin_overview(*, months: int = 12, now=None) -> dict:
    now = now or timezone.now()
    today = timezone.localdate(now)
    starts = _month_starts(months, now)
    period_start = dt.datetime.combine(starts[0], dt.time.min, tzinfo=NEPAL)

    bookings = Booking.objects.filter(created_at__gte=period_start)
    by_status = dict(bookings.values_list("status").annotate(n=Count("id")))
    decided = sum(by_status.get(s, 0) for s in ("confirmed", "cancelled", "expired"))

    attempts = PaymentAttempt.objects.filter(created_at__gte=period_start)
    attempt_status = dict(attempts.values_list("status").annotate(n=Count("id")))
    settled = sum(
        attempt_status.get(s, 0) for s in ("successful", "failed", "cancelled", "expired")
    )

    paid = Payment.objects.filter(status=Payment.Status.SUCCESSFUL)
    revenue = paid.filter(paid_at__gte=period_start).aggregate(total=Sum("amount"))["total"] or ZERO

    kpis = {
        "bookings": bookings.count(),
        "confirmed_bookings": by_status.get("confirmed", 0),
        "verified_revenue": revenue,
        "currency": "NPR",
        "upcoming_departures": Departure.objects.filter(
            status__in=[Departure.Status.OPEN, Departure.Status.CLOSED], start_date__gte=today
        ).count(),
        "active_users": User.objects.filter(
            is_active=True, last_login__gte=now - dt.timedelta(days=30)
        ).count(),
        "published_adventures": Adventure.objects.filter(status=PublishStatus.PUBLISHED).count(),
        "payment_success_rate": _rate(attempt_status.get("successful", 0), settled),
        "booking_conversion": _rate(by_status.get("confirmed", 0), decided),
    }

    # Monthly series (Nepal calendar months), filling gaps with zeros.
    booking_months = dict(
        Booking.objects.filter(status=Booking.Status.CONFIRMED, confirmed_at__gte=period_start)
        .annotate(month=TruncMonth("confirmed_at", tzinfo=NEPAL))
        .values_list("month")
        .annotate(n=Count("id"))
    )
    revenue_months = dict(
        paid.filter(paid_at__gte=period_start)
        .annotate(month=TruncMonth("paid_at", tzinfo=NEPAL))
        .values_list("month")
        .annotate(total=Sum("amount"))
    )

    def by_month(series, start):
        for key, value in series.items():
            if key and key.astimezone(NEPAL).date() == start:
                return value
        return None

    monthly = [
        {
            "month": start.strftime("%Y-%m"),
            "bookings": by_month(booking_months, start) or 0,
            "revenue": by_month(revenue_months, start) or ZERO,
        }
        for start in starts
    ]

    confirmed = Booking.objects.filter(status=Booking.Status.CONFIRMED)
    destinations = list(
        confirmed.values(
            name=F("departure__adventure__destination__name"),
            slug=F("departure__adventure__destination__slug"),
        )
        .annotate(travellers=Sum("participant_count"), bookings=Count("id"))
        .order_by("-travellers")[:8]
    )
    events = list(
        confirmed.values(
            title=F("departure__adventure__title"), slug=F("departure__adventure__slug")
        )
        .annotate(
            bookings=Count("id"),
            travellers=Sum("participant_count"),
            revenue=Sum("total_amount"),
        )
        .order_by("-revenue")[:5]
    )

    upcoming = Departure.objects.filter(
        status=Departure.Status.OPEN, start_date__gte=today
    ).select_related("adventure")
    capacity_alerts = [
        {
            "id": d.pk,
            "adventure": d.adventure.title,
            "start_date": d.start_date,
            "seats_reserved": d.seats_reserved,
            "capacity": d.capacity,
        }
        for d in upcoming.filter(seats_reserved__gte=F("capacity") * CAPACITY_ALERT).order_by(
            "start_date"
        )[:10]
    ]
    needs_decision = [
        {
            "id": d.pk,
            "adventure": d.adventure.title,
            "start_date": d.start_date,
            "seats_reserved": d.seats_reserved,
            "minimum": d.effective_min_participants,
        }
        for d in Departure.objects.needing_minimum_decision(now)
        .select_related("adventure")
        .order_by("start_date")[:10]
    ]
    attention = list(
        Payment.objects.filter(needs_attention=True)
        .select_related("booking")
        .order_by("-updated_at")
        .values("id", "amount", "currency", "status", reference=F("booking__reference"))[:10]
    )
    recent = list(
        Booking.objects.select_related("user", "departure__adventure")
        .order_by("-created_at")
        .values(
            "id",
            "reference",
            "status",
            "total_amount",
            "currency",
            "created_at",
            traveller=F("user__full_name"),
            adventure=F("departure__adventure__title"),
        )[:8]
    )

    return {
        "period": {"from": starts[0], "months": months},
        "kpis": kpis,
        "monthly": monthly,
        "destination_popularity": destinations,
        "event_performance": events,
        "recent_bookings": recent,
        "capacity_alerts": capacity_alerts,
        "departures_needing_decision": needs_decision,
        "payments_needing_attention": attention,
    }


def traveller_overview(user, *, now=None) -> dict:
    now = now or timezone.now()
    today = timezone.localdate(now)
    mine = Booking.objects.filter(user=user).select_related(
        "departure__adventure__destination", "payment"
    )
    upcoming = mine.filter(status__in=Booking.HOLDING, departure__end_date__gte=today).order_by(
        "departure__start_date"
    )
    pending_payment = mine.filter(status=Booking.Status.PENDING, expires_at__gt=now)
    counts = mine.aggregate(
        total=Count("id"),
        upcoming=Count("id", filter=Q(status__in=Booking.HOLDING, departure__end_date__gte=today)),
        completed=Count(
            "id", filter=Q(status=Booking.Status.CONFIRMED, departure__end_date__lt=today)
        ),
        cancelled=Count(
            "id", filter=Q(status__in=[Booking.Status.CANCELLED, Booking.Status.EXPIRED])
        ),
    )
    spent = (
        Payment.objects.filter(booking__user=user, status=Payment.Status.SUCCESSFUL).aggregate(
            total=Sum("amount")
        )["total"]
        or ZERO
    )
    booked = mine.values("departure__adventure_id")
    recommendations = (
        public_events()
        .exclude(pk__in=booked)
        .filter(next_departure_date__isnull=False)
        .order_by("-is_featured", "-popularity", "title")[:3]
    )
    return {
        "counts": counts,
        "total_spent": spent,
        "currency": "NPR",
        "upcoming": list(upcoming[:3]),
        "pending_payment": list(pending_payment[:5]),
        "recommendations": list(recommendations),
    }
