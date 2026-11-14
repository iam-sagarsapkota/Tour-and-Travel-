"""Admin-only catalog management endpoints under /api/v1/admin/."""

from rest_framework.routers import SimpleRouter

from apps.adventures.views import (
    AdventureAdminViewSet,
    AdventureImageAdminViewSet,
    CategoryAdminViewSet,
)
from apps.departures.views import DepartureAdminViewSet
from apps.destinations.views import DestinationAdminViewSet

app_name = "catalog_admin"

router = SimpleRouter()
router.register("destinations", DestinationAdminViewSet, basename="destination")
router.register("categories", CategoryAdminViewSet, basename="category")
router.register("adventures", AdventureAdminViewSet, basename="adventure")
router.register("adventure-images", AdventureImageAdminViewSet, basename="adventure-image")
router.register("departures", DepartureAdminViewSet, basename="departure")

urlpatterns = router.urls
