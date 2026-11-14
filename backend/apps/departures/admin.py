from django.contrib import admin

from .models import Departure


@admin.register(Departure)
class DepartureAdmin(admin.ModelAdmin):
    list_display = ("adventure", "start_date", "end_date", "capacity", "seats_reserved", "status")
    list_filter = ("status",)
    search_fields = ("adventure__title",)
    date_hierarchy = "start_date"
    readonly_fields = ("seats_reserved",)
    autocomplete_fields = ("adventure",)

    def has_delete_permission(self, request, obj=None):
        return False  # cancel instead
