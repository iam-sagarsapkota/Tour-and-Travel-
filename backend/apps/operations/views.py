from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.permissions import IsAdmin

from . import audit
from .models import AuditLog, ContactInquiry, SiteSettings


class SiteSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSettings
        fields = [
            "site_name",
            "support_email",
            "support_phone",
            "announcement",
            "announcement_active",
        ]


class ContactInquirySerializer(serializers.ModelSerializer):
    handled_by = serializers.CharField(source="handled_by.full_name", default=None, read_only=True)

    class Meta:
        model = ContactInquiry
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "handled",
            "handled_by",
            "handled_at",
            "created_at",
        ]
        read_only_fields = ["id", "handled", "handled_by", "handled_at", "created_at"]


class AuditLogSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(source="actor.full_name", default=None)

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "actor",
            "action",
            "object_type",
            "object_id",
            "object_repr",
            "changes",
            "note",
            "ip_address",
            "created_at",
        ]


class PublicSiteSettingsView(APIView):
    """Support contacts and the site announcement, for the public site."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(responses=SiteSettingsSerializer)
    def get(self, request):
        return Response(SiteSettingsSerializer(SiteSettings.load()).data)


class AdminSiteSettingsView(APIView):
    permission_classes = [IsAdmin]

    @extend_schema(responses=SiteSettingsSerializer)
    def get(self, request):
        return Response(SiteSettingsSerializer(SiteSettings.load()).data)

    @extend_schema(request=SiteSettingsSerializer, responses=SiteSettingsSerializer)
    def patch(self, request):
        settings_row = SiteSettings.load()
        serializer = SiteSettingsSerializer(settings_row, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        fields = list(serializer.validated_data)
        before = audit.snapshot(settings_row, fields)
        serializer.save()
        changes = audit.diff(before, audit.snapshot(settings_row, fields))
        if changes:
            audit.record(
                actor=request.user,
                action="update",
                obj=settings_row,
                changes=changes,
                request=request,
            )
        return Response(serializer.data)


class ContactView(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Public contact form."""

    serializer_class = ContactInquirySerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_scope = "contact"


class AdminContactViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ContactInquirySerializer
    permission_classes = [IsAdmin]
    queryset = ContactInquiry.objects.select_related("handled_by")
    filterset_fields = ["handled"]
    search_fields = ["name", "email", "subject"]

    @extend_schema(request=None, responses=ContactInquirySerializer)
    @action(detail=True, methods=["post"])
    def handle(self, request, pk=None):
        inquiry = self.get_object()
        if not inquiry.handled:
            inquiry.handled = True
            inquiry.handled_by = request.user
            inquiry.handled_at = timezone.now()
            inquiry.save(update_fields=["handled", "handled_by", "handled_at", "updated_at"])
            audit.record(actor=request.user, action="handle", obj=inquiry, request=request)
        return Response(self.get_serializer(inquiry).data)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only audit trail for admins."""

    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]
    queryset = AuditLog.objects.select_related("actor")
    filterset_fields = ["action", "object_type", "object_id", "actor"]
    search_fields = ["object_repr", "note"]
