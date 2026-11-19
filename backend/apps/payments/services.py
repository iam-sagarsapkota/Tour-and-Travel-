"""Payment flow: initiate at a gateway, verify server to server, apply exactly once.

    pending booking -> initiate (hold extended) -> gateway -> browser returns
    -> verify with the provider's API -> successful attempt -> booking confirmed

Rules (PRD §7):
- Only a provider's server-side answer can mark money as received; the browser
  redirect and its parameters are logged but never trusted.
- The amount the provider reports must equal what we asked for.
- Verifying twice (duplicate callbacks, reconciliation racing the browser) is
  harmless: results are applied under a row lock, once.
- Every exchange with a provider is kept in PaymentLog.
"""

import datetime as dt
import logging
import secrets

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError

from apps.bookings import services as booking_services
from apps.bookings.exceptions import BookingConflict
from apps.bookings.models import Booking

from .gateways import GatewayError, Result, get_gateway
from .models import Payment, PaymentAttempt, PaymentLog

logger = logging.getLogger(__name__)
Attempt = PaymentAttempt.Status

# Gateway statuses that settle an attempt for good.
FINAL = {
    Attempt.SUCCESSFUL,
    Attempt.FAILED,
    Attempt.CANCELLED,
    Attempt.EXPIRED,
    Attempt.REFUNDED,
    Attempt.PARTIALLY_REFUNDED,
}


class PaymentProviderUnavailable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = "The payment provider could not be reached. Please try again."
    default_code = "provider_unavailable"


def _log(attempt: PaymentAttempt, kind: str, message: str = "", payload: dict | None = None):
    PaymentLog.objects.create(
        attempt=attempt, kind=kind, message=message[:255], payload=payload or {}
    )


def _new_reference(booking: Booking) -> str:
    # eSewa allows letters, digits and hyphens only.
    return f"{booking.reference}-{secrets.token_hex(3).upper()}"


def _return_urls(attempt: PaymentAttempt) -> dict[str, str]:
    base = f"{settings.FRONTEND_URL.rstrip('/')}/payments/{attempt.provider}/{attempt.pk}"
    return {"success": f"{base}/success", "failure": f"{base}/failure", "return": f"{base}/return"}


def initiate_payment(*, booking: Booking, provider: str) -> tuple[PaymentAttempt, dict]:
    """Start a new attempt and return where to send the browser."""
    gateway = get_gateway(provider)
    if gateway is None:
        raise ValidationError({"provider": ["This payment method is not available."]})
    if booking.currency != "NPR":
        raise ValidationError({"provider": [f"{gateway.name} only accepts payments in NPR."]})
    if provider == "khalti" and booking.total_amount < gateway.MIN_AMOUNT:
        raise ValidationError({"provider": ["Khalti payments must be more than NPR 10."]})

    with transaction.atomic():
        payment, _ = Payment.objects.select_for_update().get_or_create(
            booking=booking,
            defaults={"amount": booking.total_amount, "currency": booking.currency},
        )
        if payment.status == Payment.Status.SUCCESSFUL:
            raise BookingConflict("This booking is already paid.", code="already_paid")
        booking_services.extend_hold(
            booking, until=timezone.now() + dt.timedelta(minutes=settings.PAYMENT_HOLD_MINUTES)
        )
        attempt = PaymentAttempt.objects.create(
            payment=payment,
            provider=provider,
            reference=_new_reference(booking),
            amount=payment.amount,
            currency=payment.currency,
        )
        if payment.status != Payment.Status.PROCESSING:
            payment.status = Payment.Status.PENDING
            payment.save(update_fields=["status", "updated_at"])

    urls = _return_urls(attempt)
    try:
        if provider == "esewa":
            redirect = gateway.initiate(
                attempt, success_url=urls["success"], failure_url=urls["failure"]
            )
        else:
            name = f"{booking.departure.adventure.title} ({booking.reference})"
            redirect = gateway.initiate(attempt, return_url=urls["return"], name=name)
    except GatewayError as exc:
        attempt.status = Attempt.FAILED
        attempt.save(update_fields=["status", "updated_at"])
        _log(attempt, PaymentLog.Kind.ERROR, f"Initiation failed: {exc}")
        logger.warning("Payment initiation failed for %s: %s", attempt.reference, exc)
        raise PaymentProviderUnavailable() from exc

    if redirect.token:
        attempt.gateway_token = redirect.token
        attempt.save(update_fields=["gateway_token", "updated_at"])
    # The eSewa form carries a signature, not a secret; logging it is safe.
    _log(
        attempt,
        PaymentLog.Kind.INITIATE,
        "Sent to gateway",
        {"url": redirect.url, **redirect.fields, **redirect.raw},
    )
    return attempt, {"method": redirect.method, "url": redirect.url, "fields": redirect.fields}


