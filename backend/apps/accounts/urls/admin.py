from rest_framework.routers import SimpleRouter

from apps.accounts.views import AdminUserViewSet

app_name = "admin_users"

router = SimpleRouter()
router.register("", AdminUserViewSet, basename="user")

urlpatterns = router.urls
