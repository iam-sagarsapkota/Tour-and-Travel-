import smtplib
import socket

from celery import shared_task

from . import services

# Errors worth retrying: the mail server or network may recover.
TRANSIENT = (smtplib.SMTPException, socket.error, TimeoutError, ConnectionError)


@shared_task(
    bind=True,
    name="notifications.send",
    autoretry_for=TRANSIENT,
    max_retries=5,
    retry_backoff=30,  # 30s, 60s, 120s, ... (bounded below)
    retry_backoff_max=900,
    retry_jitter=True,
)
def send_notification_task(self, notification_id: str) -> str:
    try:
        return services.deliver(notification_id)
    except TRANSIENT as exc:
        if self.request.retries >= self.max_retries:
            services.mark_failed(notification_id, f"Gave up after retries: {exc}")
            return "failed"
        raise
    except Exception as exc:  # not transient: record it instead of retrying forever
        services.mark_failed(notification_id, repr(exc))
        return "failed"


@shared_task(name="notifications.trip_reminders")
def send_trip_reminders_task() -> int:
    return services.send_trip_reminders()