def record_return(attempt: PaymentAttempt, params: dict) -> None:
    """Keep what the browser brought back, for audit only. It decides nothing."""
    payload = dict(params)
    if attempt.provider == "esewa" and params.get("data"):
        decoded = get_gateway("esewa").read_return(params["data"]) if get_gateway("esewa") else None
        payload = {"decoded": decoded, "signature_valid": decoded is not None}
    _log(attempt, PaymentLog.Kind.RETURN, "Browser returned from gateway", payload)


def _effective_status(attempt: PaymentAttempt, result: Result, now) -> str:
    """Don't give up on an attempt the traveller may still be completing."""
    young = now - attempt.created_at < dt.timedelta(minutes=settings.PAYMENT_ATTEMPT_GRACE_MINUTES)
    if result.status == Attempt.EXPIRED and young:
        return Attempt.PROCESSING
    return result.status


def _flag(payment: Payment, reason: str) -> None:
    payment.needs_attention = True
    payment.attention_reason = "\n".join(filter(None, [payment.attention_reason, reason]))
    payment.save(update_fields=["needs_attention", "attention_reason", "updated_at"])
    logger.warning("Payment %s needs attention: %s", payment.pk, reason)


def _apply(attempt_id, result: Result, now) -> PaymentAttempt:
    with transaction.atomic():
        attempt = (
            PaymentAttempt.objects.select_for_update().select_related("payment").get(pk=attempt_id)
        )
        payment = Payment.objects.select_for_update().get(pk=attempt.payment_id)
        attempt.payment = payment
        _log(
            attempt,
            PaymentLog.Kind.STATUS_CHECK,
            f"Provider status {result.gateway_status}",
            result.raw,
        )
        attempt.last_checked_at = now
        attempt.gateway_status = result.gateway_status
        if result.transaction_id:
            attempt.gateway_transaction_id = result.transaction_id

        new_status = _effective_status(attempt, result, now)
        if new_status == Attempt.SUCCESSFUL and result.amount != attempt.amount:
            new_status = Attempt.FAILED
            _flag(
                payment,
                f"Attempt {attempt.reference}: provider reported {result.amount} "
                f"but {attempt.amount} was requested. Possible tampering; do not deliver.",
            )

        previous = attempt.status
        already_settled = previous in FINAL and previous != Attempt.SUCCESSFUL
        if already_settled or previous == new_status:
            attempt.save(
                update_fields=[
                    "last_checked_at",
                    "gateway_status",
                    "gateway_transaction_id",
                    "updated_at",
                ]
            )
            return attempt

        attempt.status = new_status
        if new_status in FINAL:
            attempt.completed_at = attempt.completed_at or now
        attempt.save()
        _log(attempt, PaymentLog.Kind.STATUS_CHANGE, f"{previous} -> {new_status}")
        if (
            new_status in (Attempt.FAILED, Attempt.EXPIRED)
            and payment.status != Payment.Status.SUCCESSFUL
        ):
            _notify_traveller(payment, "payment_failed", f"payment_failed:{attempt.pk}")

        if new_status == Attempt.SUCCESSFUL:
            _on_success(payment, attempt, now)
        elif new_status in (Attempt.REFUNDED, Attempt.PARTIALLY_REFUNDED):
            payment.status = (
                Payment.Status.REFUNDED
                if new_status == Attempt.REFUNDED
                else Payment.Status.PARTIALLY_REFUNDED
            )
            payment.save(update_fields=["status", "updated_at"])
            _flag(payment, f"{attempt.provider} reports a refund on {attempt.reference}.")
        elif payment.status not in (Payment.Status.SUCCESSFUL, Payment.Status.REFUNDED):
            _refresh_open_status(payment)
    return attempt


