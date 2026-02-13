"""Vis app URLs - figrecipe editor integration."""

from __future__ import annotations

from django.urls import path

from ..views.api.figrecipe import figrecipe_api, figrecipe_editor_page

urlpatterns = [
    path("figrecipe/", figrecipe_editor_page, name="figrecipe_editor"),
    path("figrecipe/<path:endpoint>", figrecipe_api, name="figrecipe_api"),
]


# EOF
