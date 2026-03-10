from django.urls import path, include

app_name = "writer_app"

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
