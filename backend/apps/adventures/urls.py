from django.urls import path

from . import views

event_urlpatterns = [
    path("", views.EventListView.as_view(), name="event-list"),
    path("<slug:slug>/", views.EventDetailView.as_view(), name="event-detail"),
]

category_urlpatterns = [
    path("", views.CategoryListView.as_view(), name="category-list"),
]
