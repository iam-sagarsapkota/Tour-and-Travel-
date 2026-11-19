from django.contrib import admin

from .models import Booking, BookingEvent, BookingParticipant


class ParticipantInline(admin.TabularInline):
    model = BookingParticipant
    extra = 0
    can_delete = False


class EventInline(admin.TabularInline):
    model = BookingEvent
    extra = 0
    can_delete = False
    readonly_fields = ("from_status", "to_status", "actor", "note", "created_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    """Read-only in Django admin: status changes go through the booking service/API."""

    list_display = ("reference", "user", "departure", "participant_count", "total_amount", "status")
    list_filter = ("status",)
    search_fields = ("reference", "user__email", "user__phone", "user__full_name")
    inlines = [ParticipantInline, EventInline]

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
