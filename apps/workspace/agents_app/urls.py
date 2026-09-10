"""Login-gated routes for the optional SAC dashboard."""

from django.urls import path

from . import views

app_name = "scitex_agent_container"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/fleet", views.fleet_api, name="fleet_api"),
    path("healthz", views.healthz, name="healthz"),
    path("<str:name>/", views.detail, name="detail"),
    path("<str:name>/action", views.lifecycle_action, name="lifecycle_action"),
]
