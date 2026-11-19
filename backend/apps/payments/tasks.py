from celery import shared_task

from . import services


@shared_task(name="payments.reconcile_open_attempts")
def reconcile_open_attempts_task() -> int:
    """Ask the providers about payments whose browser never came back."""
    return services.reconcile_open_attempts()
