from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    body = serializers.SerializerMethodField()
    booking_id = serializers.UUIDField(source="booking.id", default=None, read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "kind", "subject", "body", "status", "booking_id", "created_at", "read_at"]

    def get_body(self, obj) -> str:
        # Never re-display single-use links (verification / password reset).
        return "" if obj.kind in Notification.SENSITIVE else obj.body_text


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """The signed-in user's messages, newest first."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends: list = []

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Notification.objects.none()
        return Notification.objects.filter(user=self.request.user).select_related("booking")

    @extend_schema(request=None, responses={200: None})
    @action(detail=False, methods=["post"], url_path="read-all")
    def read_all(self, request):
        updated = self.get_queryset().filter(read_at__isnull=True).update(read_at=timezone.now())
        return Response({"marked_read": updated})
