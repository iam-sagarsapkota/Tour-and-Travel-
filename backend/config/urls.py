from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.adventures.urls import category_urlpatterns, event_urlpatterns
from apps.analytics.views import AdminDashboardView, TravellerDashboardView
from apps.bookings.urls import admin_urlpatterns as admin_booking_urlpatterns
from apps.bookings.urls import urlpatterns as booking_urlpatterns
from apps.notifications.views import NotificationViewSet
from apps.operations.urls import admin_urlpatterns as operations_admin_urlpatterns
from apps.operations.urls import public_urlpatterns as operations_urlpatterns
from apps.payments.urls import admin_urlpatterns as admin_payment_urlpatterns
from apps.payments.urls import urlpatterns as payment_urlpatterns
from common.views import HealthView, ReadinessView

notification_list = NotificationViewSet.as_view({"get": "list"})
notification_read_all = NotificationViewSet.as_view({"post": "read_all"})

api_v1 = [
    path("auth/", include("apps.accounts.urls.auth")),
    # Public catalog
    path("events/", include((event_urlpatterns, "events"))),
    path("categories/", include((category_urlpatterns, "categories"))),
    path("destinations/", include("apps.destinations.urls")),
    # Bookings (authenticated)
    path("bookings/", include((booking_urlpatterns, "bookings"))),
    path("payments/", include((payment_urlpatterns, "payments"))),
    # Traveller account area
    path("dashboard/", TravellerDashboardView.as_view(), name="dashboard"),
    path("notifications/", notification_list, name="notifications"),
    path("notifications/read-all/", notification_read_all, name="notifications-read-all"),
    # Site information and contact form
    path("", include((operations_urlpatterns, "operations"))),
    # Admin
    path("admin/users/", include("apps.accounts.urls.admin")),
    path("admin/bookings/", include((admin_booking_urlpatterns, "admin_bookings"))),
    path("admin/payments/", include((admin_payment_urlpatterns, "admin_payments"))),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/", include((operations_admin_urlpatterns, "admin_operations"))),
    path("admin/", include("config.admin_urls")),
    # Docs
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/v1/", include(api_v1)),
    path("health/", HealthView.as_view(), name="health"),
    path("ready/", ReadinessView.as_view(), name="ready"),
]

if settings.DEBUG:
    # Development only; in production Nginx serves uploaded media.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
