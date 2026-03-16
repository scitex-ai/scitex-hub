"""Vis app URLs - figrecipe-embedded mode (/apps/figrecipe-react/).

Delegates directly to figrecipe._django (pip package) with
project-context injection and fetch-override for embedded mode.
"""

from __future__ import annotations

from django.http import HttpResponse
from django.urls import path
from figrecipe._django.views import api_dispatch
from figrecipe._django.views import editor_page as _figrecipe_spa_page

from ..views import figure_editor

_FETCH_OVERRIDE = """<script>
(function(){var _f=window.fetch,B='/apps/figrecipe-react/figrecipe';
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
    path("figrecipe/<path:endpoint>", api_dispatch, name="figrecipe_api"),
]


# EOF
