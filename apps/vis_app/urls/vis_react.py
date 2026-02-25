"""Vis app URLs — figrecipe-embedded mode (/vis-react/).

Serves the same editor page but with figrecipe as the primary workspace,
replacing the legacy split-view (data-pane + canvas-pane).
"""

from __future__ import annotations

from django.http import HttpResponse
from django.urls import path
from figrecipe._django.views import api_dispatch as figrecipe_api_dispatch
from figrecipe._django.views import editor_page as _figrecipe_spa_page

from ..views import figure_editor

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


def _figrecipe_api_with_project_root(request, endpoint):
    """Wrap figrecipe API dispatch, injecting user's project path as working_dir.

    Security: the browser never sees the absolute path — it is resolved
    server-side from the authenticated user's current project, exactly
    like scitex-cloud's own workspace file tree.
    """
    import logging

    from apps.project_app.services.project_utils import get_current_project

    _logger = logging.getLogger(__name__)

    if request.user.is_authenticated:
        project = get_current_project(request, user=request.user)
        _logger.info(
            "[vis_react] user=%s project=%s endpoint=%s",
            request.user.username,
            project.slug if project else None,
            endpoint,
        )
        if project:
            project_path = str(project.get_local_path())
            # Inject working_dir into GET params so figrecipe handlers use it
            mutable_get = request.GET.copy()
            mutable_get["working_dir"] = project_path
            request.GET = mutable_get
    else:
        _logger.warning("[vis_react] unauthenticated request to %s", endpoint)

    return figrecipe_api_dispatch(request, endpoint)


app_name = "vis_react"

urlpatterns = [
    path("", figure_editor, name="editor", kwargs={"figrecipe_embedded": True}),
    path("figrecipe/", _figrecipe_embedded_page, name="figrecipe_editor"),
    path(
        "figrecipe/<path:endpoint>",
        _figrecipe_api_with_project_root,
        name="figrecipe_api",
    ),
]


# EOF
