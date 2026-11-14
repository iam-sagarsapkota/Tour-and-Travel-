from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.adventures.urls import category_urlpatterns, event_urlpatterns
from common.views import HealthView, ReadinessView

api_v1 = [
    path("auth/", include("apps.accounts.urls.auth")),
    # Public catalog
    path("events/", include((event_urlpatterns, "events"))),
    path("categories/", include((category_urlpatterns, "categories"))),
    path("destinations/", include("apps.destinations.urls")),
    # Admin
    path("admin/users/", include("apps.accounts.urls.admin")),
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
