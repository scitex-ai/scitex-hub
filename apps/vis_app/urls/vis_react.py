"""Vis app URLs — figrecipe-embedded mode (/vis-react/).

NOTE: This module delegates to the consolidated figrecipe API handler
in views/api/figrecipe.py which now handles project-context injection
automatically. This /vis-react/ mount is kept for backward compatibility
but all API calls are handled by the same code path as /vis/figrecipe/.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.urls import path
from figrecipe._django.views import editor_page as _figrecipe_spa_page

from ..views import figure_editor
from ..views.api.figrecipe import figrecipe_api

_FETCH_OVERRIDE = """<script>
(function(){var _f=window.fetch,B='/vis-react/figrecipe';
window.fetch=function(u){var a=[].slice.call(arguments);
if(typeof u==='string'&&u.startsWith('/')&&!u.startsWith(B)&&!u.startsWith('/static'))
a[0]=B+u;return _f.apply(this,a);};})();
</script>"""


def _figrecipe_embedded_page(request):
    """Serve figrecipe React SPA with API base URL override."""
    response = _figrecipe_spa_page(request)
    if response.status_code == 200 and hasattr(response, "content"):
        html = response.content.decode()
        html = html.replace("<script", _FETCH_OVERRIDE + "\n<script", 1)
        return HttpResponse(html)
    return response


app_name = "vis_react"

urlpatterns = [
    path("", figure_editor, name="editor", kwargs={"figrecipe_embedded": True}),
    path("figrecipe/", _figrecipe_embedded_page, name="figrecipe_editor"),
    # Delegates to consolidated handler (same as /vis/figrecipe/<endpoint>)
    path(
        "figrecipe/<path:endpoint>",
        figrecipe_api,
        name="figrecipe_api",
    ),
]


# EOF