def _on_success(payment: Payment, attempt: PaymentAttempt, now) -> None:
    if payment.status == Payment.Status.SUCCESSFUL:
        # Money arrived twice (e.g. two tabs). Keep both records; refund one.
        _flag(payment, f"Duplicate payment {attempt.reference}: refund it.")
        return
    payment.status = Payment.Status.SUCCESSFUL
    payment.provider = attempt.provider
    payment.gateway_reference = attempt.gateway_transaction_id
    payment.paid_at = now
    payment.save()
    if not booking_services.confirm_paid_booking(payment.booking, now=now):
        _notify_traveller(payment, "payment_needs_review", f"payment_needs_review:{payment.pk}")
        _flag(
            payment,
            "Paid, but the booking could not be confirmed (cancelled, or no seats left "
            "after the hold expired). Refund the traveller.",
        )


def _notify_traveller(payment: Payment, kind: str, dedupe_key: str) -> None:
    from apps.notifications.services import notify

    booking = payment.booking
    notify(booking.user, kind, booking=booking, dedupe_key=dedupe_key)


def _refresh_open_status(payment: Payment) -> None:
    statuses = set(payment.attempts.values_list("status", flat=True))
    if statuses & {Attempt.PROCESSING}:
        new = Payment.Status.PROCESSING
    elif statuses & {Attempt.INITIATED}:
        new = Payment.Status.PENDING
    elif statuses == {Attempt.CANCELLED}:
        new = Payment.Status.CANCELLED
    else:
        new = Payment.Status.FAILED
    if payment.status != new:
        payment.status = new
        payment.save(update_fields=["status", "updated_at"])


def verify_attempt(attempt: PaymentAttempt, *, now=None, force=False) -> PaymentAttempt:
    """Ask the provider about an attempt and apply the answer (idempotent).

    The network call happens outside any transaction; the result is applied under
    a row lock, so concurrent verifications settle the attempt exactly once.
    ``force`` re-checks a settled attempt (admin reconciliation, e.g. to see refunds).
    """
    now = now or timezone.now()
    if attempt.status in FINAL and not (force and attempt.status == Attempt.SUCCESSFUL):
        return attempt
    gateway = get_gateway(attempt.provider)
    if gateway is None:
        return attempt
    try:
        result = gateway.check(attempt)
    except GatewayError as exc:
        _log(attempt, PaymentLog.Kind.ERROR, f"Status check failed: {exc}")
        logger.warning("Status check failed for %s: %s", attempt.reference, exc)
        return attempt
    return _apply(attempt.pk, result, now)


def reconcile_open_attempts(*, now=None, min_age_minutes=5, max_age_hours=48) -> int:
    """Settle attempts whose browser never came back. Run by Celery beat."""
    now = now or timezone.now()
    open_attempts = PaymentAttempt.objects.filter(
        status__in=PaymentAttempt.OPEN,
        created_at__lte=now - dt.timedelta(minutes=min_age_minutes),
        created_at__gte=now - dt.timedelta(hours=max_age_hours),
    )
    changed = 0
    for attempt in open_attempts:
        before = attempt.status
        if verify_attempt(attempt, now=now).status != before:
            changed += 1
    return changed


def resolve_attention(payment: Payment, *, actor, note: str) -> Payment:
    note = note.strip()
    if not note:
        raise ValidationError({"note": ["Describe how this was resolved."]})
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        payment.needs_attention = False
        payment.save(update_fields=["needs_attention", "updated_at"])
        latest = payment.attempts.order_by("-created_at").first()
        if latest:
            _log(latest, PaymentLog.Kind.ADMIN, f"Resolved by {actor.full_name}", {"note": note})
    return payment
