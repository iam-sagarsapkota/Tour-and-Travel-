from rest_framework.routers import SimpleRouter

from .views import AdminBookingViewSet, BookingViewSet

router = SimpleRouter()
router.register("", BookingViewSet, basename="booking")
urlpatterns = router.urls

admin_router = SimpleRouter()
admin_router.register("", AdminBookingViewSet, basename="booking")
admin_urlpatterns = admin_router.urls
