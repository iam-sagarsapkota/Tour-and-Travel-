from django.contrib import admin

from .models import Adventure, AdventureCategory, AdventureImage, ItineraryDay


@admin.register(AdventureCategory)
class AdventureCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "display_order", "is_active")
    prepopulated_fields = {"slug": ("name",)}


class ItineraryDayInline(admin.TabularInline):
    model = ItineraryDay
    extra = 0


class AdventureImageInline(admin.TabularInline):
    model = AdventureImage
    extra = 0


@admin.register(Adventure)
class AdventureAdmin(admin.ModelAdmin):
    list_display = ("title", "destination", "difficulty", "duration_days", "base_price", "status")
    list_filter = ("status", "difficulty", "activity_type", "destination")
    search_fields = ("title", "slug")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("published_at", "popularity")
    inlines = [ItineraryDayInline, AdventureImageInline]

    def has_delete_permission(self, request, obj=None):
        return False  # archive instead
