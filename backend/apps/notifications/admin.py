from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "recipient", "status", "attempts", "sent_at")
    list_filter = ("kind", "status")
    search_fields = ("recipient", "subject")
    exclude = ("body_html",)

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields if field.name != "body_html"]

    def has_add_permission(self, request):
        return False
