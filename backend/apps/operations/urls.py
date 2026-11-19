from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

public_urlpatterns = [
    path("site/", views.PublicSiteSettingsView.as_view(), name="site"),
    path("contact/", views.ContactView.as_view({"post": "create"}), name="contact"),
]

admin_router = SimpleRouter()
admin_router.register("contact-inquiries", views.AdminContactViewSet, basename="contact")
admin_router.register("audit-logs", views.AuditLogViewSet, basename="audit-log")
admin_urlpatterns = [
    path("site-settings/", views.AdminSiteSettingsView.as_view(), name="site-settings"),
    *admin_router.urls,
]
