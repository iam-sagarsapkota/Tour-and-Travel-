from rest_framework.routers import SimpleRouter

from .views import DestinationViewSet

app_name = "destinations"

router = SimpleRouter()
router.register("", DestinationViewSet, basename="destination")

urlpatterns = router.urls
