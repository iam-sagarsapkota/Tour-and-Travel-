from django.contrib import admin

from .models import Payment, PaymentAttempt, PaymentLog


class ReadOnlyAdmin(admin.ModelAdmin):
    """Transaction history is immutable: viewable, never editable or deletable here."""

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdmin):
    list_display = (
        "booking",
        "amount",
        "currency",
        "status",
        "provider",
        "needs_attention",
        "paid_at",
    )
    list_filter = ("status", "provider", "needs_attention")
    search_fields = ("booking__reference", "gateway_reference")


@admin.register(PaymentAttempt)
class PaymentAttemptAdmin(ReadOnlyAdmin):
    list_display = ("reference", "provider", "amount", "status", "gateway_status", "created_at")
    list_filter = ("provider", "status")
    search_fields = ("reference", "gateway_token", "gateway_transaction_id")


@admin.register(PaymentLog)
class PaymentLogAdmin(ReadOnlyAdmin):
    list_display = ("attempt", "kind", "message", "created_at")
    list_filter = ("kind",)
