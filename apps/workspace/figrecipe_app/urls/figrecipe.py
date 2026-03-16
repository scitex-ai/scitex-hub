"""Vis app URLs - figrecipe editor integration.

Delegates directly to figrecipe._django (pip package).
"""

from __future__ import annotations

from django.urls import path
from figrecipe._django.views import api_dispatch, editor_page

urlpatterns = [
    path("figrecipe/", editor_page, name="figrecipe_editor"),
    path("figrecipe/<path:endpoint>", api_dispatch, name="figrecipe_api"),
]


# EOF
