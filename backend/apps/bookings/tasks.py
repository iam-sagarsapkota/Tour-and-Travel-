from celery import shared_task

from . import services


@shared_task(name="bookings.expire_pending_bookings")
def expire_pending_bookings_task() -> int:
    """Release seats held by unpaid bookings whose hold has lapsed."""
    return services.expire_pending_bookings()
