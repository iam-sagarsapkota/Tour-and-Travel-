"""Queue notifications and deliver them with Celery.

``notify`` stores the message and schedules sending after the surrounding
transaction commits, so an email never goes out for a change that was rolled back.
"""

import datetime as dt
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.bookings.models import Booking

from .messages import BUILDERS
from .models import Notification

logger = logging.getLogger(__name__)
Kind = Notification.Kind
REDACTED = "[Content removed after sending: it contained a single-use link.]"


def notify(
    user, kind: str, *, booking: Booking | None = None, dedupe_key: str | None = None, **context
):
    """Create and queue a notification. Returns None if this event was already notified."""
    if dedupe_key and Notification.objects.filter(dedupe_key=dedupe_key).exists():
        return None
    message = BUILDERS[kind](user, booking=booking, **context)
    text, html = message.render()
    subject = message.subject
    status = Notification.Status.QUEUED
    error = ""
    if not user.email:
        # Phone-only account: SMS is a future channel. Keep the message in-app.
        status, error = Notification.Status.SKIPPED, "No email address; SMS not available yet."
    try:
        with transaction.atomic():
            notification = Notification.objects.create(
                user=user,
                kind=kind,
                recipient=user.email or "",
                subject=subject,
                body_text=text,
                body_html=html,
                status=status,
                last_error=error,
                dedupe_key=dedupe_key,
                booking=booking,
            )
    except IntegrityError:
        return None  # a concurrent call created it first
    if status == Notification.Status.QUEUED:
        from .tasks import send_notification_task

        _after_commit(lambda: send_notification_task.delay(str(notification.pk)))
    return notification


def _after_commit(callback) -> None:
    """Run once the current transaction commits (tests replace this to run immediately)."""
    transaction.on_commit(callback)


def deliver(notification_id) -> str:
    """Send one queued notification. Idempotent; raises on transient failure for retry."""
    with transaction.atomic():
        notification = Notification.objects.select_for_update().get(pk=notification_id)
        if notification.status != Notification.Status.QUEUED:
            return notification.status
        notification.attempts += 1
        notification.save(update_fields=["attempts", "updated_at"])
    message = EmailMultiAlternatives(
        subject=notification.subject,
        body=notification.body_text,
        to=[notification.recipient],
    )
    message.attach_alternative(notification.body_html, "text/html")
    message.send()  # transient SMTP/network errors propagate to the Celery retry

    fields = {"status": Notification.Status.SENT, "sent_at": timezone.now(), "last_error": ""}
    if notification.kind in Notification.SENSITIVE:
        fields.update(body_text=REDACTED, body_html="")
    Notification.objects.filter(pk=notification.pk).update(**fields)
    return Notification.Status.SENT


def mark_failed(notification_id, error: str) -> None:
    Notification.objects.filter(pk=notification_id, status=Notification.Status.QUEUED).update(
        status=Notification.Status.FAILED, last_error=error[:2000]
    )
    logger.error("Notification %s failed permanently: %s", notification_id, error)


def send_trip_reminders(*, today=None) -> int:
    """Remind travellers whose confirmed trip starts in TRIP_REMINDER_DAYS days."""
    today = today or timezone.localdate()
    target = today + dt.timedelta(days=settings.TRIP_REMINDER_DAYS)
    bookings = Booking.objects.filter(
        status=Booking.Status.CONFIRMED, departure__start_date=target
    ).select_related("user__profile", "departure__adventure")
    sent = 0
    for booking in bookings:
        if not booking.user.profile.trip_reminders:
            continue
        if notify(
            booking.user, Kind.TRIP_REMINDER, booking=booking, dedupe_key=f"reminder:{booking.pk}"
        ):
            sent += 1
    return sent


def notify_travellers_of_departure_change(departure, changes: list[str]) -> int:
    holding = departure.bookings.filter(status__in=Booking.HOLDING).select_related("user")
    stamp = timezone.now().strftime("%Y%m%d%H%M%S")
    count = 0
    for booking in holding:
        if notify(
            booking.user,
            Kind.DEPARTURE_CHANGED,
            booking=booking,
            changes=changes,
            dedupe_key=f"departure-change:{booking.pk}:{stamp}",
        ):
            count += 1
    return count
