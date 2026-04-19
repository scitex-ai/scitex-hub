import logging

from django.urls import include, path

app_name = "writer_app"

logger = logging.getLogger(__name__)

urlpatterns = [
    # API endpoints (must be first to match /api/* routes)
    path("api/", include("apps.workspace.writer_app.urls.api")),
    # Feature pages
    path("editor/", include("apps.workspace.writer_app.urls.editor")),
    path("compilation/", include("apps.workspace.writer_app.urls.compilation")),
    path("version-control/", include("apps.workspace.writer_app.urls.version_control")),
    path("arxiv/", include("apps.workspace.writer_app.urls.arxiv")),
    path("collaboration/", include("apps.workspace.writer_app.urls.collaboration")),
    # Main index (must be last as catch-all)
    path("", include("apps.workspace.writer_app.urls.index")),
]

# v2: shared `scitex_writer._django` implementation (gradual cut-over).
# Optional: skipped if scitex-writer is not installed in this environment.
try:
    from scitex_writer._django import views as _writer_django_views  # noqa: F401

    urlpatterns.insert(
        1,
        path("", include("apps.workspace.writer_app.urls.writer_django")),
    )
except ImportError as _exc:
    logger.info(
        "[writer_app] scitex-writer not installed, skipping v2 routes: %s", _exc
    )
