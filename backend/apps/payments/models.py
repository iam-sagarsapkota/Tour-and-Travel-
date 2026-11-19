from django.db import models
from django.db.models import Q

from common.models import BaseModel


class Provider(models.TextChoices):
    ESEWA = "esewa", "eSewa"
    KHALTI = "khalti", "Khalti"


class Payment(BaseModel):
    """What a booking owes and whether it has been paid.

    One per booking. Each try at a gateway is a ``PaymentAttempt``; the payment
    becomes successful only when an attempt is verified with the provider.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"

    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.PROTECT, related_name="payment"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    provider = models.CharField(max_length=10, choices=Provider.choices, blank=True)
    gateway_reference = models.CharField(
        max_length=100, blank=True, help_text="Provider transaction id of the successful attempt."
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    # Set when money and booking disagree (e.g. paid after seats ran out, a duplicate
    # payment, an amount mismatch) so an admin can refund or resolve it.
    needs_attention = models.BooleanField(default=False, db_index=True)
    attention_reason = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_positive"),
        ]

    def __str__(self):
        return f"Payment for {self.booking}"


class PaymentAttempt(BaseModel):
    """One redirect to a gateway. Retries create new attempts; none are deleted."""

    class Status(models.TextChoices):
        INITIATED = "initiated", "Initiated"
        PROCESSING = "processing", "Processing"
        SUCCESSFUL = "successful", "Successful"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"
        REFUNDED = "refunded", "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially refunded"

    OPEN = (Status.INITIATED, Status.PROCESSING)

    payment = models.ForeignKey(Payment, on_delete=models.PROTECT, related_name="attempts")
    provider = models.CharField(max_length=10, choices=Provider.choices)
    reference = models.CharField(
        max_length=40,
        unique=True,
        help_text="Our id sent to the gateway (eSewa transaction_uuid / Khalti purchase_order_id).",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.INITIATED, db_index=True
    )
    gateway_token = models.CharField(
        max_length=100, blank=True, db_index=True, help_text="Khalti pidx."
    )
    gateway_transaction_id = models.CharField(max_length=100, blank=True)
    gateway_status = models.CharField(max_length=40, blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["status", "created_at"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0), name="payment_attempt_amount_positive"
            ),
        ]

    def __str__(self):
        return self.reference


class PaymentLog(models.Model):
    """Append-only record of everything exchanged with a gateway, for audit and support."""

    class Kind(models.TextChoices):
        INITIATE = "initiate", "Initiate"
        RETURN = "return", "Browser return"
        STATUS_CHECK = "status_check", "Status check"
        STATUS_CHANGE = "status_change", "Status change"
        ERROR = "error", "Error"
        ADMIN = "admin", "Admin action"

    attempt = models.ForeignKey(PaymentAttempt, on_delete=models.PROTECT, related_name="logs")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    message = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.attempt}: {self.kind}"


# Importable aliases (used by SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]).
PaymentStatus = Payment.Status
PaymentAttemptStatus = PaymentAttempt.Status
