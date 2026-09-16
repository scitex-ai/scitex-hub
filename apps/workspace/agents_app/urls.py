"""Authenticated Hub mount for scitex-agent-container's Django dashboard.

The upstream package owns the UI and control-plane projection. The Hub owns
the public route and its login boundary, so every upstream view is delegated
through :mod:`apps.workspace.agents_app.views` instead of mounting the package
URLconf raw.
"""

from __future__ import annotations

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

__all__ = ["urlpatterns"]
