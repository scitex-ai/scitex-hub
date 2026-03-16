"""Vis app URLs - Page views."""

from __future__ import annotations

from django.urls import path

from .. import views

urlpatterns = [
    path("", views.figure_editor, name="figure_editor"),
]


# EOF
