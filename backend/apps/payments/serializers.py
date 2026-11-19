from rest_framework import serializers

from .models import Payment, PaymentAttempt, PaymentLog, Provider


class ProviderSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()


class InitiateSerializer(serializers.Serializer):
    booking = serializers.UUIDField()
    provider = serializers.ChoiceField(choices=Provider.choices)


class RedirectSerializer(serializers.Serializer):
    """Where the browser goes next. For POST, submit ``fields`` as a form to ``url``."""

    attempt = serializers.UUIDField()
    method = serializers.ChoiceField(choices=["GET", "POST"])
    url = serializers.URLField()
    fields = serializers.DictField(child=serializers.CharField())


class VerifySerializer(serializers.Serializer):
    attempt = serializers.UUIDField()
    # What the gateway appended to the return URL (eSewa "data", Khalti "pidx", ...).
    # Logged for audit only; the provider's API decides the outcome.
    params = serializers.DictField(child=serializers.CharField(allow_blank=True), required=False)


class AttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentAttempt
        fields = [
            "id",
            "provider",
            "reference",
            "amount",
            "currency",
            "status",
            "gateway_status",
            "gateway_transaction_id",
            "created_at",
            "completed_at",
        ]


class PaymentSerializer(serializers.ModelSerializer):
    booking_id = serializers.UUIDField(source="booking.id")
    booking_reference = serializers.CharField(source="booking.reference")
    booking_status = serializers.CharField(source="booking.status")
    adventure = serializers.CharField(source="booking.departure.adventure.title")
    attempts = AttemptSerializer(many=True, read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "booking_id",
            "booking_reference",
            "booking_status",
            "adventure",
            "amount",
            "currency",
            "status",
            "provider",
            "gateway_reference",
            "paid_at",
            "created_at",
            "attempts",
        ]


class VerifyResultSerializer(serializers.Serializer):
    attempt = AttemptSerializer()
    payment = PaymentSerializer()


class PaymentLogSerializer(serializers.ModelSerializer):
    attempt = serializers.CharField(source="attempt.reference")

    class Meta:
        model = PaymentLog
        fields = ["attempt", "kind", "message", "payload", "created_at"]


class AdminPaymentSerializer(PaymentSerializer):
    traveller = serializers.CharField(source="booking.user.full_name")
    traveller_contact = serializers.SerializerMethodField()
    logs = serializers.SerializerMethodField()

    class Meta(PaymentSerializer.Meta):
        fields = [
            *PaymentSerializer.Meta.fields,
            "traveller",
            "traveller_contact",
            "needs_attention",
            "attention_reason",
            "logs",
        ]

    def get_traveller_contact(self, obj) -> str:
        user = obj.booking.user
        return user.email or user.phone or ""

    def get_logs(self, obj) -> list[dict]:
        logs = PaymentLog.objects.filter(attempt__payment=obj).select_related("attempt")
        return PaymentLogSerializer(logs, many=True).data


class ResolveSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=2000)
