from django.urls import include, path

app_name = "console_app"

urlpatterns = [
    # Workspace and notebook API endpoints
    path("", include("apps.console_app.urls.api")),
    # SLURM job management API
    path("", include("apps.console_app.urls.jobs")),
    # Project service API, paste-upload, and on-site agent API
    path("", include("apps.console_app.urls.services")),
    # Page/template-serving views (must come after API routes)
    path("", include("apps.console_app.urls.pages")),
]
