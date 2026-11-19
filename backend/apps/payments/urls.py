from django.urls import path
from rest_framework.routers import SimpleRouter

from . import views

urlpatterns = [
    path("providers/", views.ProvidersView.as_view(), name="providers"),
    path("initiate/", views.InitiateView.as_view(), name="initiate"),
    path("verify/", views.VerifyView.as_view(), name="verify"),
    path("history/", views.PaymentHistoryView.as_view(), name="history"),
]

admin_router = SimpleRouter()
admin_router.register("", views.AdminPaymentViewSet, basename="payment")
admin_urlpatterns = admin_router.urls
