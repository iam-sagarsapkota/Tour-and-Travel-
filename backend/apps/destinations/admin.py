from django.contrib import admin

from .models import Destination


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ("name", "region", "status", "display_order")
    list_filter = ("status", "region")
    search_fields = ("name", "region")
    prepopulated_fields = {"slug": ("name",)}

    def has_delete_permission(self, request, obj=None):
        return False  # archive instead
