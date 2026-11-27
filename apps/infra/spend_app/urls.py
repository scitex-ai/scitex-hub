from django.urls import path

from . import views

urlpatterns = [
    path("", views.spend_settings, name="settings"),
    path("cap/", views.set_cap, name="set_cap"),
    path("cancel/", views.cancel_within_window, name="cancel_within_window"),
    path("api/status/", views.status_api, name="status_api"),
]
