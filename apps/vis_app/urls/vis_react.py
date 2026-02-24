"""Vis app URLs — figrecipe-embedded mode (/vis-react/).

Serves the same editor page but with figrecipe as the primary workspace,
replacing the legacy split-view (data-pane + canvas-pane).
"""

from __future__ import annotations

from django.urls import path

from ..views import figure_editor
from ..views.api.figrecipe import figrecipe_api, figrecipe_editor_page

app_name = "vis_react"

urlpatterns = [
    path("", figure_editor, name="editor",
         kwargs={"figrecipe_embedded": True}),
    path("figrecipe/", figrecipe_editor_page, name="figrecipe_editor"),
    path("figrecipe/<path:endpoint>", figrecipe_api, name="figrecipe_api"),
]


# EOF
