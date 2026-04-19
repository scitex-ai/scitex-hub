from django.urls import include, path

app_name = "writer_app"

urlpatterns = [
    # API endpoints (must be first to match /api/* routes)
    path("api/", include("apps.workspace.writer_app.urls.api")),
    # v2: shared `scitex_writer._django` implementation (gradual cut-over)
    path("", include("apps.workspace.writer_app.urls.writer_django")),
    # Feature pages
    path("editor/", include("apps.workspace.writer_app.urls.editor")),
    path("compilation/", include("apps.workspace.writer_app.urls.compilation")),
    path("version-control/", include("apps.workspace.writer_app.urls.version_control")),
    path("arxiv/", include("apps.workspace.writer_app.urls.arxiv")),
    path("collaboration/", include("apps.workspace.writer_app.urls.collaboration")),
    # Main index (must be last as catch-all)
    path("", include("apps.workspace.writer_app.urls.index")),
]
